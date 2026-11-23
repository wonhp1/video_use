# nle-auto-edit 설치 (Windows) — Premiere 스킬과 필요한 도구를 설치한다
# 실행: powershell -ExecutionPolicy Bypass -File nle-auto-edit\install.ps1
# 설치 명령은 원본(wonhp1/claude-premiere-auto-edit)이 Windows 11에서 검증한 안내를 따랐다.
# 이 스크립트 자체는 아직 Windows에서 실행해 보지 않았다.
# 한글이 들어 있으므로 BOM 붙은 UTF-8로 저장해야 Windows PowerShell 5.1이 깨뜨리지 않는다.
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Dest = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { Join-Path $env:USERPROFILE ".claude\skills" }
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

function Has($Cmd) { [bool](Get-Command $Cmd -ErrorAction SilentlyContinue) }

# Microsoft Store 바로가기(WindowsApps\python.exe)는 진짜 Python이 아니다
function Has-Python {
  $c = Get-Command python -ErrorAction SilentlyContinue
  return [bool]($c -and $c.Source -notlike "*\WindowsApps\*")
}

function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

function Install-Skill($Src, $Name) {
  $target = Join-Path $Dest $Name
  if (Test-Path $target) { Remove-Item -Recurse -Force $target }
  Copy-Item -Recurse $Src $target
  Get-ChildItem -Path $target -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
  Write-Host "  [OK] $Name"
}

function Winget-Install($Name, $Id, [scriptblock]$Check) {
  if (& $Check) { Write-Host "  [OK] $Name"; return }
  if (-not (Has "winget")) { Write-Host "  [X] $Name 없음 -> winget install $Id"; return }
  Write-Host "  ... $Name 설치 중 (winget install $Id)"
  winget install --id $Id -e --accept-source-agreements --accept-package-agreements | Out-Null
  Refresh-Path
  if (& $Check) { Write-Host "  [OK] $Name" } else { Write-Host "  [X] $Name 설치 실패 -> 새 PowerShell 창에서 다시 실행하세요" }
}

Write-Host "설치 위치: $Dest"
Write-Host ""
Write-Host "스킬"
Install-Skill (Join-Path $Here "premiere\windows")   "premiere-auto-edit"
Install-Skill (Join-Path $Here "premiere\mcp-setup") "premiere-mcp-setup"

Write-Host ""
Write-Host "필요한 도구"
Winget-Install "node"   "OpenJS.NodeJS.LTS"   { Has "node" }
if (Has "node") {
  $major = [int](node -p "process.versions.node.split('.')[0]")
  if ($major -lt 22) { Write-Host "  [!] node $(node -v) - 22 이상이 필요합니다 (winget upgrade OpenJS.NodeJS.LTS)" }
}
Winget-Install "ffmpeg" "Gyan.FFmpeg"         { Has "ffmpeg" }
Winget-Install "python" "Python.Python.3.12"  { Has-Python }

# faster-whisper 1.2.1은 PyAV 16 이상에서 실패한다. imageio-ffmpeg는 PATH에 ffmpeg가 없을 때 쓴다.
if (Has-Python) {
  python -c "import sys, av, faster_whisper, imageio_ffmpeg; sys.exit(int(av.__version__.split('.')[0]) >= 16)" 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] faster-whisper"
  } else {
    Write-Host "  ... faster-whisper 설치 중 (python -m pip install faster-whisper `"av<16`" imageio-ffmpeg)"
    python -m pip install --quiet faster-whisper "av<16" imageio-ffmpeg
    if ($LASTEXITCODE -eq 0) { Write-Host "  [OK] faster-whisper (받아쓰기 모델은 처음 자막을 만들 때 내려받습니다)" }
    else { Write-Host "  [X] faster-whisper 설치 실패 - Visual C++ 재배포 패키지가 필요할 수 있습니다" }
  }
}

Write-Host ""
Write-Host "Premiere 연결 도구"
$premiere = Get-ChildItem (Join-Path $env:ProgramFiles "Adobe") -Directory -Filter "Adobe Premiere Pro*" -ErrorAction SilentlyContinue
if (-not $premiere) {
  Write-Host "  건너뜀: Premiere Pro가 설치돼 있지 않습니다"
} elseif (Has "premiere-pro-mcp.cmd") {
  Write-Host "  [OK] premiere-pro-mcp (새 버전으로 올리려면 Claude에게 `"프리미어 MCP 업데이트해줘`")"
} elseif (-not (Has "npm.cmd")) {
  Write-Host "  [X] npm 없음 - Node를 설치한 뒤 다시 실행하세요"
} else {
  # .ps1 대신 .cmd를 부른다. 기본 실행 정책에서는 npm이 만든 .ps1이 막힌다.
  Write-Host "  ... premiere-pro-mcp 설치 중 (npm install -g premiere-pro-mcp)"
  npm.cmd install -g premiere-pro-mcp | Out-Null
  if ($LASTEXITCODE -eq 0) { Refresh-Path; premiere-pro-mcp.cmd --install-cep }
  if ($LASTEXITCODE -eq 0) { Write-Host "  [OK] premiere-pro-mcp + Premiere 커넥터(CEP)" }
  else { Write-Host "  [X] 설치 실패 - Claude에게 `"프리미어 MCP 설치해줘`"라고 하면 원인부터 점검합니다" }
}

Write-Host ""
Write-Host "완료. Claude를 재시작하면 스킬이 로드됩니다."
Write-Host "프리미어 스킬은 프리미어를 이름으로 말할 때만 동작합니다 (예: `"프리미어 무음 잘라줘`")."
Write-Host "Premiere 작업을 할 폴더에서 Claude에게 `"프리미어 연결해줘`"라고 하면 Claude Code 등록과 연결 확인까지 합니다."
