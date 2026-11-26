# 비디오유즈 — AI 에이전트 진입 컨텍스트

> 이 파일은 **`CLAUDE.md`(Claude Code) + `AGENTS.md`(Codex/Cursor/Gemini CLI 등)** 양쪽으로 사용됩니다 — `AGENTS.md`는 `CLAUDE.md`로 가는 심볼릭 링크.

이 repo에는 **두 갈래**가 있습니다.

| 갈래                                   | 위치                                             | 하는 일                                                                                |
| -------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------- |
| **편집 프로그램 없이** (기본)          | `.claude/skills/video-auto-edit/SKILL.md`        | `ffmpeg` + `faster-whisper` + `yt-dlp` + 3단계 모션그래픽으로 `final.mp4` 직접 생성    |
| **편집 프로그램 사용** (`nle-auto-edit`) | [`nle-auto-edit/`](nle-auto-edit/README.md)      | Claude가 Premiere / CapCut / Final Cut을 직접 조작해 그 안에서 편집                    |

## 어느 갈래로 갈지 — 묻지 않는다

- **기본은 "편집 프로그램 없이"다.** "이 영상 편집해줘", "무음 잘라줘", "자막 달아줘", "이 레퍼런스처럼 편집해줘"처럼 프로그램을 말하지 않은 요청은 편집 프로그램을 쓸지 묻지 않고 `.claude/skills/video-auto-edit/SKILL.md` 절차로 처리한다.
- **사용자가 프로그램 이름을 말할 때만** 편집 프로그램 갈래로 간다("프리미어로…", "캡컷 자막…", "파이널컷으로…"). 그 요청 하나만 그 프로그램으로 처리한다. 다음 요청에 이름이 없으면 다시 기본 갈래다. 이 갈래에서도 각 어댑터의 안전장치만 고정하고, 더 나은 최신 도구·편집 기법이 있으면 AI가 구식 절차에 얽매이지 않고 스스로 선택·제안한다.

**편집 프로그램 갈래로 갈 때 (스킬이 아직 없으면):**

1. `bash nle-auto-edit/install.sh <premiere|capcut|finalcut>` 실행 → `~/.claude/skills/`에 코어(`ai-video-edit`)와 해당 어댑터를 설치하고, 필요한 도구(Node·ffmpeg·faster-whisper 등)가 없으면 설치한다. Windows에서 Premiere면 `powershell -ExecutionPolicy Bypass -File nle-auto-edit\install.ps1`.
2. 프로그램별 추가 설정을 [nle-auto-edit/README.md](nle-auto-edit/README.md)의 해당 절대로 안내(Premiere는 Claude 재시작 후 그 작업 폴더에서 "프리미어 연결해줘" → `premiere-mcp-setup` 스킬, Final Cut은 `fcp-mcp` 등록, CapCut은 추가 설정 없음).
3. "Claude를 재시작해야 스킬이 로드됩니다" 안내.

## 편집 프로그램 없이 갈래 — 핵심 원칙

자세한 전체 절차와 규칙은 [`.claude/skills/video-auto-edit/SKILL.md`](.claude/skills/video-auto-edit/SKILL.md)가 정전(single source of truth)이다.

- **사전 셋업 불필요 (Windows / macOS / Linux 자동 설치)**: 별도 `setup.sh`나 외부 `~/Developer/video-use` 클론 없이, 에이전트가 작업 시작 시 `ffmpeg`, `Python 3`, 전용 가상환경(`~/.video-edit-venv`)의 `faster-whisper`(`av<16`), 그리고 필요 시 `yt-dlp` / 모션그래픽 도구를 자동 점검·설치한다.
- **프롬프트에 얽매이지 않는 자율 판단**: 6개 Hard Rules(안전장치)만 필수이며, 나머지 수치·연출·구성은 영상 성격에 맞게 AI가 더 나은 방향으로 판단·제안한다.
- **레퍼런스 분석·적용**: 레퍼런스 URL(유튜브·쇼츠·릴스 등)이 주어지면 `yt-dlp`로 다운로드 → `ffmpeg` 4x4 프레임 그리드 & 씬 전환 분석(`edit/ref_style.json`) → 원본 영상에 스타일만 재해석해 적용하고 프레임 나란히 시각 검증한다.
- **모션그래픽 3단계 자동 선택**: 난이도와 환경에 따라 `1단계 Python(Pillow/SVG)+ffmpeg` / `2단계 Hyperframes(npx hyperframes)` / `3단계 Remotion` 중 최적 도구를 스스로 고른다.
- **원본 보존 & OS 안전 경로**: 원본은 절대 덮어쓰지 않고 `<영상 폴더>/edit/`에 산출물(`edl.json`, `words.json`, `final.mp4` 등)을 저장한다. Windows `cp949`·드라이브 콜론 이스케이프·macOS 한글 NFD·DJI/GoPro 비0 타임코드 문제를 사전 회피한다.

## 6개 Hard Rules (비협상 안전장치)

1. 단일 패스 통짜 filtergraph 다중 컷 금지 → 세그먼트별 추출 후 `-c copy` concat
2. 모든 컷 경계에 30ms `afade`
3. Whisper 단어 경계 스냅 + 50~150ms 패딩(단어 중간 절단 금지)
4. 자막은 필터 체인 맨 마지막에 번인
5. 오버레이 입력은 `setpts=PTS-STARTPTS+T/TB` 적용
6. OS별 실제 설치된 한글 폰트 명시(Windows `Malgun Gothic`, macOS `AppleSDGothicNeo` 등)

## 비용

기본 워크플로우는 **API 키 0개, 비용 $0**:

- `ffmpeg` / `ffprobe` — 로컬
- `faster-whisper` — 로컬 (NVIDIA CUDA 자동 가속, CPU `int8` 폴백)
- `yt-dlp` — 로컬 (레퍼런스 URL 다운로드 시)
- 모션그래픽(`Pillow` / `Hyperframes` / `Remotion`) — 로컬

## 자주 묻는 패턴

### 사용자가 영상을 지정할 때

- 절대경로(Windows `C:\...`, macOS `/Users/...`)를 채팅에 알려주면 그 경로 그대로 처리
- 이 레포 안의 `footage/` 폴더에 복사/드래그해 두어도 처리 가능

### 첫 Whisper 실행이 오래 걸릴 때

`faster-whisper` 모델(medium ~1.5GB, large-v3 ~3GB) 첫 다운로드 중일 수 있다. 한 번 받으면 캐시되어 이후에는 빠르다.

### 선택적 NLE 타임라인 내보내기

기본 산출물은 `<영상 폴더>/edit/final.mp4`이지만, 사용자가 Final Cut Pro(`timeline.fcpxml`)나 Premiere Pro(`timeline.xml`) 타임라인 파일도 원하면 레포에 남아 있는 `scripts/export_nle_files.sh`와 `.claude/skills/video-auto-edit/helpers/edl_to_*.py`를 선택적으로 사용할 수 있다.
