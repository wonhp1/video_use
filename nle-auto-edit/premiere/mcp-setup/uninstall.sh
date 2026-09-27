#!/usr/bin/env bash
#
# premiere-mcp-claude-fix / uninstall.sh  (macOS)
# 패치를 되돌리고 진단 패널을 제거한다. (premiere-pro-mcp 패키지 자체는 안 지움)
#
set -euo pipefail
say()  { printf "\033[1;36m▸ %s\033[0m\n" "$1"; }
ok()   { printf "\033[1;32m  ✓ %s\033[0m\n" "$1"; }
warn() { printf "\033[1;33m  ! %s\033[0m\n" "$1"; }

NPM_ROOT="$(npm root -g 2>/dev/null || echo '')"
CEP_PLUGIN="$NPM_ROOT/premiere-pro-mcp/cep-plugin"

say "CSInterface.js / manifest.xml 원본 복구"
for f in "CSInterface.js" "CSXS/manifest.xml"; do
  tgt="$CEP_PLUGIN/$f"
  if [ -f "$tgt.orig-backup" ]; then
    mv "$tgt.orig-backup" "$tgt"
    ok "복구됨: $f"
  else
    warn "백업 없음(건너뜀): $f"
  fi
done

say "진단 패널(EvalTest) 제거"
EVAL_DST="$HOME/Library/Application Support/Adobe/CEP/extensions/EvalCheckPanel"
[ -d "$EVAL_DST" ] && rm -rf "$EVAL_DST" && ok "제거됨" || warn "없음(건너뜀)"

say "Claude Desktop 에서 premiere-pro 서버 항목 제거"
CLAUDE_CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$CLAUDE_CFG" ]; then
  cp "$CLAUDE_CFG" "$CLAUDE_CFG.backup-$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
  CLAUDE_CFG="$CLAUDE_CFG" python3 - <<'PY'
import json, os
p = os.environ["CLAUDE_CFG"]
try: cfg = json.load(open(p, encoding="utf-8"))
except Exception: cfg = {}
if cfg.get("mcpServers", {}).pop("premiere-pro", None) is not None:
    json.dump(cfg, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("  ✓ premiere-pro 항목 제거됨")
else:
    print("  ! premiere-pro 항목 없음")
PY
fi

echo ""
say "완료. (참고: PlayerDebugMode 와 premiere-pro-mcp 패키지는 그대로 둠)"
echo "  패키지까지 지우려면:  npm uninstall -g premiere-pro-mcp"
