; yt-dlp-YYY インストーラー定義 (Inno Setup)
; ビルド: "C:\Users\yuuma\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss

#define MyAppName "yt-dlp-YYY"
#define MyAppVersion "1.6.0"
#define MyAppExeName "yt-dlp-YYY.exe"
#define MyAppSourceExe "dist\yt-dlp-YYY.exe"

[Setup]
AppId={{9B7E9F3B-7C2C-4F62-9E60-8B7B3E6F0B7A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=yuuma
; Program Files配下(管理者権限が必要)にインストールすると、yt-dlp・子プロセス等の
; 一時ファイル書き込みが標準ユーザー権限では失敗する不具合があったため、
; ユーザー権限だけで書き込める場所を既定インストール先にする。
DefaultDirName={localappdata}\Programs\{#MyAppName}
PrivilegesRequired=lowest
; 旧バージョンでProgram Files配下にインストール済みの環境でも、そのパスを
; 引き継がず必ず上記の新しい既定パスを使う(引き継ぐと権限問題が再発するため)。
UsePreviousAppDir=no
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=installer_dist
OutputBaseFilename=yt-dlp-YYY-Setup-v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
SetupIconFile=assets\icons\rounded_y_logo.ico
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyAppSourceExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\ffmpeg\LICENSE.txt"; DestDir: "{app}"; DestName: "LICENSE-ffmpeg-GPLv3.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
