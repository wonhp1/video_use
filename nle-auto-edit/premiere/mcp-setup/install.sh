#!/usr/bin/env bash
#
# premiere-mcp-claude-fix / install.sh  (macOS)
#
# premiere-pro-mcp(npm) 를 Claude 와 연결할 때 Premiere 2025/2026(CEP 12)에서
# 발생하는 "evalScript 가 항상 undefined" 버그를 패치하고, 필요한 설정을 적용한다.
#
# 사전 준비 (이 스크립트 실행 전에):
#   1) npm install -g premiere-pro-mcp
#   2) premiere-pro-mcp --install-cep
#
# 사용법:
#   bash install.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
say()  { printf "\033[1;36m▸ %s\033[0m\n" "$1"; }
ok()   { printf "\033[1;32m  ✓ %s\033[0m\n" "$1"; }
warn() { printf "\033[1;33m  ! %s\033[0m\n" "$1"; }
err()  { printf "\033[1;31m  ✗ %s\033[0m\n" "$1"; }

# ── 0. 경로 해석 ──────────────────────────────────────────────────────────────
say "premiere-pro-mcp 설치 경로 확인"
if ! command -v node >/dev/null 2>&1; then err "node 가 설치돼 있지 않습니다."; exit 1; fi
NODE_BIN="$(command -v node)"
NPM_ROOT="$(npm root -g)"
PKG="$NPM_ROOT/premiere-pro-mcp"
CEP_PLUGIN="$PKG/cep-plugin"
INDEX_JS="$PKG/dist/index.js"

if [ ! -d "$PKG" ]; then
  err "premiere-pro-mcp 가 전역 설치돼 있지 않습니다."
  echo "    먼저 실행하세요:  npm install -g premiere-pro-mcp  &&  premiere-pro-mcp --install-cep"
  exit 1
fi
if [ ! -d "$CEP_PLUGIN" ]; then
  err "CEP 플러그인 폴더가 없습니다: $CEP_PLUGIN"
  echo "    먼저 실행하세요:  premiere-pro-mcp --install-cep"
  exit 1
fi
ok "패키지: $PKG"
ok "CEP 플러그인: $CEP_PLUGIN"

# ── 1. CSInterface.js 패치 (핵심) ────────────────────────────────────────────
say "CSInterface.js 확인 (CEP 12 비동기 콜백 버그)"
TARGET_CSI="$CEP_PLUGIN/CSInterface.js"
# 1.13.0 부터는 업스트림에 수정이 반영됐다. 무조건 덮어쓰면 신버전을 구버전으로 되돌린다.
# 콜백이 __adobe_cep__.evalScript 로 넘어가는지만 보고 필요할 때만 패치한다.
if grep -qE '__adobe_cep__\.evalScript\(script,\s*callback' "$TARGET_CSI" 2>/dev/null; then
  ok "이미 수정된 버전 — 패치 불필요"
else
  if [ -f "$TARGET_CSI" ] && [ ! -f "$TARGET_CSI.orig-backup" ]; then
    cp "$TARGET_CSI" "$TARGET_CSI.orig-backup"
    ok "원본 백업: $TARGET_CSI.orig-backup"
  fi
  cp "$SCRIPT_DIR/patches/CSInterface.js" "$TARGET_CSI"
  ok "패치 적용됨: $TARGET_CSI"
fi

# ── 2. manifest.xml 패치 (--enable-nodejs / --mixed-context) ─────────────────
say "설치된 CEP 확장에 동기화"
# --install-cep 은 패키지의 cep-plugin 을 복사한다. 순서에 따라 패치 전 원본이 복사될 수 있어
# 실제로 Premiere 가 읽는 쪽을 다시 맞춘다.
CEP_DEST="$HOME/Library/Application Support/Adobe/CEP/extensions/MCPBridgeCEP"
if [ -d "$CEP_DEST" ]; then
  cp "$CEP_PLUGIN/CSInterface.js" "$CEP_DEST/CSInterface.js"
  ok "동기화: $CEP_DEST/CSInterface.js"
else
  warn "CEP 확장이 아직 설치되지 않았습니다 — premiere-pro-mcp --install-cep 을 먼저 실행하세요"
fi

say "manifest.xml 패치 (Node.js 파일입출력 활성화)"
MANIFEST="$CEP_PLUGIN/CSXS/manifest.xml"
if [ ! -f "$MANIFEST" ]; then err "manifest 를 찾을 수 없습니다: $MANIFEST"; exit 1; fi
[ -f "$MANIFEST.orig-backup" ] || cp "$MANIFEST" "$MANIFEST.orig-backup"
python3 - "$MANIFEST" <<'PY'
import sys, re
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
need = ["--enable-nodejs", "--mixed-context"]
add = [f"            <Parameter>{n}</Parameter>" for n in need if n not in s]
if add and "<CEFCommandLine>" in s:
    s = s.replace("</CEFCommandLine>", "\n".join(add) + "\n          </CEFCommandLine>", 1)
    open(p, "w", encoding="utf-8").write(s)
    print("  ✓ Node.js 파라미터 추가됨")
