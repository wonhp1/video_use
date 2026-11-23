# 설정과 문제 해결 (premiere-pro-mcp 1.31.0 기준)

기준 환경: macOS, Premiere Pro 2027(27.0.0, CEP 12), premiere-pro-mcp 1.31.0, CEP 브리지(UXP는 설정하지 않음). 2026-11-22 실측.
새 버전이면 `SKILL.md` 0단계(원본 확인)의 결과를 먼저 본다.

## 연결 구조

```
Claude → premiere-pro MCP 서버(npm premiere-pro-mcp) → CEP 커넥터(MCPBridgeCEP) → Premiere
```

- 설치·등록·패널 열기·연결 확인은 `premiere-mcp-setup` 스킬(video_use의 `nle-auto-edit/premiere/mcp-setup/`)을 따른다.
- 1.31.0의 커넥터는 Premiere가 시작될 때 백그라운드(headless)로 함께 켜진다. 예전처럼 패널을 열고 Start Bridge를 누를 필요가 없다. 패널(Window › Extensions › MCP for Adobe Premiere Pro)은 상태를 눈으로 보는 용도다.
- 연결 확인: `verify_premiere_connection` → `overall: ready`(서버·커넥터·프로젝트·시퀀스 4개 항목 모두 ready).

## 예전 문서와 달라진 점

| 예전(npm 1.1.1, Premiere 2025/2026) | 지금(1.31.0, Premiere 2027) |
|---|---|
| CSInterface.js `evalScript` 버그 → 패치 필요 | 원본에서 이미 고쳐짐. 옛 패치는 최신 커넥터를 망가뜨리므로 쓰지 않는다(원본 레포의 `legacy/mcp-setup-1.1.1`, video_use의 예전 `mcp-setup/install.sh`) |
| `razor_all_tracks`·`ripple_delete`가 성공만 보고하고 실제로 안 잘림 | 1.31.0은 실제로 자르고 readback으로 확인한다. 실측에서 프레임 단위로 정확했다 |
| 모든 편집을 `execute_extendscript`로 QE DOM 직접 호출 | `execute_extendscript`는 unsafe-script 권한이 있어야 등록된다. 이 스킬은 기본 도구만 쓴다 |
| 오디오 export를 `exportAsMediaDirect` 직접 호출 | `export_sequence`에 같은 프리셋(`WAV_Mono_16bit_16kHz.epr`)을 넘긴다. 길이·신호 검사까지 해 준다 |
| 자막을 `createCaptionTrack` 직접 호출 | `import_media` + `create_caption_track`(action `import`) |

## 도구별 메모 (실측)

| 단계 | 도구 | 결과 | 메모 |
|---|---|---|---|
| 연결 | `verify_premiere_connection`, `get_project_info`, `get_active_sequence` | 성공 | `get_active_sequence`의 `syncCheck.frameTicks`가 프레임 길이 |
| 경로 | `detect_silence`(`project_item_id`) | 성공 | 결과 `mediaPath`로 원본 경로를 얻는다. 무음 구간은 ffmpeg 스크립트와 같다 |
| 컷 | `ripple_remove_timeline_ranges` | 성공 | dry run 토큰 필요, 한 번에 50구간, 경계를 가장 가까운 프레임으로 반올림 |
| 컷(대체) | `razor_all_tracks` + `ripple_delete` | 성공 | 시각을 프레임 경계로 맞춰 넘긴다. 지우기는 뒤에서부터 |
| 오디오 | `export_sequence` | 성공 | `durationVerified`, `audio_check`로 확인. 같은 경로에 다시 쓰려면 `overwrite: true` |
| 자막 | `import_media` + `create_caption_track` | 부분 | 트랙은 생기지만 도구가 다시 읽어 확인하지 못함(`committed_unverified`). 화면으로 확인 |

## 경로와 언어

- **한글 경로**: macOS 디스크의 한글 이름은 자모 분리형(NFD), 손으로 입력한 문자열은 완성형(NFC)이다. 서버가 둘을 같은 것으로 보지 않아서 `expected_project_path` 가드가 같은 프로젝트를 "active project differs"로 거부한다. 이때 `verify_premiere_connection`은 원인을 "커넥터 응답 없음"으로 잘못 안내한다.
  - 해결: 프로젝트와 작업 폴더를 영문 경로에 둔다. 꼭 한글 경로를 써야 하면 `get_project_info`가 돌려준 `path` 문자열을 그대로 가드에 넣는다.
- **한국어 UI**: 이 스킬이 쓰는 도구는 한국어 UI에서도 동작했다. 한국어 UI에서 실패하는 도구 28개(모션·불투명도·볼륨 단축 도구, `color_correct`, `add_caption_graphics` 등)는 쓰지 않는다. 목록과 UI 언어 바꾸는 법은 `premiere-mcp-setup/references/known-issues.md`에 있다.

## 증상별

| 증상 | 원인과 해결 |
|---|---|
| `verify_premiere_connection`이 `PREMIERE_CONNECTOR_UNREACHABLE` | Premiere가 꺼졌거나 대화상자가 떠 있음. `get_bridge_telemetry`로 `blocking.state` 확인. 가드를 넣었을 때만 그렇다면 경로 문자열 불일치 |
| 도구 호출이 30초 타임아웃 | Premiere 대화상자(저장 확인, 미디어 연결, Scratch Disk Settings)가 스크립트 엔진을 막음. 사용자에게 처리를 부탁하고 `get_last_operations`로 직전 호출이 끝났는지 본 뒤 다시 시도 |
| 편집 도구가 `HOST_RECOVERY_REQUIRED`로 거부 | `inspect_operation_recovery` → 실제 상태 재조회 → `acknowledge_operation_recovery` |
| `ripple_remove_timeline_ranges`가 거부 | 트랜지션(`transitionsAffected`), 잠긴 트랙, sync lock 꺼짐, 400개 넘는 이동(`allow_large_ripple`), 다른 시퀀스 지정(활성 시퀀스만 가능) |
| `confirmation_token` 오류 | 토큰은 한 번만 쓸 수 있고 타임라인이 바뀌면 무효. dry run을 다시 한다 |
| `export_sequence`가 파일이 있다며 거부 | `overwrite: true`를 넣거나 새 파일 이름을 쓴다 |
| `get_encoder_presets`에 16kHz WAV가 없음 | Media Encoder 폴더만 훑기 때문. Premiere 설치본 `Contents/Settings/EncoderPresets/WAV_Mono_16bit_16kHz.epr` 경로를 직접 넘긴다 |
| 자막 도구가 `committed_unverified` | 정상. CEP에 자막 읽기 API가 없다. 화면으로 확인 |
| faster-whisper가 `metadata_errors` TypeError | PyAV 16 이상과 맞지 않음. `pip install "av<16"` |

## 되돌리기

- Premiere에서 Edit › Undo(⌘Z). 도구 결과의 `undoSteps`가 그 호출로 쌓인 단계 수다(4구간 컷에 24단계).
- 컷 전에 `duplicate_sequence`로 원본 시퀀스를 복제해 두면 비교와 복구가 쉽다.
- 자막 트랙은 CEP로 지울 수 없다. 사용자가 트랙 헤더를 우클릭해 지운다.
