# premiere-auto-edit — Claude로 Premiere Pro 무음 컷 + 자막 자동화 (스킬)

> [nle-auto-edit](../README.md)의 Premiere 어댑터입니다.
> 원본은 [wonhp1/claude-premiere-auto-edit](https://github.com/wonhp1/claude-premiere-auto-edit)이고, 2026-11-22 버전(`f10bbe9`)을 가져왔습니다.

Claude(Claude Code/Desktop)가 `premiere-pro` MCP의 기본 도구로 **Adobe Premiere Pro를 직접 조작**해서:

- 🔇 영상의 **무음 구간 자동 컷편집** (dB·최소 길이 지정 가능, 프레임 단위로 정확)
- 💬 **자막 자동 생성** (시퀀스 오디오 → Whisper 단어 타임스탬프 → 쉼 기반 1줄 SRT → 자막 트랙)

을 수행하는 Claude **스킬**입니다. 편집이 실제 프리미어 타임라인에 반영됩니다.

**프리미어를 이름으로 말할 때만 동작합니다.** "프리미어 무음 잘라줘"는 이 스킬이 처리하고,
그냥 "무음 잘라줘"는 편집 프로그램 없이 처리합니다.

## 구성

| 폴더 | 설치 이름 | 하는 일 | 상태 |
|---|---|---|---|
| [`mcp-setup/`](mcp-setup/) | `premiere-mcp-setup` | MCP 설치·Claude Code 등록·Premiere 연결 확인 | ✅ macOS·Windows 11 검증 |
| [`mac/`](mac/) | `premiere-auto-edit` | 무음 컷 + 자막 (bash·Python + MCP 기본 도구) | ✅ 검증 (Premiere Pro 2027 27.0.0, premiere-pro-mcp 1.31.0) |
| [`windows/`](windows/) | `premiere-auto-edit` | 무음 컷 + 자막 (Python + MCP 기본 도구) | ✅ 검증 (Windows 11, Premiere Pro 2027 한국어 UI, premiere-pro-mcp 1.31.0) |

검증 기록: 원본 레포의 [`tests/README.md`](https://github.com/wonhp1/claude-premiere-auto-edit/blob/main/tests/README.md)

## 설치

```bash
# macOS (저장소 루트에서)
bash nle-auto-edit/install.sh premiere
```

```powershell
# Windows (저장소 루트에서, PowerShell)
powershell -ExecutionPolicy Bypass -File nle-auto-edit\install.ps1
```

> ⚠️ `install.ps1`은 아직 Windows에서 실행해 보지 않았습니다. 안의 설치 명령은 원본 레포가 Windows 11에서 검증한 것입니다.

설치 스크립트가 하는 일:

- 스킬 설치: `premiere-auto-edit`, `premiere-mcp-setup` (macOS는 공통 뼈대 `ai-video-edit`도)
- 도구 설치: Node(22 이상), ffmpeg, faster-whisper + `av<16`
  - macOS는 전용 가상환경 `~/.local/share/nle-auto-edit/venv`에 설치합니다.
  - Windows는 `python -m pip`으로 설치하고, `imageio-ffmpeg`도 함께 설치합니다.
- Premiere가 설치돼 있으면 `premiere-pro-mcp`와 Premiere 커넥터(CEP)도 설치합니다.

그다음 Claude를 재시작하고, Premiere 작업을 할 폴더에서 **"프리미어 연결해줘"**라고 하세요.
`premiere-mcp-setup` 스킬이 원본 최신 버전 확인 → 점검 → Claude Code 등록(그 폴더 한정) → Premiere 켜기 → 연결 확인(`overall: ready`)까지 진행합니다.

## 동작 원리

```
ffmpeg/Whisper = 귀(무음·음성 인식)   →   Claude = 두뇌(판단)   →   premiere-pro MCP 도구 = 손   →   Premiere = 작업대
```

| 단계 | 로컬 스크립트 | MCP 도구 |
|---|---|---|
| 연결 확인 | `ensure-premiere.mjs` (꺼져 있으면 켬) | `verify_premiere_connection`, `get_project_info`, `get_active_sequence` |
| 무음 감지 | `detect_silence.sh` / `detect_silence.py` (ffmpeg) | (`detect_silence`로 원본 경로 확인) |
| 컷 계획 | `plan_cut_ranges.py` (프레임 경계, 50개 묶음) | — |
| 컷 | — | `ripple_remove_timeline_ranges` (dry run → 적용). 대체: `razor_all_tracks` + `ripple_delete` |
| 오디오 export | — | `export_sequence` (`WAV_Mono_16bit_16kHz.epr`) |
| 받아쓰기·분할 | `transcribe_words.py`, `segment_subtitles.py` | — |
| 자막 트랙 | — | `import_media` + `create_caption_track` |

무음 컷·자막 말고 다른 프리미어 편집(속도, 트림, 전환, 효과 등)은 정해진 레시피 없이
Claude가 premiere-pro MCP 기본 도구(1.31.0 기준 451개)로 직접 처리합니다. 이 저장소에서 검증하지는 않았습니다.

## 원본 추적

- 원본 MCP 서버: https://github.com/leancoderkavy/premiere-pro-mcp
- 각 폴더의 `upstream.json`에 검증한 버전(1.31.0)과 스킬이 쓰는 도구(`requiredTools`)를 적어 두었습니다.
- 스킬은 시작할 때 `premiere-mcp-setup/scripts/check-upstream.mjs --baseline <스킬>/upstream.json`으로 원본의 최신 버전과 CHANGELOG를 확인하고, 도구·권한이 바뀌었으면 원본을 따릅니다.

## 주의

- **한글 경로는 피하세요.** macOS는 한글 파일 이름을 자모 분리형(NFD)으로 저장해서, MCP의 프로젝트 가드(`expected_project_path`)가 같은 프로젝트를 다른 프로젝트로 보고 거부합니다.
- **한국어 UI에서는 MCP 도구 28개가 실패합니다**(모션·불투명도·볼륨 단축 도구 등). 무음 컷·자막에 쓰는 도구는 한국어 UI에서도 동작합니다. 목록: [`mcp-setup/references/known-issues.md`](mcp-setup/references/known-issues.md)

## 예전 버전과 달라진 점

- 예전 스킬은 Premiere 2026에서 MCP 기본 도구가 "성공만 보고하고 실제로는 동작하지 않아" 모든 편집을 `execute_extendscript`로 직접 처리했습니다. 그래서 `unsafe-script` 권한과 CSInterface.js 패치(`mcp-setup/install.sh`)가 필요했습니다.
- premiere-pro-mcp 1.31.0에서는 기본 도구가 실제로 동작하고 결과를 다시 읽어 확인하며, 실측에서 프레임 단위로 정확했습니다. 그래서 스킬을 기본 도구로 바꿨고 `unsafe-script`는 켜지 않습니다.
- 옛 CSInterface.js 패치는 최신 커넥터를 옛 파일로 덮어써 망가뜨리므로 지웠습니다.
- 속도·전환·키프레임·MOGRT·모션그래픽 오버레이 레시피(`references/recipes.md`)도 지웠습니다. 전부 `execute_extendscript` 기반이었습니다.
- 옛 파일은 원본 레포의 [`legacy/`](https://github.com/wonhp1/claude-premiere-auto-edit/tree/main/legacy)에 기록으로 남아 있습니다.

## 라이선스

MIT
