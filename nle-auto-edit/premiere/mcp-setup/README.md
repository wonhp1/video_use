# Premiere Pro × Claude MCP 연결 키트 (CEP 12 버그 패치 포함)

Claude(또는 Claude Code / Codex 등 MCP 클라이언트)로 **Adobe Premiere Pro 를 직접 제어**하기 위한 설치 키트입니다.
`premiere-pro-mcp`(npm) 를 Premiere **2025 / 2026** 에서 쓸 때 발생하는 치명적 버그를 패치합니다.

> **핵심:** 명령이 프리미어 타임라인에 **실시간으로 반영**됩니다 (마커·효과·클립 편집 등). Premiere 2025(25.5.0)·2026(26.2.2)에서 동작 확인 완료.

---

## 이 키트가 고치는 문제

설치 직후 MCP 명령이 전부 실패하고, MCP Bridge 패널 로그에 빨간 글씨로
**`Warning: Could not detect Premiere Pro version`** 이 뜨는 증상.

**원인:** npm 으로 배포된 `premiere-pro-mcp@1.1.1` 의 `CSInterface.js` 가 잘못된(구버전) 방식으로 작성돼 있습니다.

```js
// ❌ 원본 (항상 undefined 반환)
var result = __adobe_cep__.evalScript(script); // 콜백 없이 동기 호출

// ✅ 패치 (CEP 12 비동기 콜백 방식)
__adobe_cep__.evalScript(script, callback);
```

CEP 12(Premiere 2025/2026)에서 `evalScript` 는 **비동기**라, 콜백을 네이티브 계층에 넘겨야 결과가 옵니다.
원본은 콜백 없이 동기 호출해서 항상 `undefined` 를 받았고, 그 결과 모든 ExtendScript 호출이 실패했습니다.
(참고: GitHub 이슈 [leancoderkavy/premiere-pro-mcp#2](https://github.com/leancoderkavy/premiere-pro-mcp/issues/2))

> ⚠️ 이건 **프리미어 버전·맥 기종·시스템 문제가 아닙니다.** 오직 이 라이브러리 파일 하나입니다.
> "25.6.2 클린설치 버그" 같은 다른 원인설과 헷갈리기 쉬우니 주의하세요.

---

## 사전 준비

| 필요               | 비고                                |
| ------------------ | ----------------------------------- |
| macOS              | (Windows 는 아래 "Windows" 절 참고) |
| Node.js            | `node -v` 로 확인                   |
| Adobe Premiere Pro | 2025(25.x) 또는 2026(26.x)          |
| Claude Desktop     | MCP 클라이언트                      |

```bash
# 1) MCP 서버 + CEP 패널 설치 (공식 패키지)
npm install -g premiere-pro-mcp
premiere-pro-mcp --install-cep
```

---

## 설치 (자동)

```bash
bash install.sh
```

`install.sh` 가 자동으로:

1. **CSInterface.js 패치** (원본은 `*.orig-backup` 으로 백업)
2. **manifest.xml 패치** — `--enable-nodejs` / `--mixed-context` 추가 (Node.js 파일입출력 활성화)
3. **PlayerDebugMode** 활성화 (서명 없는 CEP 확장 로딩 허용)
4. **Claude Desktop 설정**에 `premiere-pro` 서버 등록 (기존 설정 백업 후 병합)
5. **진단 패널(EvalTest)** 설치 (evalScript 동작 확인용)

---

## 설치 후 실행

1. **Claude Desktop** 완전 종료(⌘Q) 후 재실행
2. **Premiere Pro** 완전 종료(⌘Q) 후 재실행 → 프로젝트 + **시퀀스(타임라인)** 열기
3. Premiere: **Window → Extensions → MCP Bridge**
   - Temp Directory = `/tmp/premiere-mcp-bridge` → **Save Config** → **Start Bridge**
   - 로그에 **`Premiere Pro: 25.5.0`** 처럼 버전이 뜨면 성공 ✅
4. Claude 에서 "지금 열린 시퀀스 정보 알려줘" 같은 명령으로 확인

> 💡 **두 버전을 동시에 켜지 마세요.** 2025·2026 둘 다 Bridge 를 돌리면 같은 폴더(`/tmp/premiere-mcp-bridge`)를 동시에 감시해 충돌합니다. 한 번에 하나만.

---

## 진단 패널 (EvalTest)

연결이 안 될 때 원인을 가르는 도구입니다. **Window → Extensions → EvalTest** 에서 버튼을 누르세요.

| 결과                            | 의미                                                                              |
| ------------------------------- | --------------------------------------------------------------------------------- |
| 🟢 `[25.5.0]`, `[2]` 등 값이 뜸 | evalScript 정상 — 패치 성공                                                       |
| 🔴 `undefined` / 타임아웃       | CSInterface.js 패치가 적용 안 됨 → Premiere 완전 재시작 확인, `install.sh` 재실행 |

---

## ⚠️ 중요: npm 업데이트 시 재패치 필요

`npm update -g premiere-pro-mcp` 로 패키지를 업데이트하면 **패치한 CSInterface.js 가 원본으로 덮어써져 버그가 재발**할 수 있습니다.
그럴 땐 `bash install.sh` 를 다시 실행하세요. (공식 패키지가 1.1.2+ 로 수정 배포되면 불필요)

---

## 되돌리기

```bash
bash uninstall.sh
```

---

## Windows 사용자

원리는 동일하나 경로가 다릅니다 (`install.sh` 는 macOS 전용). 수동으로:

- CEP 확장 폴더: `%APPDATA%\Adobe\CEP\extensions\`
- `patches\CSInterface.js` 로 패키지의 `cep-plugin\CSInterface.js` 교체
- `manifest.xml` 에 `--enable-nodejs` 추가
- PlayerDebugMode: `reg add HKCU\Software\Adobe\CSXS.12 /v PlayerDebugMode /t REG_SZ /d 1`
- Claude 설정: `%APPDATA%\Claude\claude_desktop_config.json`

---

## 파일 구성

```
premiere-mcp-claude-fix/
├─ README.md                         이 문서
├─ install.sh                        자동 설치/패치 (macOS)
├─ uninstall.sh                      되돌리기
├─ TROUBLESHOOTING.md                증상별 해결
├─ patches/
│  └─ CSInterface.js                 ⭐ 핵심 패치 파일
├─ config/
│  └─ claude_desktop_config.snippet.json   설정 예시
└─ diagnostic/
   └─ EvalCheckPanel/                evalScript 진단 패널
```

---

## 크레딧 / 참고

- MCP 서버: [leancoderkavy/premiere-pro-mcp](https://github.com/leancoderkavy/premiere-pro-mcp)
- 버그 원인: [issue #2 — npm 1.1.1 missing CEP 12 bridge fix](https://github.com/leancoderkavy/premiere-pro-mcp/issues/2)
