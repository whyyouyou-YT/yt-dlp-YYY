# yt-dlp-YYY (v1.5.5.1)

yt-dlpを使ってYouTubeの動画+音声をダウンロードするGUIソフト。`dist/yt-dlp-YYY.exe` を実行するだけで、Python/ffmpegなどの追加環境構築なしにダウンロードできる。

## 使い方(配布されたexeを使う場合)

1. `yt-dlp-YYY.exe` をダブルクリックして起動する
2. URLを入力(「貼り付け」ボタンでクリップボードから貼り付け可)
3. 種別(映像+音声/映像のみ/音声のみ)・映像画質(最高品質/1080p/720p/480p、音声のみ選択時は無効)・形式(映像系はmp4/mkv、音声のみはmp3/wav/m4a)を選択。「映像+音声」は同梱のFFmpegで映像と音声を結合する
4. 保存先フォルダを選択(初期値は `ダウンロード/yt-dlp-YYY`)
5. 「ダウンロード開始」を押す。進捗バー・%表示・速度・ETAが表示される
6. プレイリストURLを入れた場合は自動でプレイリスト全体をダウンロードし、プレイリスト名のフォルダにまとめて保存する
7. ダウンロード完了後、「完了後に保存先フォルダを自動で開く」がオンになっていれば保存先フォルダが自動で開く(ログ下部のチェックボックスでオン/オフ切り替え可能)
8. 同時に「完了後にファイルもコピー」がオンになっていれば、ダウンロードしたmp3/mp4ファイル本体がクリップボードにコピーされる(エクスプローラーやDiscord等に`Ctrl+V`でそのまま貼り付け可能。プレイリストの場合は全ファイルをまとめてコピー)
9. 「完了音を鳴らす」がオンになっていれば、完了時にWindows標準の通知音(MessageBeep)が鳴る(オン/オフ切り替え可)
10. 「履歴」ボタンから過去のダウンロード履歴(タイトル・日時・種別/画質/形式)を一覧できる。各行の「開く」で保存先フォルダを再度開け、「コピー」でそのダウンロード時のファイルを再度クリップボードにコピーできる。「履歴をクリア」で全削除可能(最大200件まで自動保持、`%APPDATA%/yt-dlp-YYY/history.json`に保存)
11. テーマ(ダーク/ライト)はログ下部のボタンでトグル切り替え可能(デフォルトはダーク、次回起動時も前回の設定を引き継ぐ)
12. ログ欄はヘッダー右の「ログを表示/隠す」ボタンで表示・非表示を切り替え可能(デフォルトは非表示、次回起動時も前回の設定を引き継ぐ)
13. 現在のバージョンはウィンドウ右下とタイトルバーに表示される(`v1.5.5.1`)

UIフォントはNoto Sans JP(`assets/fonts/`に同梱、実行時にWindowsへ一時登録)。

同梱している第三者ソフトウェア(ffmpeg/yt-dlp/yt-dlp-ejs/CustomTkinter/Noto Sans JP)のライセンス表記は`LICENSES.txt`にまとめている。インストーラー経由でインストールした場合、`LICENSES.txt`と`LICENSE-ffmpeg-GPLv3.txt`がインストール先フォルダにコピーされる。

## 開発環境での実行

```
pip install -r requirements.txt
python app/main.py
```

## exeのビルド方法

0. バージョンを上げる場合は、リリース前に以下3箇所を揃えて更新する
   - `app/main.py` の `APP_VERSION`
   - `installer.iss` の `MyAppVersion`
   - `version_info.txt` の `filevers`/`prodvers`/`FileVersion`/`ProductVersion`
