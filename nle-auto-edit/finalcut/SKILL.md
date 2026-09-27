---
name: finalcut-auto-edit
description: >-
  Final Cut Pro(파이널컷프로)를 FCPXML 생성·임포트로 자동 편집한다. 사용자가 "파이널컷 무음 잘라줘",
  "파이널컷 컷편집", "파이널컷 자막", "파이널컷 자동 편집", "FCP로 편집해줘", "fcpxml 만들어줘"
  처럼 파이널컷을 지목하거나 .fcpxml / .fcpbundle 을 다루려 할 때 사용한다. 무음 컷·자막(글꼴·크기·
  색·테두리)·세로 프로젝트·비표준 fps 소스를 지원한다. 파이널컷은 AppleScript 가 읽기 전용이라
  편집은 FCPXML 을 만들어 임포트하는 방식이며, 임포트할 때마다 사용자가 보관함을 선택해야 한다.
  공통 절차(무음 감지·받아쓰기·자막 분할·모션그래픽 렌더)는 ai-video-edit 스킬을 따른다.
---

# 파이널컷 자동 편집

파이널컷은 **AppleScript 가 읽기 전용**이다(`ProEditor.sdef` — `get` 명령 하나, 전부 `access="r"`).
편집은 **FCPXML 을 생성해 임포트**한다. 라이브러리(`.fcpbundle`)는 SQLite + Core Data 바이너리라
직접 편집하지 않는다.

```
읽기 → AppleScript / fcp MCP (라이브러리·이벤트·프로젝트 탐색)
쓰기 → FCPXML 생성 → 임포트 (새 이벤트로 추가됨)
검증 → xmllint --valid + 자체 프레임 정렬 검사
```

## 🚨 절대 규칙

### 1. 생성은 `fcpxml_build.py` 로 한다
MCP 의 `fcpxml_*` 생성 도구는 결함이 있다(uid 누락, 프레임 미정렬, 세로 불가).
`scripts/fcpxml_build.py` 의 `FCPXML` 클래스가 이 함정들을 전부 막는다.

### 2. 자막은 클립의 **자식**으로 중첩한다
`<spine>` 의 형제로 두면 파이널컷이 **오류 없이 버린다.** 가장 위험한 함정이다.
자세한 건 `references/recipes.md`.

### 3. 검증은 파이널컷과 같은 DTD 로
MCP 의 `fcpxml_validate` 는 **DTD 위반을 통과시킨다.** 믿지 말 것.
```bash
xmllint --noout --valid <SYSTEM 식별자를 넣은 사본>; echo $?
```
DTD 도 프레임 정렬은 못 잡으므로 자체 전수 검사를 함께 돌린다.

### 4. 모든 시간값은 프레임 경계에
`frameDuration` 의 정수배가 아니면 거부된다. `FCPXML.snap()` 이 처리한다.

## 절차

### 0) 준비
```python
import sys; sys.path.insert(0, "<skill-dir>/scripts")
from fcpxml_build import FCPXML
b = FCPXML(1080, 1920, project="이름", event="이벤트")   # 이름의 '/' 는 자동 살균
aid = b.add_media("<영상 경로>")      # ffprobe 로 해상도·fps·회전·오디오 실측
```

### 1) 무음 컷
`ai-video-edit` 의 `detect_silence.sh` 또는 MCP `media_detect_silence`
(둘의 결과는 실측으로 일치 확인됨 — MCP 는 패딩 없는 원본값).
유지 구간을 계산해 `b.add_clip(aid, 시작초, 길이초, 이름)`.
3프레임 미만 조각은 버린다(플래시 프레임).

### 2) 자막
`ai-video-edit` 의 `transcribe_words.py` → `segment_subtitles.py` 로 SRT 생성 후
`b.add_title(텍스트, 시작초, 길이초, size=64, color="1 1 1 1", stroke="0 0 0 1")`.

컷된 타임라인 기준 자막이 필요하면 **ffmpeg 로 유지 구간만 이어붙인 오디오**를 만들어
받아쓰기한다(파이널컷에서 export 할 필요 없음).

### 3) 출력·검증·임포트
```python
b.build("/tmp/out.fcpxml")
```
→ `xmllint --valid` + 프레임 정렬 전수 검사 → MCP `fcp_import_xml`

### 4) 결과 보고
임포트는 **항상 새 이벤트**를 만든다(중복 시 `이름 2`, `이름 3`…).
시도가 쌓이면 사용자가 헷갈리므로 **이벤트/프로젝트 이름을 정확히 알려준다.**
임포트 시 **"보관함 열기" 대화상자가 뜨니** 사용자에게 선택하라고 안내한다.

## 그 밖의 요청

`references/recipes.md` 의 검증 매트릭스를 먼저 본다.
목록에 없는 기능은 `ai-video-edit` 의 "만들어서 쓴다" 절차를 따르고 결과를 기록한다.
