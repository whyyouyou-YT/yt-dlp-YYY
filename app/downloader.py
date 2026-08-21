import queue
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

import yt_dlp

from app.settings import app_data_dir

PROJECT_ROOT = Path(__file__).resolve().parent.parent

KIND_OPTIONS = ["映像+音声", "映像のみ", "音声のみ"]
QUALITY_OPTIONS = ["最高品質", "1080p", "720p", "480p"]
VIDEO_CONTAINER_OPTIONS = ["mp4", "mkv"]
AUDIO_CONTAINER_OPTIONS = ["mp3", "wav", "m4a"]

_HEIGHT_BY_QUALITY = {"1080p": 1080, "720p": 720, "480p": 480}

# yt-dlp 2026.8 以降、YouTube の署名解読・n チャレンジ解決には外部 JS ランタイムが必要。
# 既定では deno しか自動検出されないため、利用者の環境にありうるものを広く有効化する
# （どれも見つからない場合でも既定クライアントなら通常はダウンロード可能）。
JS_RUNTIMES = {"deno": {}, "node": {}, "bun": {}, "quickjs": {}}

# 403 等で失敗したときに順に切り替える YouTube クライアント。
# None = yt-dlp の既定（visionos 等）。以降は画質が下がる可能性のある保険。
PLAYER_CLIENT_FALLBACKS = [None, "web_embedded", "android"]

# クライアントを変えれば成功しうるエラーの目印
_RETRYABLE_MARKERS = (
    "http error 403",
    "http error 429",
    "unable to download video data",
    "requested format is not available",
    "sign in to confirm",
    "the page needs to be reloaded",
    "failed to extract any player response",
    "please report this issue",
)


class DownloadCancelled(Exception):
    pass


def get_ffmpeg_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "ffmpeg"
    return PROJECT_ROOT / "vendor" / "ffmpeg"


def error_log_path() -> Path:
    return app_data_dir() / "logs" / "error.log"


def log_error(context: str, exc: BaseException) -> None:
    """例外をユーザーデータ領域のログファイルに追記する（失敗しても本処理は止めない）。"""
    try:
        path = error_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} | {context} =====\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except OSError:
        pass


def is_retryable_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _RETRYABLE_MARKERS)


def is_audio_only(kind: str) -> bool:
    return kind == "音声のみ"


def container_options_for_kind(kind: str) -> list:
    return AUDIO_CONTAINER_OPTIONS if is_audio_only(kind) else VIDEO_CONTAINER_OPTIONS


def build_format_and_postprocessors(kind: str, quality: str, container: str):
    if is_audio_only(kind):
        format_str = "bestaudio/best"
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": container,
                "preferredquality": "192",
            }
        ]
        return format_str, postprocessors, None

    height = _HEIGHT_BY_QUALITY.get(quality)

    if kind == "映像のみ":
        format_str = f"bestvideo[height<={height}]" if height else "bestvideo"
        postprocessors = [{"key": "FFmpegVideoConvertor", "preferedformat": container}]
        return format_str, postprocessors, None

    if height:
        format_str = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
    else:
        format_str = "bestvideo+bestaudio/best"
    return format_str, [], container


def common_opts(player_client=None) -> dict:
    """全 yt-dlp 呼び出しで共通に使うオプション。"""
    opts = {
        "ffmpeg_location": str(get_ffmpeg_dir()),
        "js_runtimes": dict(JS_RUNTIMES),
        "quiet": True,
        "no_warnings": True,
    }
    if player_client:
        opts["extractor_args"] = {"youtube": {"player_client": [player_client]}}
    return opts


def _normalize_progress(d: dict) -> dict:
    status = d.get("status")
    info = d.get("info_dict") or {}
    total = d.get("total_bytes") or d.get("total_bytes_estimate")
    downloaded = d.get("downloaded_bytes")
    percent = None
    if total and downloaded is not None:
        percent = downloaded / total * 100
    return {
        "status": status,
        "percent": percent,
        "speed": d.get("speed"),
        "eta": d.get("eta"),
        "title": info.get("title") or d.get("filename"),
        "filename": d.get("filename"),
    }


class Downloader:
    def __init__(self, progress_queue: "queue.Queue"):
        self.progress_queue = progress_queue
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    def reset_cancel(self):
        self._cancel_event.clear()

    def probe(self, url: str) -> dict:
        opts = common_opts()
        opts.update(
            {
                "skip_download": True,
                "extract_flat": "in_playlist",
            }
        )
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        is_playlist = bool(info.get("entries"))
        return {
            "is_playlist": is_playlist,
            "title": info.get("title") or "video",
            "entry_count": len(info.get("entries") or []) if is_playlist else 1,
        }

    def _progress_hook(self, d: dict):
        if self._cancel_event.is_set():
            raise DownloadCancelled("ユーザーによりキャンセルされました")
        self.progress_queue.put(("progress", _normalize_progress(d)))

    def _build_download_opts(self, url_output, kind, quality, container, is_playlist, player_client):
        format_str, postprocessors, merge_format = build_format_and_postprocessors(kind, quality, container)

        opts = common_opts(player_client)
        opts.update(
            {
                "format": format_str,
                "outtmpl": url_output,
                "postprocessors": postprocessors,
                "progress_hooks": [self._progress_hook],
                "noplaylist": not is_playlist,
                "ignoreerrors": is_playlist,
            }
        )
        if merge_format:
            opts["merge_output_format"] = merge_format
        return opts

    def download(self, url: str, output_dir: str, kind: str, quality: str, container: str, is_playlist: bool):
        self.reset_cancel()

        if is_playlist:
            outtmpl = str(Path(output_dir) / "%(playlist_title)s" / "%(title)s.%(ext)s")
        else:
            outtmpl = str(Path(output_dir) / "%(title)s.%(ext)s")

        last_error = None
        for attempt, player_client in enumerate(PLAYER_CLIENT_FALLBACKS):
            if self._cancel_event.is_set():
                self.progress_queue.put(("cancelled", None))
                return

            opts = self._build_download_opts(outtmpl, kind, quality, container, is_playlist, player_client)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                self.progress_queue.put(("done", self._collect_output_files(info)))
                return
            except DownloadCancelled:
                self.progress_queue.put(("cancelled", None))
                return
            except Exception as exc:  # yt-dlp can raise various error types
                last_error = exc
                label = player_client or "既定"
                log_error(f"download(client={label})", exc)

                has_next = attempt < len(PLAYER_CLIENT_FALLBACKS) - 1
                if has_next and is_retryable_error(exc):
                    next_label = PLAYER_CLIENT_FALLBACKS[attempt + 1] or "既定"
                    self.progress_queue.put(
                        ("status", f"取得に失敗したため別方式({next_label})で再試行しています…")
                    )
                    continue
                break

        self.progress_queue.put(("error", self._format_error(last_error)))

    @staticmethod
    def _format_error(exc) -> str:
        if exc is None:
            return "不明なエラーが発生しました"
        message = str(exc)
        if "403" in message:
            message = (
                "YouTube側にアクセスを拒否されました（403）。"
                "yt-dlpの更新で解消する場合があります"
            )
        return f"{message}\n詳細ログ: {error_log_path()}"

    @staticmethod
    def _collect_output_files(info: dict) -> list:
        if not info:
            return []
        entries = info.get("entries")
        entries = entries if entries is not None else [info]
        files = []
        for entry in entries:
            if not entry:
                continue
            for requested in entry.get("requested_downloads") or []:
                filepath = requested.get("filepath")
                if filepath and Path(filepath).exists():
                    files.append(filepath)
        return files
