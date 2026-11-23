---
name: premiere-auto-edit-win
description: >-
  사용자가 프리미어(Premiere Pro)를 이름으로 지목했을 때만 쓴다. 예: "프리미어 무음 잘라줘", "프리미어에서 자막 달아줘",
  "프리미어로 컷편집해줘", "프리미어 타임라인 빈 곳 빼줘", "프리미어에서 속도 바꿔줘". 프리미어를 말하지 않은 편집 요청
  ("무음 잘라줘", "자막 달아줘", "영상 편집해줘")에는 쓰지 않는다. 그때는 편집 프로그램 없이 처리한다.
  (Windows판) Adobe Premiere Pro를 premiere-pro MCP(원본 leancoderkavy/premiere-pro-mcp)의 기본 도구로 조작해 무음 구간을
  컷편집하고 자막을 단다. 무음은 ffmpeg로 감지하고 ripple_remove_timeline_ranges(dry run 후 적용)로 프레임 단위로
  자른다. 자막은 export_sequence로 시퀀스 오디오만 WAV로 뽑아 faster-whisper 단어 타임스탬프 → 쉼 기반 1줄 SRT →
  create_caption_track으로 자막 트랙을 만든다. 그 밖의 프리미어 편집도 이 스킬의 연결·안전 규칙을 따라 MCP 기본
  도구로 처리한다. execute_extendscript와 unsafe-script 권한은 쓰지 않는다. 시작할 때 원본 레포의 최신 버전과
  바뀐 도구를 먼저 확인하고, Premiere가 꺼져 있으면 켜서 연결부터 맞춘다.
  Windows 환경(Python+pip, PowerShell, %APPDATA% 경로)에 맞춰져 있다. 모든 산출물은 세션 프로젝트 폴더의
  premiere-auto-edit\ 하위에 둔다.
---

# Premiere 무음 컷 + 자막 (Windows판)

> ✅ **Windows 11에서 검증했다** (2026-11-22, Premiere Pro 2027 27.0.0 한국어 UI, premiere-pro-mcp 1.31.0, Python 3.12, faster-whisper 1.2.1). 무음 컷·오디오 export·자막 트랙까지 아래 순서 그대로 실제 Premiere에서 돌렸다. 결과는 원본 레포(wonhp1/claude-premiere-auto-edit)의 `tests/README.md` Windows 절에 있다. 막히면 `references/setup-and-troubleshooting-windows.md`를 본다.

## 원본과 검증 버전

- 원본 MCP 서버: https://github.com/leancoderkavy/premiere-pro-mcp (npm `premiere-pro-mcp`)
- 기준 버전과 필수 도구: 이 폴더의 `upstream.json` (1.31.0, macOS·Windows 검증)
- 도구 이름·인자·권한이 이 문서와 다르면 **원본을 따른다.**

## 작업 폴더

