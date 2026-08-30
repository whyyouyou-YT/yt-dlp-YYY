import os

# インストーラー版はProgram Files配下(管理者権限が必要)にインストールされ、
# ショートカットはWorkingDir未指定のためそこがカレントディレクトリになる。
# yt-dlp・依存ライブラリ・子プロセス(node等)はcwdへの相対パス書き込みに
# 依存する箇所があり、それが原因で情報取得時にPermissionErrorになる不具合が
# あった(個別のtempfile呼び出し単位で塞いでも別経路で再発したため、
# 他の一切のimportより前にプロセス全体のcwdを確実に書き込み可能な場所へ
# 固定することで、この種の不具合を経路に依らず解消する)。
_WRITABLE_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "yt-dlp-YYY")
os.makedirs(_WRITABLE_DIR, exist_ok=True)
os.chdir(_WRITABLE_DIR)

import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.clipboard import copy_files_to_clipboard
from app.downloader import (
    KIND_OPTIONS,
    QUALITY_OPTIONS,
    Downloader,
    container_options_for_kind,
    is_audio_only,
)
from app.fonts import FONT_FAMILY, load_custom_fonts
from app.history import add_history_entry, clear_history, load_history
from app.settings import load_settings, save_settings
from app.sound import play_complete_sound
from app.winutil import is_admin, relaunch_as_admin

APP_VERSION = "v1.6.0"

ICON_PATH = (
    Path(sys._MEIPASS) / "assets" / "icons" / "rounded_y_logo.ico"
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
    else Path(__file__).resolve().parent.parent / "assets" / "icons" / "rounded_y_logo.ico"
)

ACCENT_COLOR = {"fg": "#1f6aa5", "hover": "#144870"}
APPEARANCE_OPTIONS = ["ダーク", "ライト"]
_APPEARANCE_MODE_MAP = {"ダーク": "dark", "ライト": "light"}

