---
name: premiere-auto-edit
description: >-
  Adobe Premiere Pro를 premiere-pro MCP로 직접 조작해 영상의 무음 구간을 자동으로 컷편집한다.
  사용자가 "프리미어 무음 잘라줘", "무음 구간 컷편집", "침묵/조용한 부분 제거", "-30dB 이하 잘라줘",
  "프리미어로 자동 편집", "silence cut", "프리미어 컷편집 자동화", "영상에서 빈 부분 빼줘" 같은 말을
  하거나, 프리미어 타임라인의 무음·여백·쉼을 줄여 영상을 짧게 만들고 싶어 할 때 반드시 사용한다.
  프리미어를 Claude가 직접 제어해 타임라인에서 실시간으로 컷이 적용되는 게 특징이다. dB 임계값과
  최소 무음 길이는 사용자 요청대로 조절한다. 자막 생성도 지원한다("자막 만들어줘", "자막 달아줘",
  "받아쓰기", "subtitle", "캡션") — 시퀀스 오디오 export → faster-whisper 단어 타임스탬프 → 쉼 기반 1줄 분할 →
  createCaptionTrack 으로 타임라인에 자막을 정확한 타이밍으로 자동 생성까지 전부 자동(수동 드래그 불필요). 모든 편집은
  MCP 기본 도구 대신 execute_extendscript 직접 호출로 처리한다(2026에서 기본 도구가 버그라서).
  움직이는 타이틀·모션그래픽·페이드 요청("타이틀 넣어줘", "모션그래픽", "인트로", "로어서드")도 처리한다 —
  트랜지션·모션 키프레임·MOGRT는 2026-08-23 검증에서 모두 작동 확인됐고(한글 이름·클립 단위 호출이 관건), 복잡한 다중 요소 애니메이션은 hyperframes 알파 mov 오버레이로 처리한다(references/recipes.md).
  **프리미어에서 하는 편집이라면 목록에 없는 것도 처리한다** — 네스팅·멀티캠·노이즈제거·프록시·리프레임 등
  미검증 기능을 요청받으면 "미검증인데 만들어볼까요?" 안내 후 동의를 받아 그 자리에서 개발·검증하고
  성공하면 레시피로 남긴다. 실패해도 1회로 포기하지 않고 남은 접근을 소진한 뒤 판정한다.
---

# Premiere 무음 자동 컷편집

> **공통 뼈대는 `ai-video-edit` 스킬에 있다.** 무음 감지·받아쓰기·자막 분할·모션그래픽 렌더
> 스크립트와, 검증 프로토콜·자가확장 규칙이 거기 있다. 이 문서는 **프리미어 고유 연결 계층**
> (MCP + ExtendScript)과 프리미어 전용 재시도 체크리스트를 다룬다.

영상의 조용한(무음) 구간을 ffmpeg로 감지하고, Premiere Pro 타임라인에서 직접 잘라 제거한다.
결과는 실제 Premiere 시퀀스에 실시간으로 반영되므로, 사용자가 타임라인에서 바로 보고 다듬을 수 있다.

## 동작 원리 (역할 분담)

Claude는 영상을 직접 듣지 못하므로 도구로 정보를 뽑아 판단·편집한다:

- **ffmpeg** = 귀 (어디가 조용한지 = 무음 타임스탬프)
- **Claude** = 두뇌+손 (어디를 자를지 결정 → 프리미어에 정확한 컷 명령)
- **Premiere(QE DOM)** = 작업대 (실제로 타임라인이 잘림)

## 사전 조건

> ⚠️ **premiere-pro-mcp 1.13.0 이상**은 `execute_extendscript` 가 기본 차단이다.
> MCP 설정 env 에 `PREMIERE_MCP_CAPABILITIES=inspect,edit,export,filesystem,unsafe-script` 가 필요하다.
> CSInterface CEP12 패치는 1.13.0 부터 **불필요**(업스트림 반영됨).

> 🚨 **전환·효과는 현지화된 이름만 받는다.** 영문 이름은 오류 없이 빈 객체를 돌려준다.
> `references/recipes.md` 의 "로케일 함정" 절을 먼저 읽을 것.


- `premiere-pro` MCP가 연결돼 있고, Premiere에 **시퀀스(타임라인)** 가 열려 있어야 한다.
- 처음 쓰는 환경이면 연결/패치가 안 돼 있을 수 있다 → `references/setup-and-troubleshooting.md` 참고.

## 절차

### 0) 연결 확인 (항상 먼저)

`execute_extendscript`로 다음을 실행해 실제 값이 오는지 본다:

