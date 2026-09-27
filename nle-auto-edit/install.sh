#!/usr/bin/env bash
# claude-video-auto-edit 설치 — 코어 + 선택한 어댑터를 ~/.claude/skills 에 넣는다
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST"

say() { printf "%s\n" "$*"; }

install_one() {          # install_one <소스디렉터리> <스킬이름>
  local src="$1" name="$2"
  if [ ! -f "$src/SKILL.md" ]; then say "  건너뜀: $name (SKILL.md 없음)"; return; fi
  rm -rf "${DEST:?}/$name"
  mkdir -p "$DEST/$name"
  cp -R "$src/." "$DEST/$name/"
  find "$DEST/$name" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
  say "  ✅ $name"
}

say "설치 위치: $DEST"
say ""
say "공통 뼈대"
install_one "$HERE/core" "ai-video-edit"

say ""
say "어댑터"
TARGETS="${1:-all}"
case "$TARGETS" in
  all|"")
    install_one "$HERE/premiere/mac" "premiere-auto-edit"
    install_one "$HERE/capcut"       "capcut-auto-edit"
    install_one "$HERE/finalcut"     "finalcut-auto-edit"
    ;;
  *)
    for t in $TARGETS; do
      case "$t" in
        premiere)         install_one "$HERE/premiere/mac"     "premiere-auto-edit" ;;
        premiere-windows) install_one "$HERE/premiere/windows" "premiere-auto-edit" ;;
        capcut)           install_one "$HERE/capcut"           "capcut-auto-edit" ;;
        finalcut)         install_one "$HERE/finalcut"         "finalcut-auto-edit" ;;
        *) say "  알 수 없는 대상: $t" ;;
      esac
    done
    ;;
esac

say ""
say "필요한 도구 확인"
for c in ffmpeg ffprobe; do
  command -v "$c" >/dev/null && say "  ✅ $c" || say "  ❌ $c  → brew install ffmpeg"
done
if python3 -c "import faster_whisper" 2>/dev/null; then
  say "  ✅ faster-whisper"
else
  say "  ⚠️  faster-whisper 없음 (자막 기능에 필요)"
  say "      pip3 install faster-whisper"
  say "      ※ python3 가 anaconda 면 시스템 python 에 설치해야 한다"
fi

say ""
say "Premiere 를 쓰려면 MCP 등록과 CEP12 패치가 추가로 필요합니다:"
say "  $HERE/premiere/mcp-setup/install.sh"
say ""
say "Final Cut 을 쓰려면 fcp-mcp 를 등록하세요 (mcp<2.0 고정 필수):"
say '  uvx --from fcp-mcp --with "mcp<2.0" fcp-mcp'
say ""
say "완료. Claude 를 재시작하면 스킬이 로드됩니다."
