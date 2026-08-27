# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

for pkg in ("yt_dlp", "yt_dlp_ejs", "customtkinter"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

binaries += [
    ("vendor/ffmpeg/ffmpeg.exe", "ffmpeg"),
    ("vendor/ffmpeg/ffprobe.exe", "ffmpeg"),
]

datas += [
    ("assets/fonts/NotoSansJP-Regular.ttf", "assets/fonts"),
    ("assets/fonts/NotoSansJP-Bold.ttf", "assets/fonts"),
    ("assets/icons/rounded_y_logo.ico", "assets/icons"),
]

a = Analysis(
    ["app/main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="yt-dlp-YYY",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icons/rounded_y_logo.ico",
    version="version_info.txt",
)
