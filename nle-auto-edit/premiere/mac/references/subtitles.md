# 자막(캡션) 생성 — v2 (단어 타임스탬프 → 1줄 자막, 전 과정 자동)

## 흐름 (전부 스크립트)

1. **오디오 export** — `assets/export_sequence_audio.jsx` → `<WORK>/cut_audio.wav`(16kHz 모노). 현재 시퀀스 그대로.
2. **단어별 받아쓰기** — `scripts/transcribe_words.py` → `<WORK>/words.json` (faster-whisper, 정확한 단어 시간).
3. **1줄 분할** — `scripts/segment_subtitles.py` → `<WORK>/cut_audio.srt` (쉼·연결어미 기준 자연스러운 1줄, 정확 타이밍).
4. **타임라인 삽입** — `assets/add_subtitles.jsx` → `createCaptionTrack`로 자동 생성. 수동 드래그 불필요.

## 왜 v2(단어 타임스탬프)인가

- whisper.cpp는 세그먼트 첫 단어 시간이 늘어나는 버그가 있어(예: 첫 단어 0.7→7.0초) 타이밍이 부정확.
- faster-whisper `word_timestamps`는 정확 → 첫 자막이 실제 말 시작점(예: 5.82초)에 맞고, 쉼 기반 분할이 가능.
- 정확한 단어 시간 덕에 자막이 길어도 싱크가 안 밀린다.

## 분할 규칙 (segment_subtitles.py)

- **쉼 기반(말할 때만 자막)**: 단어 간격이 `--gap`(기본 0.4s) 이상이면 자막을 끊고, 끝을 말끝+여운(0.2s)으로
  닫아 **쉼 구간엔 자막이 사라짐(빈 화면)**. 같은 말 덩어리 안은 연속(다음 자막에 붙음).
- **1줄 고정**, 길이는 내용 따라 적응. `--soft`(기본 16)=화면 넘침 방지 소프트 상한, 하드 상한=soft+8.
- glue: 의존명사("수","것","때"…)·"하는/할/있는" 등 앞에서 안 끊음. look-ahead로 상한 내 최적 지점 선택.
- **최소 표시 0.5초** 보장(깜빡임 방지): 같은 덩어리 연속이면 앞 자막에 병합, 고립이면 끝 연장.
- 조절: `--gap 0.3`(잘게)~`0.6`(덜 분리), `--soft 14`~`18`.

## 핵심 API — createCaptionTrack

```javascript
app.project.importFiles(
  ["<WORK>/cut_audio.srt"],
  true,
  app.project.rootItem,
  false,
);
// 프로젝트에서 srt projectItem 찾은 뒤:
seq.createCaptionTrack(cap, 0, Sequence.CAPTION_FORMAT_SUBTITLE); // → true
```

- ⚠️ `for..in`으론 안 보이는 네이티브 메서드 → 직접 호출. 포맷: SUBTITLE=0(권장), 608=1, 708=2.
- 반복 생성 시 같은 SRT projectItem을 **재사용하면 no-op**(트랙이 안 생김) → 새 파일명으로 fresh import.
- 캡션 트랙 **삭제는 스크립트 불가**(2026 DOM/QE 미노출) → 사용자가 UI에서 트랙 헤더 우클릭 → 트랙 삭제.

## 속도 주의 (Mac)

faster-whisper large-v3는 Mac CPU에서 느림(7분 영상 ~20분, GPU 없음). 급하면 `--model medium`.
Windows/GPU에선 빠름. (CUT 단계는 ffmpeg라 빠르고 무관.)

## 의존성

`pip install faster-whisper` (모델은 공용 캐시에 자동 다운로드). 컷 단계엔 ffmpeg 필요.

## 폴백

`createCaptionTrack` 실패 시: SRT는 이미 import 됐으니 사용자가 프로젝트 패널의 SRT를 타임라인에 드래그. (2025/2026에선 보통 정상 동작.)
