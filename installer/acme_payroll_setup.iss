; Acme Corporation 급여·인사 — Inno Setup 설치 스크립트
; 빌드: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\acme_payroll_setup.iss
; 사전: pyinstaller payroll.spec → dist\Acme_Payroll.exe 생성

#define MyAppName "Acme Corporation 급여·인사"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Acme Corporation"
#define MyAppExeName "Acme_Payroll.exe"

[Setup]
AppId={{A8F3C2E1-9B4D-4F6A-8C1E-2D5E7F9A0B3C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Acme Corporation\Payroll
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=Acme_Payroll_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면 바로가기 만들기"; GroupDescription: "추가 작업:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs
Source: "..\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "프로그램 실행"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
