#!/usr/bin/env bash
# nle-auto-edit 설치 (macOS) — 코어 + 선택한 어댑터를 ~/.claude/skills 에 넣고, 필요한 도구를 설치한다
# Windows 는 install.ps1 을 쓴다.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
VENV="${NLE_VENV:-$HOME/.local/share/nle-auto-edit/venv}"   # faster-whisper 전용 가상환경
mkdir -p "$DEST"

say() { printf "%s\n" "$*"; }
has() { command -v "$1" >/dev/null 2>&1; }

install_one() {          # install_one <소스디렉터리> <스킬이름>
  local src="$1" name="$2"
  if [ ! -f "$src/SKILL.md" ]; then say "  건너뜀: $name (SKILL.md 없음)"; return; fi
  rm -rf "${DEST:?}/$name"
  mkdir -p "$DEST/$name"
  cp -R "$src/." "$DEST/$name/"
  find "$DEST/$name" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
  say "  ✅ $name"
}

brew_install() {         # brew_install <명령> <brew 패키지>
  if has "$1"; then say "  ✅ $1"; return; fi
  if ! has brew; then say "  ❌ $1 없음 → Homebrew(https://brew.sh) 설치 후 brew install $2"; return; fi
  say "  … $1 설치 중 (brew install $2)"
  if brew install "$2" >/dev/null; then say "  ✅ $1"; else say "  ❌ $1 설치 실패 → brew install $2"; fi
}

setup_whisper() {        # faster-whisper + av<16 (faster-whisper 1.2.1 은 PyAV 16 이상에서 실패한다)
  local py="$VENV/bin/python"
  if [ -x "$py" ] && "$py" -c 'import sys, av, faster_whisper; sys.exit(int(av.__version__.split(".")[0]) >= 16)' 2>/dev/null; then
    say "  ✅ faster-whisper ($VENV)"; return
  fi
  [ -f "$VENV/pyvenv.cfg" ] && rm -rf "$VENV"
  mkdir -p "$(dirname "$VENV")"
  say "  … faster-whisper 설치 중 ($VENV)"
  if has uv; then
    uv venv --quiet --python 3.12 "$VENV" && uv pip install --quiet --python "$py" faster-whisper "av<16"
  elif has python3; then
    python3 -m venv "$VENV" && "$py" -m pip install --quiet --disable-pip-version-check faster-whisper "av<16"
  else
    say "  ❌ python3 없음 → brew install python 후 다시 실행"; return
  fi || { say "  ❌ faster-whisper 설치 실패 — 위 오류를 확인하세요"; return; }
  say "  ✅ faster-whisper ($VENV)"
  say "     받아쓰기 모델은 처음 자막을 만들 때 내려받습니다 (medium 약 1.5GB)"
}

setup_premiere() {       # premiere-pro MCP 서버 + Premiere 커넥터(CEP)
  if ! compgen -G "/Applications/Adobe Premiere Pro*" >/dev/null; then
    say "  건너뜀: Premiere Pro 가 설치돼 있지 않습니다"; return
  fi
  if has premiere-pro-mcp; then
    say "  ✅ premiere-pro-mcp $(npm ls -g premiere-pro-mcp --depth=0 2>/dev/null | sed -n 's/.*premiere-pro-mcp@//p')"
    say "     (새 버전으로 올리려면 Claude 에게 \"프리미어 MCP 업데이트해줘\")"
    return
  fi
  if ! has npm; then say "  ❌ npm 없음 — Node 를 설치한 뒤 다시 실행하세요"; return; fi
  say "  … premiere-pro-mcp 설치 중 (npm install -g premiere-pro-mcp)"
  if npm install -g premiere-pro-mcp >/dev/null && premiere-pro-mcp --install-cep; then
    say "  ✅ premiere-pro-mcp + Premiere 커넥터(CEP)"
  else
    say "  ❌ 설치 실패 — Claude 에게 \"프리미어 MCP 설치해줘\" 라고 하면 원인부터 점검합니다"
  fi
}

say "설치 위치: $DEST"
say ""
say "공통 뼈대"
install_one "$HERE/core" "ai-video-edit"

say ""
say "어댑터"
TARGETS="${*:-all}"
[ "$TARGETS" = "all" ] && TARGETS="premiere capcut finalcut"
PREMIERE=0; FINALCUT=0
for t in $TARGETS; do
  case "$t" in
    premiere)
      install_one "$HERE/premiere/mac"       "premiere-auto-edit"
      install_one "$HERE/premiere/mcp-setup" "premiere-mcp-setup"
      PREMIERE=1 ;;
    premiere-windows) say "  Windows 는 install.ps1 을 쓰세요: powershell -ExecutionPolicy Bypass -File install.ps1" ;;
    capcut)   install_one "$HERE/capcut"   "capcut-auto-edit" ;;
    finalcut) install_one "$HERE/finalcut" "finalcut-auto-edit"; FINALCUT=1 ;;
    *) say "  알 수 없는 대상: $t" ;;
  esac
done

say ""
say "필요한 도구"
if has node; then
  if [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 22 ]; then say "  ✅ node $(node -v)"
  else say "  ⚠️  node $(node -v) — 22 이상이 필요합니다 (brew upgrade node)"; fi
else
  brew_install node node
fi
brew_install ffmpeg ffmpeg
has ffprobe || say "  ⚠️  ffprobe 없음 → brew reinstall ffmpeg"
setup_whisper
if has npx; then
  if npx --yes hyperframes@latest --version >/dev/null 2>&1; then say "  ✅ hyperframes (모션그래픽 렌더, npx 캐시)"
  else say "  ⚠️  hyperframes 를 미리 받지 못했습니다 — 처음 쓸 때 npx 가 받습니다(인터넷 필요)"; fi
fi

if [ "$PREMIERE" = 1 ]; then
  say ""
  say "Premiere 연결 도구"
  setup_premiere
fi

say ""
say "완료. Claude 를 재시작하면 스킬이 로드됩니다."
say "편집 프로그램 스킬은 프로그램 이름을 말할 때만 동작합니다 (예: \"프리미어 무음 잘라줘\", \"캡컷 자막 달아줘\")."
say "이름 없이 \"편집해줘\" 라고 하면 편집 프로그램 없이 처리합니다."
if [ "$PREMIERE" = 1 ]; then
  say ""
  say "Premiere: Premiere 작업을 할 폴더에서 Claude 에게 \"프리미어 연결해줘\" 라고 하세요."
  say "  premiere-mcp-setup 스킬이 Claude Code 등록 → Premiere 켜기 → 연결 확인(overall: ready)까지 합니다."
fi
if [ "$FINALCUT" = 1 ]; then
  say ""
  say "Final Cut 을 쓰려면 fcp-mcp 를 등록하세요 (mcp<2.0 고정 필수):"
  say '  uvx --from fcp-mcp --with "mcp<2.0" fcp-mcp'
fi
