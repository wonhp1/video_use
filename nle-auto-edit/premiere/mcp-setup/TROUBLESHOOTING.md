# 문제 해결 (증상별)

우리가 실제로 겪은 함정들을 순서대로 정리했습니다.

## 1. 로그에 `Could not detect Premiere Pro version` (빨간 글씨)

가장 흔한 증상. **CSInterface.js 패치가 안 먹은 것.**

- `bash install.sh` 를 실행했는가?
- Premiere 를 **완전히 종료(⌘Q) 후 재실행**했는가? (CEP 는 시작 시 한 번만 파일을 읽음 — 패널의 Stop/Start 만으론 안 됨)
- **EvalTest 패널**(Window → Extensions → EvalTest)에서 `1+1` 버튼이 `[2]` 를 주는지 확인.
  - `undefined` 면 패치 미적용 → `install.sh` 재실행 후 Premiere 완전 재시작.

## 2. `Error creating dir: Cannot read properties of undefined (reading 'existsSync')`

manifest 에 `--enable-nodejs` 가 없어서 `require("fs")` 가 안 되는 것.
→ `install.sh` 가 자동 추가함. 안 됐다면 `cep-plugin/CSXS/manifest.xml` 의 `<CEFCommandLine>` 에
`--enable-nodejs`, `--mixed-context` 가 있는지 확인 후 Premiere 완전 재시작.

## 3. MCP 명령이 타임아웃 (`Command timed out`)

MCP Bridge 패널이 **안 켜져 있거나 폴더가 안 맞는 것.**

- Premiere: Window → Extensions → **MCP Bridge** 가 열려 있고 **Start Bridge** 됐는가?
- 패널의 **Temp Directory** 가 `/tmp/premiere-mcp-bridge` 인가?
  - 패널은 켤 때마다 기본값(`/var/folders/.../T/...`)으로 돌아가는 버릇이 있음 →
    `/tmp/premiere-mcp-bridge` 로 바꾸고 **Save Config** 클릭.
- Claude Desktop 설정의 `PREMIERE_TEMP_DIR` 과 패널의 Temp Directory 가 **반드시 동일**해야 함.

## 4. 패널에 응답은 오는데 `data: null` 만 옴

`{"success":true,"data":null}` 형태. → CSInterface.js 패치 전의 전형적 증상.
→ 1번 항목대로 패치 + 완전 재시작.

## 5. MCP 도구 목록에 premiere-pro 가 안 보임

- Claude Desktop 을 **완전 종료(⌘Q) 후 재실행**했는가?
- `claude_desktop_config.json` 에 `premiere-pro` 항목이 있고, `command`(node 경로)·`args`(dist/index.js 경로)가 실제 경로인지 확인.
  - 경로 확인: `command -v node` / `echo $(npm root -g)/premiere-pro-mcp/dist/index.js`

## 6. `add_text_overlay` 가 `Illegal Parameter type` 에러

자막 추가 도구가 Premiere 25.x/26.x 타이틀 API 와 안 맞는 별개 버그.
**연결 자체는 정상**(마커·읽기·execute_extendscript 는 됨). 자막은 다른 방식(직접 ExtendScript 로 타이틀 생성, 또는 MOGRT) 으로 우회 필요.

## 7. 두 버전(2025·2026)을 같이 켰을 때 이상 동작

둘 다 MCP Bridge 를 돌리면 같은 `/tmp/premiere-mcp-bridge` 를 동시에 감시해 충돌.
→ **한 번에 하나만** 실행.

## 8. npm 업데이트 후 갑자기 다시 먹통

`npm update` 가 패치한 CSInterface.js 를 원본으로 덮어쓴 것. → `bash install.sh` 재실행.

---

## 빠른 자가진단 순서

1. EvalTest 패널 `1+1` → `[2]` 나오나? → 안 나오면 **패치/재시작 문제** (1,2번)
2. 나온다면 MCP Bridge 켜져 있고 Temp Dir 맞나? → **연결 문제** (3번)
3. Claude 에 premiere-pro 도구 보이나? → **Claude 설정 문제** (5번)