모든 산출물은 **세션 프로젝트 폴더** 아래 `premiere-auto-edit\`에 둔다. 이하 `<WORK>`. 경로는 영문으로 둔다(사용자 이름이 한글이면 `%TEMP%` 대신 `C:\premiere-work` 같은 폴더를 쓴다).
Python 스크립트엔 `--workdir <WORK>`, MCP 도구의 경로 인자엔 `C:/.../premiere-auto-edit/...`처럼 슬래시 경로를 넣는다.

명령 예시는 PowerShell 기준이다. 환경 변수는 `%USERPROFILE%`이 아니라 `$env:USERPROFILE`로 쓴다(PowerShell은 `%...%`를 풀지 않는다).

## 사전 조건

- premiere-pro MCP 연결: `premiere-mcp-setup` 스킬(video_use의 `nle-auto-edit/premiere/mcp-setup/`, Windows 메모는 `premiere-mcp-setup/references/windows.md`)
- video_use의 `nle-auto-edit/install.ps1`이 아래 Python 패키지와 ffmpeg를 설치한다.
- `python -m pip install faster-whisper "av<16" imageio-ffmpeg` (Python 3 필요. `winget install Python.Python.3.12`)
  - faster-whisper 1.2.1은 PyAV 16 이상에서 `metadata_errors` TypeError로 실패한다(macOS 실측). 그래서 `av<16`을 같이 설치한다.
  - 모델은 처음 쓸 때 내려받는다(small 약 0.5GB, medium 약 1.5GB, large-v3 약 3GB). 1GB가 넘으면 먼저 사용자에게 묻는다.
- ffmpeg: PATH의 ffmpeg 또는 `imageio-ffmpeg`. MCP `detect_silence` 도구는 PATH의 ffmpeg가 있어야 한다(`winget install Gyan.FFmpeg`).
- 한국어 UI에서 실패하는 모션·불투명도·볼륨 단축 도구는 이 스킬에서 쓰지 않는다. 이 스킬의 흐름은 한국어 UI에서 그대로 동작했다.

## 0) 원본 최신 상태 확인 (매번 먼저)

```powershell
node "$env:USERPROFILE\.claude\skills\premiere-mcp-setup\scripts\check-upstream.mjs" --baseline "<이 스킬 폴더>\upstream.json"
```

- 새 버전이 있으면 출력된 CHANGELOG 중 `requiredTools`의 도구가 나온 줄을 읽고, 바뀐 도구는 `get_capabilities`(tool_query)로 지금 스키마를 확인해 따른다. 권한이 바뀌어 숨겨진 도구는 사용자에게 알린다. unsafe-script를 대신 켜지 않는다.
- 레포 이름 변경·보관·deprecated 경고가 나오면 진행하기 전에 사용자에게 묻는다.

## 무음 컷

1. **연결과 대상 확인**
   - Premiere가 꺼져 있으면 켜는 것부터 한다: `node "$env:USERPROFILE\.claude\skills\premiere-mcp-setup\scripts\ensure-premiere.mjs" [--project=<.prproj 경로>]`. 꺼져 있으면 켜고 커넥터를 기다린 뒤 연결 결과를 보여 준다(Windows 11 실측: 꺼진 상태에서 프로젝트 열기, `overall: ready`까지 16초). 출력의 "참고"(프로젝트 없음·시퀀스 없음·커넥터 신호 없음)를 따른다.
   - `verify_premiere_connection` → `overall: ready`
     - 홈 화면에서도 `active_project`가 ready로 나온 적이 있다. 프로젝트가 열렸는지는 다음 줄의 `get_project_info`로 판단한다.
   - `get_project_info` → `path`를 이후 모든 호출의 `expected_project_path`로 그대로 쓴다.
   - `get_active_sequence` → V1 클립의 `name`·`start`·`inPoint`·`end`, `syncCheck.frameTicks`, 시퀀스 `end`, `transitionCount`
   - `detect_silence`(`project_item_id`: V1 클립 이름) → 결과 `mediaPath`가 원본 경로
2. **파라미터**: dB(기본 -30), 최소 길이(기본 2.0초). 사용자가 안 정했으면 제안하고 확인받는다.
3. **무음 감지** — `python scripts\detect_silence.py "<영상경로>" --noise -30 --min-sec 2.0 --workdir "<WORK>"` → `<WORK>\cuts.json` + 요약. 무음이 많으면 요약을 먼저 보여 주고 확인받는다.
4. **타임라인 구간으로 변환** — `python scripts\plan_cut_ranges.py "<WORK>\cuts.json" --frame-ticks <frameTicks> --clip-start <start> --clip-in <inPoint> --clip-end <end> --out "<WORK>\cut_plan.json"`
   - `>`로 저장하지 않는다. Windows PowerShell 5.1의 `>`는 UTF-16/BOM 파일을 만들어 JSON 파서(Python `json`, Node `JSON.parse`)가 읽지 못한다.
5. **컷** — `chunks`를 배열 순서대로(뒤쪽 묶음부터) 처리한다. 묶음마다:
   - `ripple_remove_timeline_ranges`(`ranges`, `scope: "sync_locked"`, `range_content: "delete"`, `dry_run: true`) → `adjustments`·`clipsRemoved`·`totalRemovedSeconds` 확인
   - 같은 인자 + `dry_run: false` + `confirmation_token`(dry run 결과의 `confirmationToken`) + `idempotency_key`로 적용
     - 토큰은 한 번만 쓰이고 금방 만료된다. dry run 결과를 확인한 뒤 바로 적용한다. "A valid, unexpired, single-use preview confirmation_token is required"가 나오면 dry run부터 다시 한다(Windows 실측).
   - 거부되면(트랜지션, 잠긴 트랙, 400개 넘는 이동) 사용자에게 알린다. 도구가 없거나 계속 거부되면 대체 경로: `razor_times`마다 `razor_all_tracks` → `get_active_sequence`로 조각 확인 → 지울 조각을 뒤에서부터 `ripple_delete`
6. **확인** — `get_active_sequence`로 V1·A1 클립 수(컷 수+1)와 시퀀스 `end`(컷 전 길이 − `removed_seconds`, 1프레임 이내)를 본다. 결과를 보고하고 저장(`save_project`)은 사용자에게 묻는다.

## 자막

자막만 요청받았으면 먼저 무음 컷 1번(Premiere 켜기·연결 확인, `get_project_info`의 `path`를 가드로 쓰기)을 한다.

S1. **오디오만 export** — `export_sequence`
  - `output_path`: `C:/.../premiere-auto-edit/cut_audio.wav`
  - `preset_path`: `C:/Program Files/Adobe/Adobe Premiere Pro <연도>/Settings/EncoderPresets/WAV_Mono_16bit_16kHz.epr` (Premiere 2027에서 이 위치에 있는 것을 확인했다. 없으면 `get_encoder_presets`의 WAV 프리셋)
  - `audio_check: "expect_signal"`, 다시 뽑을 때는 `overwrite: true`
S2. **받아쓰기** — `python scripts\transcribe_words.py "<WORK>\cut_audio.wav" --lang ko --workdir "<WORK>"` → `<WORK>\words.json`
  - `--device auto`(기본)는 CUDA로 먼저 해 보고 실패하면 CPU(int8)로 다시 한다. NVIDIA GPU는 있는데 CUDA 런타임(cuBLAS)이 없는 PC에서는 `Library cublas64_12.dll is not found` 뒤 CPU로 넘어간다. 정상이다.
  - GPU(CUDA 런타임까지 설치)가 있으면 large-v3도 빠르다. CPU만 쓰면 `--model medium`이나 `small`을 권한다.
S3. **쉼 기반 1줄 분할** — `python scripts\segment_subtitles.py --workdir "<WORK>" --soft 16 --gap 0.4` → `<WORK>\cut_audio.srt`. 조절: `--gap 0.6`(덜 분리) / `--soft 14`(짧게).
S4. **자막 트랙** — `import_media`로 SRT를 가져와 `nodeId`를 얻고, `create_caption_track`(`action: "import"`, `item_id`, `caption_format: "subtitle"`, `start_seconds: 0`).
  - 결과는 보통 `committed_unverified`다(CEP에 자막 읽기 API가 없음. `read_sequence_captions`도 `captionReadSupported: false`). 실패가 아니다.
  - 화면으로 확인한다. 타임라인 위쪽 자막 트랙(영어 UI `C1 Subtitle`, 한국어 UI `C1 소제목`)과 프로그램 모니터의 자막 글자를 스크린샷이나 사용자 확인으로 본다.
  - 다시 실행하면 트랙이 하나 더 생기고, CEP로는 지울 수 없다.

## 무음 컷·자막 말고 다른 프리미어 편집

속도, 트림, 크기·위치, 전환, 효과, 내보내기처럼 다른 편집을 프리미어에서 해 달라고 하면 정해진 절차 없이 premiere-pro MCP 기본 도구로 처리한다.

- 도구는 `get_capabilities`(`tool_query`에 하려는 일)로 찾고, 스키마를 확인한 뒤 쓴다.
- 무음 컷과 같은 규칙을 지킨다. 먼저 Premiere 켜기·연결 확인을 하고, 모든 호출에 `expected_project_path`를 넣고, `dry_run`이 있는 도구는 미리보기 후 적용하고, 적용 뒤에는 `get_active_sequence` 등으로 다시 읽어 확인한다.
- 그래픽·애니메이션은 읽기 확인만으로 부족하다. 그 구간을 export해 프레임을 뽑아 눈으로 확인한다.
- 한국어 UI에서는 모션·불투명도·볼륨 단축 도구 등 28개가 실패한다(`premiere-mcp-setup/references/known-issues.md`). 실패하면 사용자에게 알리고 영어 UI를 권한다.
- 맞는 도구가 없어도 `execute_extendscript`나 unsafe-script로 우회하지 않는다. 안 되는 이유를 사용자에게 알린다.

## 막혔을 때

- 타임아웃: `get_bridge_telemetry` → 대화상자면 사용자에게 처리를 부탁한다.
- `HOST_RECOVERY_REQUIRED`: `inspect_operation_recovery` → 실제 상태 재조회 → `acknowledge_operation_recovery`.
- 자세한 내용: `references/setup-and-troubleshooting-windows.md`

## 하지 않을 일

- `execute_extendscript`를 쓰거나 unsafe-script 권한을 켜지 않는다. 예전 ExtendScript는 원본 레포(wonhp1/claude-premiere-auto-edit)의 `legacy/`에 기록으로만 남아 있다.
- 옛 CSInterface.js 패치(원본 레포의 `legacy/mcp-setup-1.1.1`, video_use의 예전 `mcp-setup/install.sh`)를 설치하지 않는다. 최신 커넥터를 망가뜨린다.
- 다른 프로젝트를 건드리지 않는다. 모든 호출에 `expected_project_path` 가드를 넣는다.
