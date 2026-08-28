# -*- mode: python ; coding: utf-8 -*-
# 軽量アップデーター（既にインストール済みの本体exeを最新版に差し替えるだけの単体ツール）。
# yt_dlp/customtkinter等は使わず標準ライブラリのみなので、yt-dlp-YYY.exeよりずっと小さい。

a = Analysis(
    ["updater.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="yt-dlp-YYY-Updater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icons/rounded_y_logo.ico",
)