```javascript
return __result({
  v: app.version,
  hasSeq: app.project.activeSequence ? true : false,
  media: app.project.activeSequence
    ? app.project.activeSequence.videoTracks[0].clips[0].projectItem.getMediaPath()
    : null,
});
```

- `null`/타임아웃 → 연결 또는 CSInterface.js 패치 문제. `references/setup-and-troubleshooting.md`의 CSInterface.js 절을 따른다.
- `hasSeq:false` → 사용자에게 타임라인에 영상을 올려달라고 요청.
- `media` → 원본 파일 경로. 무음 감지에 이 파일을 쓴다.

### 1) 파라미터 확인

사용자가 dB나 최소 길이를 지정했으면 그대로 쓴다. 안 했으면 기본값을 제안하고 확인받는다:

- **noise dB** (기본 -30): 낮을수록(-40) 보수적=적게 자름, 높을수록(-20) 공격적=많이 자름(조용한 말까지).
- **최소 무음 길이** (기본 2.0초): 길수록 큰 쉼만, 짧을수록 잔 끊김 많음.

무음이 매우 많은 영상(예: 60%+)이면 컷이 수십~수백 개가 될 수 있다. 먼저 2)의 요약을 보여주고
"이대로 진행할까요?" 확인하면 사용자가 놀라지 않는다.

### 2) 무음 감지 → 컷 목록 생성

공통 스크립트 `detect_silence.sh` 를 실행한다 (ai-video-edit 스킬에 있음):

```bash
bash ~/.claude/skills/ai-video-edit/scripts/detect_silence.sh "<영상경로>" <dB> <최소초> [pad]
# 예: bash .../detect_silence.sh "/Users/me/Desktop/clip.mov" -30 2.0
```

→ `/tmp/premiere_cuts.json` 에 컷 구간이 저장되고, 감지 개수·제거 시간·예상 결과 길이가 출력된다.
이 요약을 사용자에게 보여준다.

### 3) 일괄 컷 실행

`assets/cut_silence.jsx` 파일을 읽어 그 내용을 `execute_extendscript`의 `code`로 그대로 실행한다.
오래 걸릴 수 있으니 `timeout_ms`를 넉넉히(예: 240000) 준다.

이 스크립트는 `/tmp/premiere_cuts.json`을 읽어 V1·A1에서 각 구간을 프레임 정확하게 razor +
ripple delete 한다(역순 처리). 결과로 `{done, fail, resultMinutes}` 등을 돌려준다.

### 4) 결과 보고

`done/total`, 결과 길이(분), 실패가 있으면 그 구간을 보고한다. 사용자에게 타임라인을 확인·재생해보라고 안내하고,
원하면 ⌘S 저장 또는 되돌리기(troubleshooting 참고)를 알려준다.

## 중요 — 왜 MCP 기본 도구를 안 쓰는가

Premiere 2026에서 MCP의 `razor_all_tracks` / `ripple_delete` / `add_text_overlay`는 "성공" 응답만 주고
실제로는 동작하지 않는다. 그래서 이 스킬은 `execute_extendscript`로 **QE DOM을 직접** 호출한다.
프레임 정확도(비표준 fps 대응)의 핵심 기법은 `assets/cut_silence.jsx` 주석과
`references/setup-and-troubleshooting.md`에 정리돼 있다. 컷이 "성공인데 안 잘리면" 이 방식인지 먼저 확인한다.

## 자막 생성 (단어 타임스탬프 → 1줄 자막, 완전 자동)

자막은 "지금 타임라인"의 오디오에 맞아야 한다. AI 컷 후 사람이 더 다듬었을 수도 있으므로,
낡은 `cuts.json`이 아니라 **현재 시퀀스를 그대로 export** 해서 그 오디오를 받아쓴다.
산출물(`cut_audio.wav`, `words.json`, `cut_audio.srt`)은 작업 폴더에 둔다(아래 `<WORK>`; Mac은 `/tmp` 기본).

### S1) 현재 시퀀스 오디오만 export

`assets/export_sequence_audio.jsx`를 `execute_extendscript`로 실행 (timeout 예: 180000).
→ `<WORK>/cut_audio.wav` (16kHz 모노). 오디오만이라 빠르고, 현재 타임라인을 정확히 반영.
(MCP export 도구는 2026 불안정 → `exportAsMediaDirect` 직접 호출.)

### S2) 단어별 받아쓰기 → words.json

```bash
python3 ~/.claude/skills/ai-video-edit/scripts/transcribe_words.py <WORK>/cut_audio.wav --lang ko --workdir <WORK>
```

