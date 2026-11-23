# Windows에서 설치·연결할 때

2026-11-22 Windows 11 Home(한국어), Adobe Premiere Pro 2027(27.0.0, 한국어 UI), premiere-pro-mcp 1.31.0, Node 26.13.1에서 설치부터 `verify_premiere_connection` = `overall: ready`까지 실제로 확인했다. Claude Code 등록(`claude mcp add`)만 이 환경에 `claude` CLI가 없어 직접 해 보지 못했다.

## 준비물

- **Node.js 20.19 이상**: 없으면 `winget install OpenJS.NodeJS.LTS`로 설치한다(관리자 권한 확인 창이 뜬다).
- **ffmpeg·ffprobe**: `trim_clip`, `slip_edit`, `detect_silence`에 필요하다. 없으면 `winget install Gyan.FFmpeg`로 설치한다.
- 설치한 뒤에는 PATH가 반영되도록 새 셸에서 확인한다. 이미 열려 있는 셸에서 바로 쓰려면:
  `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`

## PowerShell 실행 정책 주의 (사용자가 직접 명령을 칠 때)

Windows PowerShell의 기본 실행 정책(Restricted)에서는 npm이 만든 `premiere-pro-mcp.ps1`이 막힌다. PowerShell은 같은 이름이면 `.ps1`을 먼저 고르므로 `premiere-pro-mcp --install-cep`는 아래 오류로 아무것도 하지 않고 끝난다.

```
premiere-pro-mcp.ps1 cannot be loaded because running scripts is disabled on this system.
```

- 사용자에게 직접 실행을 부탁할 때는 **`premiere-pro-mcp.cmd`**로 적어 준다. 실행 정책을 바꾸지 않아도 된다.
- Claude 데스크톱 앱의 PowerShell 도구에서는 프로세스 범위 정책이 `Bypass`라 그대로 돌았지만, 셸마다 다르므로 Claude가 실행할 때도 `.cmd`로 쓴다.
- 실행 정책(`Set-ExecutionPolicy`)은 보안 설정이므로 대신 바꾸지 않는다.

## 설치

```powershell
npm install -g premiere-pro-mcp
premiere-pro-mcp.cmd --install-cep
premiere-pro-mcp.cmd --diagnose-cep
premiere-pro-mcp.cmd --doctor
```

- `--install-cep`는 `install-cep.ps1`을 `-ExecutionPolicy Bypass`로 실행한다. npm 패키지에 든 **서명된 커넥터**(`artifacts\MCPBridgeCEP.zxp`)를 `%APPDATA%\Adobe\CEP\extensions\MCPBridgeCEP`에 풀고, 이어서 `HKCU\Software\Adobe\CSXS.9`~`CSXS.14`의 `PlayerDebugMode`를 `REG_SZ` `1`로 켠다. 사용자에게 이 레지스트리 변경을 한 줄로 알린다.
- **서명된 커넥터는 PlayerDebugMode 없이도 로드된다.** 이 환경에서 PlayerDebugMode를 하나도 켜지 않은 채 연결까지 `ready`였다. 그래서 사용자가 PlayerDebugMode(서명 없는 확장 허용) 변경을 원하지 않으면 아래처럼 서명된 패키지만 설치한다.
  1. 원본 GitHub 릴리스(`https://github.com/leancoderkavy/premiere-pro-mcp/releases/download/v<버전>/MCPBridgeCEP.zxp`)나 npm 패키지의 `artifacts\MCPBridgeCEP.zxp`를 쓴다.
  2. 압축 안에 `META-INF/signatures.xml`이 있고 `CSXS/manifest.xml`의 `ExtensionBundleVersion`이 설치한 npm 버전과 같은지 확인한다.
  3. `.zxp`를 `.zip`으로 복사해 `%APPDATA%\Adobe\CEP\extensions\MCPBridgeCEP`에 푼다(`Expand-Archive`). 이미 폴더가 있으면 사용자에게 묻고 바꾼다.
- 이때 `--diagnose-cep`는 PlayerDebugMode가 없다고 "needs attention"을 내지만 서명된 커넥터에서는 무시해도 된다. `scripts/preflight.mjs`는 서명 여부를 보고 "(서명된 커넥터라 없어도 됨)"으로 표시한다.
- PlayerDebugMode 확인: `reg query HKCU\Software\Adobe\CSXS.12 /v PlayerDebugMode` (Premiere 2027은 CSXS 12)

## Premiere 켜기와 연결 확인

