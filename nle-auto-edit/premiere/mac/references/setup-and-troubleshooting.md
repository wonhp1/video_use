# 설정 & 문제 해결

## premiere-pro MCP 연결 구조

```
Claude → premiere-pro MCP 서버 → CEP 패널(MCP Bridge) → Premiere ExtendScript/QE
```

- MCP 서버: `premiere-pro-mcp` (npm 전역 설치), Claude Desktop 설정의 `premiere-pro` 항목.
- CEP 패널: Premiere → Window → Extensions → MCP Bridge → Temp Directory `/tmp/premiere-mcp-bridge` → Start Bridge.
- 패널 로그에 `Premiere Pro: <버전>` 이 떠야 정상. `Could not detect Premiere Pro version` 이면 아래 CSInterface.js 문제.

## ⭐ CSInterface.js CEP 12 패치 (가장 흔한 막힘)

`premiere-pro-mcp@1.1.1` 이 배포한 `CSInterface.js` 는 `evalScript` 를 동기 호출해서
Premiere 2025/2026(CEP 12)에서 **항상 undefined** 를 반환한다. 모든 명령이 실패한다.

**확인:** `execute_extendscript` 로 `return __result({v: app.version})` 했을 때 `null`/타임아웃이면 이 문제.

**수정:** 패키지의 `cep-plugin/CSInterface.js` 안 `evalScript` 를 아래로 교체:

```js
CSInterface.prototype.evalScript = function (script, callback) {
  if (typeof __adobe_cep__ !== "undefined") {
    if (callback === null || callback === undefined) callback = function (r) {};
    __adobe_cep__.evalScript(script, callback); // 콜백을 네이티브에 넘김(비동기)
  } else if (callback) {
    callback("EvalScript Error: Not in CEP environment");
  }
};
```

경로 찾기: `echo $(npm root -g)/premiere-pro-mcp/cep-plugin/CSInterface.js`
수정 후 **Premiere 완전 종료(⌘Q) 후 재실행** (CEP 는 시작 시 한 번만 읽음).

전체 설치 키트: https://github.com/wonhp1/premiere-mcp-claude-fix

## QE DOM 편집 — 직접 호출이 필요한 이유

Premiere 2026 에서 MCP 의 `razor_all_tracks`, `ripple_delete`, `add_text_overlay` 는
"성공" 응답을 주지만 실제로는 동작하지 않는다. 그래서 이 스킬은 `execute_extendscript` 로
**QE DOM 을 직접** 호출한다.

핵심 함정:

- **타임코드만 정확**: QE `razor` 는 타임코드 문자열만 정확히 받는다. 초("39.8")나 ticks 문자열은
  부정확하거나 무시된다. → `setPlayerPosition(frameTicks)` 로 플레이헤드를 정확히 두고
  `qe.project.getActiveSequence().CTI.timecode` 를 읽어 그 문자열로 razor.
- **ripple delete**: `qeItem.remove(true, true)` (ripple, alignToVideo).
- **stale 방지**: QE 객체(`qe.project.getActiveSequence()...`)는 다른 QE 호출 후 무효화될 수 있으니
  작업마다 새로 fetch.
- **역순 처리**: 여러 컷은 뒤(시간 큰 것)→앞 순서로. 그래야 앞쪽 절대 시간이 안 틀어진다.

## 증상별

| 증상                                    | 원인/해결                                                   |
| --------------------------------------- | ----------------------------------------------------------- |
| `execute_extendscript` 가 null/타임아웃 | CSInterface.js 미패치 또는 Bridge 미시작/완전재시작 안 함   |
| 컷이 "성공"인데 실제 안 잘림            | MCP 기본 도구 버그 → 이 스킬의 직접-QE 방식 사용            |
| 컷 위치가 어긋남                        | razor 에 초/ticks 문자열을 넘긴 것 → CTI.timecode 방식 사용 |
| `razor is not a function`               | QE 객체 stale → 직전에 새로 fetch                           |
| 활성 시퀀스 없음                        | 타임라인(시퀀스)에 클립을 올리고 다시 실행                  |

## 되돌리기

컷이 마음에 안 들면 Premiere 에서 ⌘Z 여러 번, 또는:
`execute_extendscript` 로 `app.enableQE(); for(var i=0;i<200;i++){try{qe.project.undo();}catch(e){}}`
(횟수는 컷 수 이상으로) 후 상태 확인.
