# 자막(캡션) 생성 — 단어 타임스탬프 → 쉼 기반 1줄 자막 (premiere-pro-mcp 1.31.0 기본 도구)

## 흐름

1. **오디오 export** — `export_sequence`에 `WAV_Mono_16bit_16kHz.epr`를 넘겨 `<WORK>/cut_audio.wav`(16kHz 모노). 지금 시퀀스 그대로.
2. **단어별 받아쓰기** — `scripts/transcribe_words.py` → `<WORK>/words.json` (faster-whisper, 정확한 단어 시간).
3. **1줄 분할** — `scripts/segment_subtitles.py` → `<WORK>/cut_audio.srt` (쉼·연결어미 기준 1줄, 정확한 타이밍).
4. **타임라인에 올리기** — `import_media`로 SRT를 가져온 뒤 `create_caption_track`(action `import`)으로 자막 트랙을 만든다.

## 왜 단어 타임스탬프인가

- whisper.cpp는 세그먼트 첫 단어 시간이 늘어나는 버그가 있어(예: 첫 단어 0.7→7.0초) 타이밍이 부정확했다.
- faster-whisper `word_timestamps`는 단어 시간이 정확해서 첫 자막이 실제 말 시작점에 맞고, 쉼 기반 분할이 가능하다.

## 분할 규칙 (segment_subtitles.py)

- **쉼 기반(말할 때만 자막)**: 단어 간격이 `--gap`(기본 0.4s) 이상이면 자막을 끊고, 끝을 말끝+여운(0.2s)으로 닫아 쉼 구간엔 화면을 비운다. 같은 말 덩어리 안은 연속.
- **1줄 고정**, 길이는 내용 따라 적응. `--soft`(기본 16)=소프트 상한, 하드 상한=soft+8.
- 의존명사("수","것","때"…)·"하는/할/있는" 앞에서는 끊지 않는다. 상한 안에서 가장 자연스러운 지점을 고른다.
- **최소 표시 0.5초**: 같은 덩어리 연속이면 앞 자막에 합치고, 따로 떨어져 있으면 끝을 늘린다.
- 조절: `--gap 0.3`(잘게)~`0.6`(덜 분리), `--soft 14`~`18`.

## MCP 도구 호출

```text
import_media           file_paths: ["<WORK>/cut_audio.srt"], expected_project_path
                       → items[0].nodeId
create_caption_track   action: "import", item_id: <nodeId>, caption_format: "subtitle",
                       start_seconds: 0, expected_project_path, idempotency_key
```

- `caption_format`: `subtitle`(크리에이터 자막, 권장), `608`, `708` 등.
- 결과는 `committed_unverified`가 정상이다. CEP에는 자막 트랙을 읽는 API가 없어 도구가 생성 여부를 다시 확인하지 못한다. `read_sequence_captions`도 `captionReadSupported: false`로만 답한다.
- **확인은 화면으로 한다.** 재생 헤드를 자막이 있는 시각에 두고 스크린샷을 찍으면 타임라인 위쪽 `C1 Subtitle` 트랙의 자막 블록과 프로그램 모니터의 자막 글자가 보인다. 1.31.0 실측에서 SRT 8개 큐가 그대로 블록 8개로 올라온 것을 확인했다.
- 다시 실행하면 자막 트랙이 하나 더 생긴다. CEP로는 자막 트랙을 지울 수 없다. 지우려면 사용자가 UI에서 트랙 헤더를 우클릭해 지운다.
- 스타일은 Premiere 기본값이다. 글꼴·배경·위치는 `get_caption_style_guidance`가 알려 주는 수동 절차를 따른다.
- 자막 트랙은 `export_sequence` 결과물에 기본으로 함께 렌더된다.

다른 방법: `create_caption_track`의 `action: "import_plan"`은 받아쓰기 JSON이나 SRT를 넣으면 도구가 직접 자막을 나눠 SRT를 쓰고 트랙까지 만든다. 다만 쉼 기반 1줄 분할 규칙은 이 스킬의 `segment_subtitles.py`에만 있으므로 기본 흐름은 SRT import를 쓴다.

## 속도 (Mac)

faster-whisper는 Mac에서 CPU로 돈다. large-v3는 7분 영상에 약 20분 걸린다. 기본은 medium, 빠르게 볼 때는 small을 쓴다. 모델은 첫 실행 때 내려받는다(small 약 0.5GB, medium 약 1.5GB, large-v3 약 3GB).

## 의존성

- `pip install faster-whisper "av<16"` (faster-whisper 1.2.1은 PyAV 16 이상과 맞지 않는다)
- 컷 단계엔 ffmpeg가 필요하다.

## 폴백

`create_caption_track`이 오류를 내면 SRT는 이미 프로젝트에 들어와 있으니, 사용자가 프로젝트 패널의 SRT를 타임라인으로 끌어다 놓으면 된다.