- `scripts/ensure-premiere.mjs`는 Windows에서 `C:\Program Files\Adobe\Adobe Premiere Pro <연도>\Adobe Premiere Pro.exe`를 찾아 켠다. 꺼진 상태에서 `--project`로 프로젝트 열기, `overall: ready`까지 16초 걸렸다.
  - 예전 버전은 `start`를 파이프로 불러 Premiere가 꺼질 때까지 스크립트가 끝나지 않았다(2026-11-22 수정).
- **홈 화면(프로젝트 없음)에서 `verify_premiere_connection`이 `active_project`를 `ready`(ACTIVE_PROJECT_OPEN)로 잘못 보고했다.** 같은 때 `ping`은 `"projectName": "No project open"`, `get_project_info`는 `TypeError: null is not an object`였다. 프로젝트가 열렸는지는 `get_project_info`의 `path`로 판단한다(`ensure-premiere.mjs`는 이미 그렇게 한다).
- 패널 없이도 연결된다. 커넥터의 백그라운드 확장이 Premiere 시작 때 자동으로 켜진다.
- 새 프로젝트는 MCP `create_project`(`path`: 영문 경로의 `.prproj`)로 만들 수 있었다. 화면 조작이 필요 없다.

## Claude Code 등록 (미검증)

npm 전역 명령은 `premiere-pro-mcp.cmd`라서, stdio 서버로 직접 띄우면 실패할 수 있다. 그래서 node와 서버 파일 경로로 등록한다.

1. `premiere-pro-mcp.cmd --print-client-config claude`로 `command`(node.exe 경로)와 `args`(`...\premiere-pro-mcp\dist\index.js`)를 확인한다.
   - 보통 `C:\Program Files\nodejs\node.exe`와 `%APPDATA%\npm\node_modules\premiere-pro-mcp\dist\index.js`다.
2. Premiere 작업 폴더에서 다음을 실행한다.
   `claude mcp add --scope local premiere-pro -- "<node.exe 경로>" "<index.js 경로>"`
3. `claude mcp get premiere-pro`가 Connected인지 확인한다.

`scripts/mcp-call.mjs`와 `scripts/lib-mcp.mjs`는 `npm root -g`로 index.js를 찾아 지금 실행 중인 node로 띄운다. Windows에서 이 방식으로 도구 호출이 동작하는 것을 확인했다.

## 경로 주의

- 사용자 이름에 한글이 있으면 `%USERPROFILE%`과 `%TEMP%`에도 한글이 들어간다.
- 작업 폴더는 `C:\premiere-mcp-test`나 `C:\Users\<영문 이름>\premiere-mcp-test`처럼 영문 경로에 둔다.
- 브리지 임시 폴더(기본 `%TEMP%\premiere-mcp-bridge`)에 비ASCII 문자가 있으면, 영문 경로를 `PREMIERE_TEMP_DIR`로 정한다. 이 값은 MCP 서버 설정과 CEP 패널 설정에 똑같이 넣어야 한다.
- 한국어 Windows에서 Premiere 창 제목은 `C:\사용자\...`로 보이지만 실제 경로와 도구가 돌려주는 `path`는 `C:\Users\...`다. 가드(`expected_project_path`)에는 도구가 돌려준 값을 그대로 쓴다.
- 레포를 zip으로 받아 깊은 폴더에 풀면 260자 경로 제한에 걸릴 수 있다. 짧은 경로에 풀거나 `git -c core.longpaths=true clone`을 쓴다.

## Premiere 조작 (computer use)

- **설치본 위치**: `C:\Program Files\Adobe\Adobe Premiere Pro 20xx\`
- **종료**: Windows에는 macOS식 앱 메뉴가 없다. `File › Exit`(한국어 UI: `파일 › 종료`)를 쓴다. 종료 전에 사용자 허락을 받는다. 스크립트로는 저장(`save_project`) 뒤 `(Get-Process "Adobe Premiere Pro").CloseMainWindow()`로 정상 종료할 수 있었다(창이 막 뜬 직후에는 한 번 더 불러야 했다).
- **패널 메뉴**: macOS와 같다. `Window › Extensions › MCP for Adobe Premiere Pro`(한국어 UI: `창 › 확장명`)이고, 프로젝트가 열려 있어야 나타난다.
- **샘플 미디어**: `C:\Users\Public\Documents\Adobe\Premiere Pro\<버전>\Sample Media` (2027은 `27.0`)
- **한국어 UI 트랙 이름**: `비디오 1`, `오디오 1`, 자막 트랙은 `C1 소제목`으로 보인다.
- **CSXS 로그**: `%TEMP%` 아래 `CEP12-PPRO.log` 등을 찾아본다.