→ faster-whisper(`word_timestamps`)로 **정확한 단어 시간**을 어절 단위 `<WORK>/words.json`로.
GPU 있으면 빠름. **Mac CPU는 large-v3가 느림(~20분)** — 급하면 `--model medium`. (pip install faster-whisper 필요)

### S3) 쉼 기반 1줄 자막으로 분할 → SRT

```bash
python3 ~/.claude/skills/ai-video-edit/scripts/segment_subtitles.py --workdir <WORK> --soft 16 --gap 0.4
```

→ **말할 때만 자막이 뜨도록** 분할: 단어 간격이 `--gap`(기본 0.4초) 이상이면 자막을 끊고 끝을 말끝+여운으로
닫아 **쉼 구간엔 빈 화면**(자막 없음)이 된다. 같은 말 덩어리 안은 연속. 1줄 고정, 길이는 내용 따라 적응.
정확한 타이밍으로 `<WORK>/cut_audio.srt` 생성. 최소 표시 0.5초 보장(깜빡임 방지).

- 너무 자주 바뀌면 `--gap 0.6`(덜 쪼갬), 더 잘게는 `--gap 0.3`. 줄 길이는 `--soft 14`(짧게)~`18`(여유).

### S4) 자막을 타임라인에 올리기 (완전 자동)

`assets/add_subtitles.jsx`를 `execute_extendscript`로 실행. SRT를 import 하고
`createCaptionTrack(cap, 0, Sequence.CAPTION_FORMAT_SUBTITLE)`로 **자막 트랙을 자동 생성**한다. 수동 드래그 불필요.

> 참고: `createCaptionTrack`은 `for..in`엔 안 보이는 네이티브 메서드지만 동작한다.
> `CAPTION_FORMAT_SUBTITLE`(0)=크리에이터 자막, `_708`(2)=방송 CC. 자세한 건 `references/subtitles.md`.

### 옵션

- 언어/번역: `transcribe_words.py --lang en` 등.
- 자막 길이: `segment_subtitles.py --soft 14`(짧게) ~ `--soft 18`(여유).
- 쉼 민감도: `segment_subtitles.py --gap 0.3`(잘게 분리) ~ `--gap 0.6`(덜 분리).
- 속도 우선(Mac): `transcribe_words.py --model medium`.

## 그 밖의 편집 요청 — `references/recipes.md` 를 먼저 볼 것

무음컷·자막 외의 편집(속도/슬로모션, 크기·위치·불투명도, 트림, 클립 이동, 영상 export, 타이틀 삽입,
효과·Lumetri, 볼륨, 썸네일, 씬 감지, 프로젝트 정리·재연결·프록시)을 요청받으면
**`references/recipes.md` 의 검증 매트릭스를 먼저 읽고 그 코드를 쓴다.** Premiere 26.2.2에서 23개 항목을
실제 실행 후 **렌더 결과까지** 확인한 기록이라, 되는 것/안 되는 것/대안이 정리돼 있다.

- ✅ 작동(21): 백업·시퀀스복제, 속도, 정적 크기·위치·회전·불투명도, 트림, 이동, 볼륨,
  영상export, 프레임캡처, 효과·Lumetri, 갭찾기, 빈·이름·재연결·미사용·프록시,
  **트랜지션 · 모션 키프레임 · MOGRT**(2026-08-23 승격), 모션그래픽 오버레이
- ⚠️ ffmpeg 폴백(1): 씬 감지
- ❌ 불가(1): 오디오 전환

**애니메이션 원칙**: 모션 키프레임·트랜지션은 2026-08-23 에 ✅ 로 승격됐다(`references/recipes.md`).
다만 여러 요소가 얽힌 복잡한 애니메이션은 여전히 밖에서 알파 mov 로 렌더하는 편이 안정적이다.
움직이는 타이틀·오버레이·페이드는 **밖에서 알파 영상으로 렌더**하고 프리미어는 **정적 배치**만 한다.
추가 설치 불필요(`npx hyperframes` 자동 다운로드).

**안전 원칙**: 파괴적 편집 전에 recipes.md의 0차(백업 저장 + 시퀀스 복제)를 먼저 실행하고 **복제본에서 작업**한다.
대규모 컷은 undo로 되돌아가지 않으니, 복원은 원본 클립 `overwriteClip` 방식을 쓴다.

**판정 원칙**: 어떤 동작이든 실행 후 **읽기로 상태를 재확인**한다. "성공" 응답만 오고 실제로는 아무 일도
안 일어나는 API가 실재한다(트랜지션, MCP razor 기본도구). **그래픽·애니메이션은 읽기 확인만으로 부족하다** —
export → ffmpeg 프레임 추출 → 눈으로 확인까지 해야 유효하다(키프레임·MOGRT를 이 단계에서 걸러냈다).

