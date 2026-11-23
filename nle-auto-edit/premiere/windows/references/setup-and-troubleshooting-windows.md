# Windows 설정과 문제 해결

> ✅ 2026-11-22 Windows 11 Home(한국어), Premiere Pro 2027(27.0.0, 한국어 UI), premiere-pro-mcp 1.31.0, Python 3.12.10, faster-whisper 1.2.1(PyAV 15.1)에서 실제로 확인했다. 결과는 원본 레포(wonhp1/claude-premiere-auto-edit)의 `tests/README.md` Windows 절에 있다.

## 의존성 (pip 중심)

Windows에는 brew가 없으므로 Python + pip로 통일한다. 전제는 Python 3(`winget install Python.Python.3.12`). `python`을 쳤을 때 Microsoft Store 안내만 뜨면 Python이 설치되지 않은 것이다.

```powershell
python -m pip install faster-whisper "av<16" imageio-ffmpeg
```

- `faster-whisper`: 받아쓰기. 모델은 첫 실행 때 `%USERPROFILE%\.cache\huggingface`에 내려받는다.
- `av<16`: faster-whisper 1.2.1이 PyAV 16 이상에서 `metadata_errors` TypeError로 실패한다(macOS 실측). Windows에서는 PyAV 15.1이 설치됐다.
- `imageio-ffmpeg`: `detect_silence.py`용 ffmpeg. MCP `detect_silence` 도구는 PATH의 ffmpeg가 필요하므로 `winget install Gyan.FFmpeg`도 권한다.
- GPU: `transcribe_words.py --device auto`(기본)는 CUDA로 받아쓰다 실패하면 CPU(int8)로 다시 한다. 실제 GPU 가속을 쓰려면 CUDA 12 런타임(cuBLAS, cuDNN 9)이 PATH에 있어야 한다.

## premiere-pro MCP 연결

설치·등록·연결 확인은 `premiere-mcp-setup` 스킬(video_use의 `nle-auto-edit/premiere/mcp-setup/`)을 따른다. Windows 메모는 `premiere-mcp-setup/references/windows.md`에 있다.

- `npm install -g premiere-pro-mcp` → `premiere-pro-mcp.cmd --install-cep` (PowerShell에서는 `.cmd`를 붙인다. 실행 정책 때문에 `premiere-pro-mcp.ps1`이 막힌다)
- 커넥터: `%APPDATA%\Adobe\CEP\extensions\MCPBridgeCEP`. 서명된 커넥터는 PlayerDebugMode 없이도 로드된다.
- npm 전역 명령이 `.cmd`라서 Claude Code에는 node 경로와 `dist\index.js` 경로로 등록한다.
- **옛 CSInterface.js 패치·manifest 수정은 하지 않는다.** npm 1.1.1 전용이었고(원본 레포의 `legacy/mcp-setup-1.1.1`, video_use의 예전 `mcp-setup/install.sh`), 1.31.0에서는 최신 커넥터를 옛 파일로 덮어써 망가뜨린다.

## 경로(workdir)

- 산출물(`cuts.json`, `cut_plan.json`, `cut_audio.wav`, `words.json`, `cut_audio.srt`)은 세션 프로젝트 폴더 아래 `premiere-auto-edit\`에 둔다.
- MCP 도구에 넘기는 경로는 슬래시(`C:/Users/me/proj/premiere-auto-edit/cut_audio.wav`)로 쓴다.
- 사용자 이름에 한글이 있으면 `%USERPROFILE%`·`%TEMP%`에도 한글이 들어간다. 작업 폴더와 프로젝트는 영문 경로에 둔다.
- `expected_project_path`에는 `get_project_info`가 돌려준 `path`를 그대로 넣는다(Windows 백슬래시 경로 그대로 통과했다).

## 오디오 프리셋

- Premiere 설치본: `C:\Program Files\Adobe\Adobe Premiere Pro <연도>\Settings\EncoderPresets\WAV_Mono_16bit_16kHz.epr` (Premiere 2027에서 확인. `export_sequence` 결과 16kHz 모노 WAV, 길이 일치)
- `get_encoder_presets`는 Media Encoder 폴더만 훑는다. 16kHz 프리셋이 목록에 없어도 위 파일 경로를 직접 넘길 수 있다.

## 셸·인코딩

- 이 폴더의 Python 스크립트는 표준 출력을 UTF-8로 고정한다. 한국어 Windows에서 출력을 파이프로 읽으면(Claude Code 셸 등) cp949로 나가 한글이 `����`로 깨졌기 때문이다.
- `plan_cut_ranges.py`의 결과는 `--out`으로 저장한다. Windows PowerShell 5.1의 `>`·`Tee-Object`는 UTF-16(또는 BOM 붙은 UTF-8) 파일을 만들어 `json.load`·`JSON.parse`가 읽지 못한다.
- `.ps1` 파일에 한글이 들어 있으면 BOM 붙은 UTF-8로 저장해야 Windows PowerShell 5.1이 깨뜨리지 않는다(원본 레포의 `tests/make_test_media.ps1`).

## 증상별

| 증상 | 해결 |
|---|---|
| `premiere-pro-mcp --install-cep`가 "running scripts is disabled"로 끝나고 아무것도 설치 안 됨 | `premiere-pro-mcp.cmd --install-cep`로 다시 실행. 실행 정책은 바꾸지 않는다 |
| `verify_premiere_connection`이 커넥터 응답 없음 | Premiere 실행·대화상자 확인, `get_bridge_telemetry`. 가드를 넣을 때만 그렇다면 경로 문자열 불일치 |
| 홈 화면인데 `active_project`가 ready | 실측된 오보고. `get_project_info`가 실패하면 프로젝트가 없는 것이다 |
| `ensure-premiere.mjs`가 "Premiere 실행" 뒤 끝나지 않음 | 2026-11-22 이전 버전의 버그(실행 파이프 상속). 레포를 최신으로 받는다 |
| 도구가 30초 타임아웃 | 대화상자가 막음. 사용자에게 처리 부탁 → `get_last_operations` 확인 후 재시도 |
| `HOST_RECOVERY_REQUIRED` | `inspect_operation_recovery` → 상태 재조회 → `acknowledge_operation_recovery` |
| 컷 도구 거부 | 트랜지션, 잠긴 트랙, sync lock, 400개 넘는 이동(`allow_large_ripple`) |
| 컷 적용이 `confirmation_token is required`로 거부 | 토큰이 만료됐거나 이미 쓰였다. dry run부터 다시 하고 바로 적용한다 |
| 자막 도구가 `committed_unverified` | 정상(CEP에 자막 읽기 API 없음). 화면으로 확인 |
| 받아쓰기가 `cublas64_12.dll is not found` | 최신 `transcribe_words.py`는 CPU로 자동 전환한다(`--device cpu`로 처음부터 CPU도 가능). 옛 버전이면 `$env:CUDA_VISIBLE_DEVICES='-1'`로 GPU를 숨기고 실행한다 |
| 스크립트 출력의 한글이 `����` | 최신 스크립트는 UTF-8로 출력한다. `python -I`는 `PYTHONIOENCODING`을 무시하니 환경 변수로는 못 고친다 |
| `python`/`pip` 없음 | `winget install Python.Python.3.12` 뒤 새 셸 |
| faster-whisper 설치 실패 | Visual C++ 재배포 패키지가 필요할 수 있다 / `python -m pip install --upgrade pip` 후 재시도 |