load_custom_fonts()

ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"yt-dlp-YYY ダウンローダー {APP_VERSION}" + ("（管理者）" if is_admin() else ""))
        self.geometry("700x600")
        self.minsize(620, 540)
        if ICON_PATH.exists():
            try:
                self.iconbitmap(str(ICON_PATH))
            except Exception:
                pass

        self.font_normal = ctk.CTkFont(family=FONT_FAMILY, size=13)
        self.font_bold = ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")
        self.font_small = ctk.CTkFont(family=FONT_FAMILY, size=11)
        self.font_percent = ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold")

        self.settings = load_settings()
        self.progress_queue: "queue.Queue" = queue.Queue()
        self.downloader = Downloader(self.progress_queue)
        self.is_downloading = False

        appearance = self.settings.get("appearance", APPEARANCE_OPTIONS[0])
        if appearance not in APPEARANCE_OPTIONS:
            appearance = APPEARANCE_OPTIONS[0]
        ctk.set_appearance_mode(_APPEARANCE_MODE_MAP[appearance])

        self._build_widgets()
        self._apply_accent()
        self.after(200, self._poll_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_widgets(self):
        pad = {"padx": 12, "pady": 6}

        url_frame = ctk.CTkFrame(self)
        url_frame.pack(fill="x", **pad)
        ctk.CTkLabel(url_frame, text="動画/プレイリストURL", font=self.font_bold, anchor="center").pack(fill="x", padx=8, pady=(8, 0))
        url_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        url_row.pack(fill="x", padx=8, pady=(0, 8))
        self.url_entry = ctk.CTkEntry(
            url_row, placeholder_text="https://www.youtube.com/watch?v=...", font=self.font_normal
        )
        self.url_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            url_row, text="貼り付け", width=80, font=self.font_normal, command=self._paste_url
        ).pack(side="left", padx=(8, 0))

        options_frame = ctk.CTkFrame(self)
        options_frame.pack(fill="x", **pad)

        kind_col = ctk.CTkFrame(options_frame, fg_color="transparent")
        kind_col.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        ctk.CTkLabel(kind_col, text="種別", font=self.font_bold, anchor="center").pack(fill="x")
        self.kind_var = ctk.StringVar(value=self.settings.get("kind", KIND_OPTIONS[0]))
        if self.kind_var.get() not in KIND_OPTIONS:
            self.kind_var.set(KIND_OPTIONS[0])
        self.kind_menu = ctk.CTkOptionMenu(
            kind_col, values=KIND_OPTIONS, variable=self.kind_var,
            font=self.font_normal, dropdown_font=self.font_normal, command=self._on_kind_change
        )
        self.kind_menu.pack(fill="x")

        quality_col = ctk.CTkFrame(options_frame, fg_color="transparent")
        quality_col.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        ctk.CTkLabel(quality_col, text="映像画質", font=self.font_bold, anchor="center").pack(fill="x")
        self.quality_var = ctk.StringVar(value=self.settings.get("quality", QUALITY_OPTIONS[0]))
        if self.quality_var.get() not in QUALITY_OPTIONS:
            self.quality_var.set(QUALITY_OPTIONS[0])
        self.quality_menu = ctk.CTkOptionMenu(
            quality_col, values=QUALITY_OPTIONS, variable=self.quality_var,
            font=self.font_normal, dropdown_font=self.font_normal
        )
        self.quality_menu.pack(fill="x")

        container_col = ctk.CTkFrame(options_frame, fg_color="transparent")
        container_col.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        ctk.CTkLabel(container_col, text="形式", font=self.font_bold, anchor="center").pack(fill="x")
        initial_container_options = container_options_for_kind(self.kind_var.get())
        saved_container = self.settings.get("container", initial_container_options[0])
        if saved_container not in initial_container_options:
            saved_container = initial_container_options[0]
        self.container_var = ctk.StringVar(value=saved_container)
        self.container_menu = ctk.CTkOptionMenu(
            container_col, values=initial_container_options, variable=self.container_var,
            font=self.font_normal, dropdown_font=self.font_normal
        )
        self.container_menu.pack(fill="x")

        self._on_kind_change(self.kind_var.get())

        out_frame = ctk.CTkFrame(self)
        out_frame.pack(fill="x", **pad)
        ctk.CTkLabel(out_frame, text="保存先フォルダ", font=self.font_bold, anchor="center").pack(fill="x", padx=8, pady=(8, 0))
        out_row = ctk.CTkFrame(out_frame, fg_color="transparent")
        out_row.pack(fill="x", padx=8, pady=(0, 8))
        self.output_dir_var = ctk.StringVar(value=self.settings.get("output_dir"))
        self.output_dir_entry = ctk.CTkEntry(out_row, textvariable=self.output_dir_var, font=self.font_normal)
        self.output_dir_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            out_row, text="参照", width=80, font=self.font_normal, command=self._browse_output_dir
        ).pack(side="left", padx=(8, 0))

        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", **pad)
        self.download_button = ctk.CTkButton(
            action_frame, text="ダウンロード開始", font=self.font_bold, command=self._start_download
        )
        self.download_button.pack(side="left")
        self.cancel_button = ctk.CTkButton(
            action_frame, text="キャンセル", font=self.font_normal, fg_color="#b3261e", hover_color="#8c1d17",
            command=self._cancel_download, state="disabled"
        )
        self.cancel_button.pack(side="left", padx=(8, 0))

        progress_frame = ctk.CTkFrame(self)
        progress_frame.pack(fill="x", **pad)
        progress_row = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_row.pack(fill="x", padx=8, pady=(8, 4))
        self.progress_bar = ctk.CTkProgressBar(progress_row)
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.progress_bar.set(0)
        self.percent_label = ctk.CTkLabel(progress_row, text="0%", font=self.font_percent, width=56)
        self.percent_label.pack(side="left", padx=(8, 0))
        self.status_label = ctk.CTkLabel(progress_frame, text="待機中", font=self.font_normal, anchor="center")
        self.status_label.pack(fill="x", padx=8, pady=(0, 8))

        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.pack(fill="x", **pad)
        log_header = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkLabel(log_header, text="ログ", font=self.font_bold).pack(side="left")
        self.show_log_var = ctk.BooleanVar(value=self.settings.get("show_log", False))
        self.log_toggle_button = ctk.CTkButton(
            log_header, text="", width=90, font=self.font_small, command=self._on_log_toggle
        )
        self.log_toggle_button.pack(side="right")
        self.log_box = ctk.CTkTextbox(self.log_frame, font=self.font_normal, state="disabled")
        self._apply_log_visibility(self.show_log_var.get())

        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.pack(fill="x", **pad)

        appearance_col = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        appearance_col.pack(side="left", padx=8, pady=8)
        ctk.CTkLabel(appearance_col, text="テーマ", font=self.font_bold, anchor="center").pack(fill="x")
        self.appearance_var = ctk.StringVar(value=self.settings.get("appearance", APPEARANCE_OPTIONS[0]))
        if self.appearance_var.get() not in APPEARANCE_OPTIONS:
            self.appearance_var.set(APPEARANCE_OPTIONS[0])
        self.appearance_button = ctk.CTkButton(
            appearance_col, text=self.appearance_var.get(), width=120, font=self.font_normal,
            command=self._on_appearance_toggle
        )
        self.appearance_button.pack(fill="x")

        self.auto_open_var = ctk.BooleanVar(value=self.settings.get("auto_open_folder", True))
        self.auto_open_check = ctk.CTkCheckBox(
            bottom_frame, text="完了後に保存先フォルダを自動で開く", font=self.font_normal,
            variable=self.auto_open_var, command=self._on_auto_open_toggle
        )
        self.auto_open_check.pack(side="left", padx=(16, 8), pady=8)

        self.auto_copy_var = ctk.BooleanVar(value=self.settings.get("auto_copy_clipboard", True))
        self.auto_copy_check = ctk.CTkCheckBox(
            bottom_frame, text="完了後にファイルもコピー", font=self.font_normal,
            variable=self.auto_copy_var, command=self._on_auto_copy_toggle
        )
        self.auto_copy_check.pack(side="left", padx=(0, 8), pady=8)

        extra_frame = ctk.CTkFrame(self, fg_color="transparent")
        extra_frame.pack(fill="x", padx=12, pady=(0, 4))

        self.play_sound_var = ctk.BooleanVar(value=self.settings.get("play_complete_sound", True))
        self.play_sound_check = ctk.CTkCheckBox(
            extra_frame, text="完了音を鳴らす", font=self.font_normal,
            variable=self.play_sound_var, command=self._on_play_sound_toggle
        )
        self.play_sound_check.pack(side="left", padx=(4, 8), pady=4)

        ctk.CTkButton(
            extra_frame, text="履歴", width=80, font=self.font_normal, command=self._open_history_window
        ).pack(side="left", padx=(8, 0), pady=4)

        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(footer_frame, text=APP_VERSION, font=self.font_small, text_color="gray60").pack(side="right")
        if is_admin():
            ctk.CTkLabel(footer_frame, text="管理者", font=self.font_small, text_color="gray60").pack(side="left")
        else:
            ctk.CTkButton(
                footer_frame, text="管理者権限で開き直す", width=160, font=self.font_small,
                fg_color="transparent", border_width=1, text_color=("gray20", "gray80"),
                command=self._request_admin
            ).pack(side="left")

    def _on_kind_change(self, value):
        self.quality_menu.configure(state="disabled" if is_audio_only(value) else "normal")

        new_options = container_options_for_kind(value)
        self.container_menu.configure(values=new_options)
        if self.container_var.get() not in new_options:
            self.container_var.set(new_options[0])

    def _apply_log_visibility(self, visible: bool):
        if visible:
            self.log_box.pack(fill="both", expand=True, padx=8, pady=(4, 8))
            self.log_frame.pack_configure(fill="both", expand=True)
        else:
            self.log_box.pack_forget()
            self.log_frame.pack_configure(fill="x", expand=False)
        self.log_toggle_button.configure(text="ログを隠す" if visible else "ログを表示")

    def _on_log_toggle(self):
        new_value = not self.show_log_var.get()
        self.show_log_var.set(new_value)
        self._apply_log_visibility(new_value)
        self.settings["show_log"] = new_value
        save_settings(self.settings)

    def _on_appearance_toggle(self):
        new_value = "ライト" if self.appearance_var.get() == "ダーク" else "ダーク"
        self.appearance_var.set(new_value)
        ctk.set_appearance_mode(_APPEARANCE_MODE_MAP[new_value])
        self.appearance_button.configure(text=new_value)
        self.settings["appearance"] = new_value
        save_settings(self.settings)

    def _on_auto_open_toggle(self):
        self.settings["auto_open_folder"] = self.auto_open_var.get()
        save_settings(self.settings)

    def _on_auto_copy_toggle(self):
        self.settings["auto_copy_clipboard"] = self.auto_copy_var.get()
        save_settings(self.settings)

    def _on_play_sound_toggle(self):
        self.settings["play_complete_sound"] = self.play_sound_var.get()
        save_settings(self.settings)

    def _apply_accent(self):
        fg, hover = ACCENT_COLOR["fg"], ACCENT_COLOR["hover"]
        self.download_button.configure(fg_color=fg, hover_color=hover)
        self.progress_bar.configure(progress_color=fg)
        for menu in (self.kind_menu, self.quality_menu, self.container_menu):
            menu.configure(fg_color=fg, button_color=fg, button_hover_color=hover)

    def _paste_url(self):
        try:
            text = self.clipboard_get()
        except Exception:
            return
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, text.strip())

    def _browse_output_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.output_dir_var.get() or str(Path.home()))
        if chosen:
            self.output_dir_var.set(chosen)

    def _log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{timestamp}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_downloading_state(self, downloading: bool):
        self.is_downloading = downloading
        self.download_button.configure(state="disabled" if downloading else "normal")
        self.cancel_button.configure(state="normal" if downloading else "disabled")

    def _start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self._log("URLを入力してください")
            return

        output_dir = self.output_dir_var.get().strip() or str(Path.home() / "Downloads")
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.status_label.configure(text=f"エラー: 保存先フォルダを作成できません（{exc}）")
            self._log(f"保存先フォルダを作成できません: {output_dir} ({exc})")
            return
        kind = self.kind_var.get()
        quality = self.quality_var.get()
        container = self.container_var.get()

        self.settings.update({"output_dir": output_dir, "kind": kind, "quality": quality, "container": container})
        save_settings(self.settings)
        self.current_output_dir = output_dir
        self._pending_meta = {"url": url, "kind": kind, "quality": quality, "container": container, "title": None}

        self.progress_bar.set(0)
        self.percent_label.configure(text="0%")
        self.status_label.configure(text="情報を取得中...")
        self._log(f"ダウンロード開始: {url}")
        self._set_downloading_state(True)

        thread = threading.Thread(
            target=self._worker, args=(url, output_dir, kind, quality, container), daemon=True
        )
        thread.start()

    def _worker(self, url, output_dir, kind, quality, container):
        try:
            info = self.downloader.probe(url)
        except Exception as exc:
            self.progress_queue.put(("error", f"情報取得に失敗しました: {exc}"))
            return
        target_kind = "プレイリスト" if info["is_playlist"] else "動画"
        self._pending_meta["title"] = info["title"]
        self.progress_queue.put(("status", f"{target_kind}を処理中: {info['title']}"))
        self.downloader.download(url, output_dir, kind, quality, container, info["is_playlist"])

    def _cancel_download(self):
        self.downloader.cancel()
        self.status_label.configure(text="キャンセル中...")

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.progress_queue.get_nowait()
                self._handle_message(kind, payload)
        except queue.Empty:
            pass
        self.after(200, self._poll_queue)

    def _handle_message(self, kind, payload):
        if kind == "status":
            self.status_label.configure(text=payload)
        elif kind == "progress":
            self._update_progress(payload)
        elif kind == "done":
            self.current_output_files = payload or []
            self._finish("ダウンロードが完了しました")
            self._record_history()
            if self.play_sound_var.get():
                play_complete_sound()
            if self.auto_open_var.get():
                self._open_output_dir()
            if self.auto_copy_var.get():
                self._copy_output_files_to_clipboard()
        elif kind == "cancelled":
            self._finish("キャンセルしました")
        elif kind == "error":
            self._finish(f"エラー: {payload}")

    def _update_progress(self, payload):
        percent = payload.get("percent")
        if percent is not None:
            clamped = min(max(percent, 0), 100)
            self.progress_bar.set(clamped / 100)
            self.percent_label.configure(text=f"{clamped:.1f}%")
        speed = payload.get("speed")
        speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "--"
        eta = payload.get("eta")
        eta_str = f"{eta}秒" if eta is not None else "--"
        title = payload.get("title") or ""
        self.status_label.configure(text=f"{title} | {speed_str} | ETA {eta_str}")

    def _finish(self, message: str):
        self.status_label.configure(text=message)
        self._log(message)
        self._set_downloading_state(False)

    def _open_output_dir(self):
        output_dir = getattr(self, "current_output_dir", None)
        if not output_dir or not Path(output_dir).is_dir():
            return
        try:
            os.startfile(output_dir)
        except OSError as exc:
            self._log(f"フォルダを開けませんでした: {exc}")

    def _copy_output_files_to_clipboard(self):
        files = getattr(self, "current_output_files", None)
        if not files:
            self._log("クリップボードへコピーするファイルがありません")
            return
        if copy_files_to_clipboard(files):
            noun = "個のファイル" if len(files) > 1 else ""
            self._log(f"{len(files)}{noun}をクリップボードにコピーしました")
        else:
            self._log("クリップボードへのコピーに失敗しました")

    def _record_history(self):
        meta = getattr(self, "_pending_meta", None)
        if not meta:
            return
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "title": meta.get("title") or "(不明)",
            "url": meta.get("url"),
            "kind": meta.get("kind"),
            "quality": meta.get("quality"),
            "container": meta.get("container"),
            "files": self.current_output_files,
        }
        add_history_entry(entry)

    def _open_history_window(self):
        win = ctk.CTkToplevel(self)
        win.title("ダウンロード履歴")
        win.geometry("640x420")
        win.transient(self)

        header = ctk.CTkFrame(win, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(header, text="ダウンロード履歴", font=self.font_bold).pack(side="left")
        ctk.CTkButton(
            header, text="履歴をクリア", width=100, font=self.font_small,
            fg_color="#b3261e", hover_color="#8c1d17",
            command=lambda: self._clear_history_and_refresh(scroll)
        ).pack(side="right")

        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._populate_history(scroll)

    def _populate_history(self, scroll):
        for child in scroll.winfo_children():
            child.destroy()
        entries = load_history()
        if not entries:
            ctk.CTkLabel(
                scroll, text="履歴はまだありません", font=self.font_normal, text_color="gray60"
            ).pack(pady=20)
            return
        for entry in entries:
            row = ctk.CTkFrame(scroll)
            row.pack(fill="x", pady=4)

            info_col = ctk.CTkFrame(row, fg_color="transparent")
            info_col.pack(side="left", fill="x", expand=True, padx=8, pady=6)
            ctk.CTkLabel(
                info_col, text=entry.get("title") or "(不明)", font=self.font_normal, anchor="w", justify="left"
            ).pack(fill="x")
            sub = (
                f"{entry.get('timestamp', '')} | {entry.get('kind', '')} "
                f"{entry.get('quality', '')} {entry.get('container', '')}"
            ).replace("  ", " ")
            ctk.CTkLabel(info_col, text=sub, font=self.font_small, text_color="gray60", anchor="w").pack(fill="x")

            files = entry.get("files") or []
            btn_col = ctk.CTkFrame(row, fg_color="transparent")
            btn_col.pack(side="right", padx=8, pady=6)
            ctk.CTkButton(
                btn_col, text="開く", width=60, font=self.font_small,
                command=lambda f=files: self._open_history_folder(f)
            ).pack(side="left", padx=(0, 4))
            ctk.CTkButton(
                btn_col, text="コピー", width=60, font=self.font_small,
                command=lambda f=files: self._copy_history_files(f)
            ).pack(side="left")

    def _open_history_folder(self, files):
        if not files:
            return
        folder = str(Path(files[0]).parent)
        if Path(folder).is_dir():
            try:
                os.startfile(folder)
            except OSError:
                pass

    def _copy_history_files(self, files):
        copy_files_to_clipboard(files)

    def _clear_history_and_refresh(self, scroll):
        clear_history()
        self._populate_history(scroll)

    def _on_close(self):
        if self.is_downloading:
            self.downloader.cancel()
        self.destroy()

    def _request_admin(self):
        if self.is_downloading:
            self.downloader.cancel()
        if relaunch_as_admin():
            self.after(400, lambda: os._exit(0))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
