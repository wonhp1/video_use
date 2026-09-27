# Windows 설정 & 문제 해결

> ⚠️ **미검증**: 이 Windows 버전은 macOS 검증본을 기준으로 크로스플랫폼 설계한 것이며, 실제 Windows 환경에서
> 아직 검증되지 않았습니다. 동작 보고/수정 환영합니다.

## 의존성 (brew 없이 pip 중심)

Windows 에는 brew 가 없으므로 **Python + pip** 로 통일한다. 유일한 전제는 Python 3 (python.org 또는 `winget install Python.Python.3`).

```powershell
pip install faster-whisper imageio-ffmpeg
```

- `faster-whisper`: 받아쓰기. 모델은 첫 실행 시 공용 캐시(`%USERPROFILE%\.cache\huggingface`)에 자동 다운로드/재사용.
- `imageio-ffmpeg`: ffmpeg 바이너리를 pip 로 제공(무음 감지용). 또는 `winget install Gyan.FFmpeg` / 시스템 ffmpeg 가 PATH 에 있으면 그걸 씀.
- GPU(CUDA) 있으면 faster-whisper 가 자동 사용, 없으면 CPU(int8).

## premiere-pro MCP + CSInterface.js 패치 (Windows 경로)

연결 구조는 macOS 와 동일하나 경로가 다르다.

- **MCP 서버**: `npm install -g premiere-pro-mcp` (Node 필요). Claude Desktop 설정: `%APPDATA%\Claude\claude_desktop_config.json`.
- **CEP 패널 폴더**: `%APPDATA%\Adobe\CEP\extensions\MCPBridgeCEP\`
- **CSInterface.js 패치(핵심)**: macOS 와 **동일한 JS 수정**. (CEP 12 evalScript 버그는 Windows 11 + Premiere 2026 에서도 동일하게 보고됨.)
  패키지의 `cep-plugin\CSInterface.js` 안 `evalScript` 를 콜백 전달 방식으로 교체:
  ```js
  CSInterface.prototype.evalScript = function (script, callback) {
    if (typeof __adobe_cep__ !== "undefined") {
      if (callback === null || callback === undefined)
        callback = function (r) {};
      __adobe_cep__.evalScript(script, callback);
    } else if (callback) {
      callback("EvalScript Error: Not in CEP environment");
    }
  };
  ```
- **PlayerDebugMode(서명없는 확장 허용)** — macOS `defaults` 대신 **레지스트리**:
  ```
  reg add "HKCU\Software\Adobe\CSXS.12" /v PlayerDebugMode /t REG_SZ /d 1 /f
  (CSXS.9 ~ CSXS.12 까지 동일하게)
  ```
  설정 후 Premiere 완전 종료 후 재실행.
- **manifest.xml** 에 `--enable-nodejs` `--mixed-context` 추가(파일 IO용) — macOS 와 동일.

전체 설치 키트(macOS): https://github.com/wonhp1/premiere-mcp-claude-fix (Windows 변형은 위 경로 참고).

## 경로(workdir) — 프로젝트 폴더 사용

모든 산출물(`cuts.json`, `cut_audio.wav`, `cut_audio.srt`)은 **세션 프로젝트 폴더** 아래
`premiere-auto-edit\` 에 둔다. Python 스크립트는 `--workdir` 로 받는다.
ExtendScript 에 넘기는 경로(`__CUTS_JSON__`, `__OUT_WAV__`)는 슬래시(/) 형태가 안전하다
(예: `C:/Users/me/proj/premiere-auto-edit/cuts.json`).

## QE 편집 한계 (macOS 와 동일)

- MCP 기본 도구(`razor_all_tracks`/`ripple_delete`/`add_text_overlay`)는 2026에서 미동작 → execute_extendscript 직접.
- 자막은 `createCaptionTrack(cap, 0, Sequence.CAPTION_FORMAT_SUBTITLE)` 로 타임라인에 자동 생성(수동 드래그 불필요). for..in 으론 안 보이는 네이티브 메서드지만 동작.

## 증상별 (macOS 와 공통)

| 증상                                  | 해결                                                                            |
| ------------------------------------- | ------------------------------------------------------------------------------- |
| execute_extendscript 가 null/타임아웃 | CSInterface.js 미패치 / Bridge 미시작 / Premiere 완전재시작 안 함               |
| 컷이 "성공"인데 안 잘림               | MCP 기본 도구 버그 → 직접 ExtendScript                                          |
| `python`/`pip` 없음                   | python.org 또는 winget 으로 Python 설치                                         |
| faster-whisper 설치 실패              | Visual C++ 재배포 패키지 필요할 수 있음 / `pip install --upgrade pip` 후 재시도 |