## 목록에 없는 기능을 요청받았을 때 — 만들어서 쓴다

`recipes.md` 매트릭스에 없는 편집(예: 네스팅, 멀티캠, 오디오 노이즈 제거, 프록시 일괄 생성, 자동 리프레임…)을
요청받으면 "모르겠다"로 멈추지 않는다. **미검증임을 먼저 알리고, 동의를 받아 그 자리에서 만들어 검증한다.**

1. **안내** — "이건 아직 검증되지 않은 기능입니다. 지금 만들어서 시도해볼까요? (실패할 수도 있고, 되면
   레시피로 남겨 다음부터 바로 씁니다)" 라고 짧게 알리고 답을 기다린다. **말없이 실험하지 않는다**(프리미어를
   실제로 건드리는 일이다). 단, 읽기 전용 조회(정보 확인·리포트)는 안내 없이 바로 해도 된다.
2. **안전장치** — 동의를 받으면 recipes.md 0차(백업 저장 + 시퀀스 복제)를 먼저 실행하고 **복제본에서** 실험한다.
3. **개발·검증** — API 후보를 직접 호출해 시도하고, 아래 "실패했을 때" 절차를 따른다.
   판정은 **읽기 재확인**까지, 그래픽·애니메이션이면 **export → 프레임 추출 → 눈으로 확인**까지.
4. **기록** — 성공하면 `recipes.md`에 레시피(검증된 코드 + 함정)를 추가하고 상태표에 ✅로 넣는다.
   실패하면 ❌로 넣고 **시도한 접근 목록**을 남긴다(같은 삽질 반복 방지).
5. **무거운 작업은 미리 경고** — 대량 렌더·수백 개 컷처럼 시간이 오래 걸리거나 파일을 많이 만드는 작업은
   규모(예상 개수·시간)를 먼저 알린다. (PNG 시퀀스를 workArea=0으로 뽑아 1500장을 쏟은 사고가 있었다.)

## 실패했을 때 — 1회 실패로 ❌ 판정하지 않는다

"실패했다"와 "불가능하다"는 다르다. 실제로 키프레임·프레임캡처·자막삽입 셋 다 **첫 시도는 실패했지만
다른 접근으로 성공**했다. 포기 전에 아래를 순서대로 소진한다.

**A. 재시도 체크리스트** (오늘 3개를 되살린 패턴)

1. **CTI(플레이헤드)를 먼저 옮겼는가** — 시간 기반 API는 플레이헤드에 의존한다(키프레임·razor).
2. **시간 인자를 ticks 문자열로 줬는가** — 초 숫자·Time 객체로는 실패하는 API가 많다.
3. **컴포넌트를 잘못 잡지 않았는가** — 효과를 추가하면 속성 개수가 겹친다. 첫 매치에서 `break`.
4. **`for..in`에 안 보여도 직접 호출해봤는가** — 네이티브 메서드는 열거되지 않는다.
   `createCaptionTrack`을 "API 없음"으로 오판했다가 직접 호출로 살렸다.
5. **인자 개수·형식을 스윕했는가** — `setSpeed`는 5인자 필수, `move`는 상대 오프셋이었다.
6. **이미 검증된 다른 경로를 재활용할 수 있는가** — 프레임캡처는 검증된 `exportAsMediaDirect`에
   PNG 프리셋 + in/out을 얹어 해결했다.
7. **전제 조건이 빠지지 않았는가** — 클립이 2개 있어야 하는지, 시퀀스가 열려 있는지, 트랙이 비었는지.

**B. 계층을 바꿔 우회** — 위로 안 되면 프리미어 안에서 고집하지 말고 밖으로 나간다.

| 막힌 것                             | 우회                                                            |
| ----------------------------------- | --------------------------------------------------------------- |
| 애니메이션(키프레임·트랜지션·MOGRT) | **hyperframes** 알파 mov → 정적 배치 (recipes.md 모션그래픽 절) |
| 분석·감지(씬 감지 등)               | **ffmpeg** 필터로 계산 → 그 결과로 프리미어 편집                |
| 프리미어가 API를 안 주는 생성 작업  | 외부에서 파일을 만들어 **import + 배치**                        |

**C. 그래도 안 되면** ❌ 확정. 단 **시도한 접근을 전부 문서에 적는다** — 이름/인자 조합/위치/다른 계층까지.
`recipes.md`의 "트랜지션 — 시도한 것"이 그 양식이다.
