---
name: premiere-auto-edit
description: >-
  (Windows판) Adobe Premiere Pro를 premiere-pro MCP로 직접 조작해 영상의 무음 구간을 자동 컷편집하고
  자막을 생성한다. 사용자가 "프리미어 무음 잘라줘", "무음 구간 컷편집", "조용한 부분 제거", "-30dB 이하 잘라줘",
  "자막 만들어줘", "받아쓰기", "silence cut", "subtitle" 같은 말을 하거나 프리미어 타임라인의 무음·여백을
  줄이고 싶어 할 때 사용한다. Windows 환경(Python+pip, 레지스트리, %APPDATA% 경로)에 맞춰져 있다.
  모든 편집은 MCP 기본 도구 대신 execute_extendscript 직접 호출로 처리한다. 모든 산출물은 세션 프로젝트
  폴더의 premiere-auto-edit\ 하위에 둔다. (⚠️ Windows 실측 미검증 — macOS 검증본 기반 크로스플랫폼 설계.)
---

# Premiere 무음 컷 + 자막 (Windows판)

macOS 검증본을 Windows 에 맞춰 포팅한 버전. 셸 스크립트 대신 **Python**, 의존성은 **pip**, 경로는
**프로젝트 폴더 + 레지스트리/%APPDATA%** 를 쓴다. 편집 로직(ExtendScript)은 OS 무관하게 동일하다.

> ⚠️ 이 버전은 실제 Windows 에서 아직 검증되지 않았다. 막히면 `references/setup-and-troubleshooting-windows.md` 참고.

## 작업 폴더

모든 산출물은 **세션 프로젝트 폴더** 아래 `premiere-auto-edit\` 에 둔다. 이하 이 경로를 `<WORK>` 로 표기.
Python 스크립트엔 `--workdir <WORK>`, ExtendScript 토큰엔 슬래시 경로(`C:/.../premiere-auto-edit/...`)를 넣는다.

## 사전: 의존성 (최초 1회)

`pip install faster-whisper imageio-ffmpeg` (Python3 필요). premiere-pro MCP 연결+패치는
`references/setup-and-troubleshooting-windows.md` 참고. 무거운 설치/모델 다운로드는 사용자 확인 후 진행.

## 무음 컷

0. **연결 확인** — execute_extendscript 로 `return __result({v: app.version, hasSeq: app.project.activeSequence?true:false})`.
   null/타임아웃이면 references 의 CSInterface.js 패치/Bridge 확인.
1. **무음 감지** — `python scripts/detect_silence.py "<영상경로>" --noise -30 --min-sec 2.0 --workdir "<WORK>"`
   → `<WORK>\cuts.json` 생성 + 요약. (dB·초는 사용자 요청대로.) 무음이 많으면 요약 먼저 보여주고 확인받는다.
2. **일괄 컷** — `assets/cut_silence.jsx` 를 읽어 `__CUTS_JSON__` 를 `<WORK>/cuts.json` (슬래시 경로)로 치환한 뒤
   execute_extendscript 로 실행(timeout 넉넉히, 예: 240000). 결과 `{done, fail, resultMinutes}` 보고.

## 자막

S1. **오디오 export** — `assets/export_sequence_audio.jsx` 의 `__OUT_WAV__` 를 `<WORK>/cut_audio.wav` (슬래시)로
치환해 execute_extendscript 실행(timeout 180000). 현재 시퀀스 그대로 16kHz 모노로 → 사람이 다듬어도 정확.
S2. **단어별 받아쓰기** — `python scripts/transcribe_words.py "<WORK>/cut_audio.wav" --lang ko --workdir "<WORK>"`
→ `<WORK>\words.json` (faster-whisper word_timestamps, 정확한 단어 시간). 모델 공용 캐시 자동.
Windows는 GPU(CUDA)면 빠름. (pip install faster-whisper)
S3. **쉼 기반 1줄 분할** — `python scripts/segment_subtitles.py --workdir "<WORK>" --soft 16 --gap 0.4`
→ 단어 간격 `--gap`(0.4초) 이상이면 분리+끝을 말끝으로 닫아 **쉼 구간엔 자막 없음**. 정확한 타이밍으로 `<WORK>\cut_audio.srt`. 조절: `--gap 0.6`(덜 분리)/`--soft 14`(짧게).
S4. **자막 타임라인에 올리기 (완전 자동)** — `assets/add_subtitles.jsx` 의 `__SRT_PATH__` 를
`<WORK>/cut_audio.srt`(슬래시 경로)로 치환해 execute_extendscript 실행. SRT import +
`createCaptionTrack(cap, 0, Sequence.CAPTION_FORMAT_SUBTITLE)` 로 자막 트랙 자동 생성. 수동 드래그 불필요.
(createCaptionTrack 은 for..in 으로 안 보이는 네이티브 메서드지만 실제 동작.)

## 원칙

쓰기 동작은 MCP 기본 도구(`razor_all_tracks`/`add_text_overlay` 등, 2026 버그) 대신 **execute_extendscript 직접 호출**.
읽기 도구(get_premiere_state 등)는 그대로 써도 된다.

## 그 밖의 편집 요청

무음컷·자막 외 편집(속도, 크기·위치, 트림, 이동, 영상export, 타이틀, 효과·Lumetri, 볼륨, 썸네일, 씬감지,
빈·이름·재연결·프록시)은 `references/recipes.md` 의 검증 매트릭스를 먼저 읽고 그 코드를 쓴다.
✅18 / ⚠️1(씬감지) / ❌4(트랜지션·키프레임2·MOGRT — 전부 '호출 성공·렌더 미반영').
**애니메이션은 프리미어 키프레임 대신 hyperframes로 알파 mov를 렌더해 오버레이**(recipes.md의 모션그래픽 절). 추가 설치 불필요(npx). 파괴적 편집 전 백업+시퀀스복제(0차) 필수.

## 목록에 없는 기능 / 실패했을 때

- **미검증 기능 요청** → "미검증인데 만들어볼까요?" 안내 → 동의 → 백업+시퀀스복제 후 복제본에서 개발·검증 →
  성공은 recipes.md 레시피로, 실패는 ❌+시도목록으로 기록. (읽기 전용 조회는 안내 없이 바로)
- **1회 실패로 ❌ 판정 금지** → 재시도 체크리스트(CTI 이동 / ticks 문자열 / 컴포넌트 첫매치 break /
  for..in 안 보이는 네이티브 직접 호출 / 인자 스윕 / 검증된 경로 재활용 / 전제조건) 소진 →
  그래도 안 되면 계층 우회(hyperframes·ffmpeg) → 그래도 안 되면 ❌ 확정 + 시도 전부 기록.
- 상세는 `references/recipes.md` 와 mac판 SKILL.md 동일 절 참고.