elif not add:
    print("  ✓ 이미 적용돼 있음")
else:
    print("  ! <CEFCommandLine> 블록이 없어 수동 확인 필요")
PY

# ── 3. PlayerDebugMode (서명 안 된 확장 로딩 허용) ────────────────────────────
say "PlayerDebugMode 활성화 (서명 없는 CEP 확장 로딩 허용)"
for v in 9 10 11 12 13 14; do
  defaults write "com.adobe.CSXS.$v" PlayerDebugMode 1 2>/dev/null || true
done
ok "CSXS.9 ~ CSXS.14 PlayerDebugMode=1"

# ── 4. Claude Desktop 설정 등록 ──────────────────────────────────────────────
say "Claude Desktop 설정 등록 (unsafe-script 포함)"
CLAUDE_CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
TEMP_DIR="/tmp/premiere-mcp-bridge"
mkdir -p "$TEMP_DIR"

if [ -f "$CLAUDE_CFG" ]; then
  cp "$CLAUDE_CFG" "$CLAUDE_CFG.backup-$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
fi
CLAUDE_CODE_CFG="$HOME/.claude.json"
NODE_BIN="$NODE_BIN" INDEX_JS="$INDEX_JS" TEMP_DIR="$TEMP_DIR" \
CLAUDE_CFG="$CLAUDE_CFG" CLAUDE_CODE_CFG="$CLAUDE_CODE_CFG" python3 - <<'PY'
import json, os

# 🚨 1.13.0 부터 execute_extendscript 는 기본 차단이다.
#    unsafe-script 를 명시하지 않으면 모든 편집이 CAPABILITY_DENIED 로 실패한다.
CAPS = "inspect,edit,export,filesystem,unsafe-script"
entry = {
    "command": os.environ["NODE_BIN"],
    "args": [os.environ["INDEX_JS"]],
    "env": {
        "PREMIERE_TEMP_DIR": os.environ["TEMP_DIR"],
        "PREMIERE_MCP_CAPABILITIES": CAPS,
        "DEBUG": "0",
    },
}

for key, label in (("CLAUDE_CFG", "Claude Desktop"), ("CLAUDE_CODE_CFG", "Claude Code")):
    cfg_path = os.environ[key]
    # Claude Code 설정은 이미 있을 때만 건드린다(없으면 만들지 않는다)
    if key == "CLAUDE_CODE_CFG" and not os.path.exists(cfg_path):
        print(f"  · {label}: 설정 파일이 없어 건너뜀")
        continue
    try:
        cfg = json.load(open(cfg_path, encoding="utf-8")) if os.path.exists(cfg_path) else {}
    except Exception:
        cfg = {}
    cfg.setdefault("mcpServers", {})["premiere-pro"] = dict(entry)
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"  ✓ {label} 등록 완료: {cfg_path}")
print("  ✓ capabilities:", CAPS)
PY

# ── 5. 진단 패널 설치 (선택) ─────────────────────────────────────────────────
say "진단 패널(EvalTest) 설치 — evalScript 동작 확인용"
EVAL_SRC="$SCRIPT_DIR/diagnostic/EvalCheckPanel"
EVAL_DST="$HOME/Library/Application Support/Adobe/CEP/extensions/EvalCheckPanel"
if [ -d "$EVAL_SRC" ]; then
  rm -rf "$EVAL_DST"; mkdir -p "$EVAL_DST"
  cp -R "$EVAL_SRC/." "$EVAL_DST/"
  ok "설치됨: Window > Extensions > EvalTest"
else
  warn "진단 패널 소스 없음(건너뜀)"
fi

echo ""
say "완료! 다음 단계:"
echo "  1) Claude Desktop 완전 종료(Cmd+Q) 후 재실행"
echo "  2) Premiere Pro 완전 종료(Cmd+Q) 후 재실행 → 프로젝트/시퀀스 열기"
echo "  3) Premiere: Window > Extensions > MCP Bridge"
echo "     Temp Directory = $TEMP_DIR  →  Save Config  →  Start Bridge"
echo "  4) 로그에 'Premiere Pro: <버전>' 이 뜨면 성공 (Could not detect 아님)"
echo "  5) (선택) Window > Extensions > EvalTest 로 evalScript 동작 확인"