1. `vendor/ffmpeg/ffmpeg.exe` と `vendor/ffmpeg/ffprobe.exe` を配置する
   (Windows用静的ビルド: https://www.gyan.dev/ffmpeg/builds/ の essentials build から `bin/ffmpeg.exe` と `bin/ffprobe.exe` を取得)
2. 依存パッケージをインストール

   ```
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. ビルド

   ```
   python -m PyInstaller build.spec --noconfirm
   ```

4. `dist/yt-dlp-YYY.exe` が生成される。このexe単体を配布すれば、Python/ffmpegの追加インストールなしに動作する

## インストーラーのビルド方法

Inno Setup 6が必要(`winget install --id JRSoftware.InnoSetup -e`で導入可能)。

1. 上記の手順で `dist/yt-dlp-YYY.exe` をビルド済みにする
2. `installer.iss` の `MyAppVersion` を必要に応じて更新する
3. コンパイル

   ```
   "C:\Users\<ユーザー名>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
   ```

4. `installer_dist\yt-dlp-YYY-Setup-v<バージョン>.exe` が生成される。スタートメニュー登録・デスクトップアイコン任意作成・アンインストーラー付き

## アップデーターのビルド方法（既にインストール済みの人向け）

フルインストーラー（ffmpeg等を含み数十MB）を落とし直さず、本体exeだけを最新版に差し替える軽量ツール。
yt_dlp/customtkinter等は使わず標準ライブラリのみなので `dist/yt-dlp-YYY.exe` よりずっと軽い。

```
python -m PyInstaller updater.spec --noconfirm
```

`dist/yt-dlp-YYY-Updater.exe` が生成される。GitHub Release に本体exe・インストーラーと
並べてアップロードする。

**使い方（利用者側）**: `yt-dlp-YYY-Updater.exe` をそのまま実行するだけ。インストール先は
レジストリのアンインストール情報から自動検出し、GitHub の最新Releaseから本体exeだけを
ダウンロードして上書きする。実行中は置き換えできないため、事前にアプリを閉じておくこと。
書き込み権限が無い場合は自動的に管理者権限で再起動する。

### リポジトリがPrivateの間のアクセス（知り合いに使ってもらう場合）

このリポジトリは現在Privateのため、GitHub Releases APIへの匿名アクセスは404になる。
知り合いにアップデーターを使ってもらうには、読み取り専用スコープのアクセストークンを
発行して渡す必要がある。

1. GitHubの [Settings > Developer settings > Fine-grained tokens](https://github.com/settings/tokens?type=beta) で新規発行
   - Repository access: `Only select repositories` → `yt-dlp-YYY` のみ選択
   - Permissions: `Contents` を `Read-only` に設定（それ以外は付与しない）
   - 有効期限は必要に応じて短めに設定（失効すればいつでも同じ手順で再発行できる）
2. 発行されたトークン文字列（`github_pat_...`）を、渡したい相手にDiscord DM等の安全な経路で共有する
3. 相手は `yt-dlp-YYY-Updater.exe` と同じフォルダに `token.txt` という名前のテキストファイルを作り、
   トークンだけを1行貼り付けて保存してから実行する（環境変数 `YT_DLP_YYY_UPDATER_TOKEN` でも可）
4. リポジトリを将来Publicにした場合は `token.txt` は不要になる（無くてもそのまま動く）

トークンはリポジトリ単位・読み取り専用でスコープを絞ってあるため、漏れても実害は小さいが、
不要になったらGitHub側でいつでも失効させること。

## ディレクトリ構成

```
app/
  main.py        GUI本体 (CustomTkinter)
  downloader.py  yt-dlpラッパー・進捗フック・画質マッピング・完了後の出力ファイル一覧収集
  clipboard.py   Windowsクリップボードへのファイルコピー (CF_HDROP、ctypes直叩き・pywin32不要)
  history.py     ダウンロード履歴の保存/読込/クリア (%APPDATA%/yt-dlp-YYY/history.json、最大200件)
  sound.py       完了通知音の再生 (winsound.MessageBeep)
  settings.py    設定の保存/読込 (%APPDATA%/yt-dlp-YYY/settings.json、テーマ設定も含む)
  fonts.py       Noto Sansのランタイム登録 (GDIへ一時フォント登録)
vendor/ffmpeg/   同梱用ffmpeg.exe / ffprobe.exe (gitには含めない想定) / LICENSE.txt (GPLv3全文)
assets/fonts/    同梱用Noto Sans (Regular/Bold, OFL.txt)
assets/icons/    実行ファイルアイコン (rounded_y_logo.ico)
build.spec       PyInstaller設定 (ffmpeg・フォント・アイコン・バージョンリソース同梱・単一exe・コンソール非表示)
version_info.txt exeのバージョンリソース定義 (会社名/製品名/バージョン等、リリースごとに更新)
installer.iss    Inno Setupインストーラー定義
updater.py / updater.spec 既存インストールを最新Releaseの本体exeに差し替える軽量アップデーター。標準ライブラリのみで完結
LICENSES.txt     同梱している第三者ソフトウェア・フォントのライセンス表記
```
