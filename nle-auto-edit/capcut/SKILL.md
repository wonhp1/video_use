---
name: capcut-auto-edit
description: >-
  CapCut(캡컷)의 프로젝트 파일을 직접 편집해 자동 편집한다. 사용자가 "캡컷 무음 잘라줘",
  "캡컷 컷편집", "캡컷 자막", "캡컷에 전환 넣어줘", "캡컷 모션그래픽", "캡컷 배경음악",
  "캡컷 자동 편집" 처럼 캡컷을 지목하거나, 캡컷 프로젝트를 편집하려 할 때 사용한다.
  무음 컷·자막(스타일·애니메이션)·트랜지션·등장 애니메이션·오버레이·알파 모션그래픽·
  필터·영상효과·배경음악·키프레임·크기/위치/회전/불투명도/속도/볼륨을 전부 지원한다.
  트랜지션 1137개, 애니메이션 578개, 필터 274개 등 2390개 내장 리소스를 이름으로 찾아 적용한다.
  캡컷은 실시간 제어가 불가능하므로 반드시 앱을 완전 종료(⌘Q)한 뒤 편집하고, 다시 열어 확인한다.
  공통 절차(무음 감지·받아쓰기·자막 분할·모션그래픽 렌더)는 ai-video-edit 스킬을 따른다.
---

# 캡컷 자동 편집

캡컷은 **외부에서 실시간 제어가 불가능하다**(플러그인 API·AppleScript·CDP·URL 스킴 전부 확인 완료).
유일한 경로는 **draft JSON 파일 직접 편집**이다. 그래서 앱을 끄고 → 고치고 → 다시 연다.

## 🚨 절대 규칙 — 어기면 편집이 통째로 되돌아간다

### 1. 저장은 반드시 `capcut_edit.py` 의 `save()` 로
`draft_info.json` 은 **사본이 6개 더 있다.** 하나만 고치면 캡컷이 사본에서 복구해버린다.
```
draft_info.json / .bak / template-2.tmp   ×   (프로젝트 루트, Timelines/<main_timeline_id>/)
```

### 2. 캡컷이 꺼져 있어야 한다
가드는 `pgrep -x CapCut`. (`pgrep -f ".../MacOS/CapCut "` 는 끝 공백 때문에 본체를 못 잡는다.)
`save()`/`load()` 가 자동으로 검사하고 실행 중이면 중단한다. 창만 닫는 건 종료가 아니다 — **⌘Q**.

### 3. 세그먼트와 material 은 짝이다
한쪽만 고치면 캡컷이 불일치를 감지해 **전체를 리셋**한다.
- `segment.speed` 를 바꾸면 `materials.speeds` 도 같이 바꾼다
- 무음 컷으로 세그먼트를 복제하면 material 도 **세그먼트별 고유 id 로 새로 발급**한다
  (deepcopy 하면 전부 같은 id 를 가리켜 나중에 speed·효과 변경이 실패한다)

### 4. 외부 파일은 `~/Movies/CapCut/` 아래에 둔다
macOS 는 데스크탑/문서/다운로드를 TCC 로 막는다. 캡컷에 권한이 없으면 **파일이 있어도**
"미디어를 찾을 수 없음"이 뜬다. `asset_path()` 가 자동으로 복사한다.
그리고 `register_material()` 로 `draft_meta_info.json` 등록부에도 넣는다.

시간 단위는 **마이크로초**(1초 = 1_000_000).

## 절차

### 0) 준비
```python
import sys; sys.path.insert(0, "<skill-dir>/scripts")
import capcut_edit as cc
cc.projects()              # 프로젝트 목록
d, p = cc.load("프로젝트명")  # 캡컷 실행 중이면 여기서 중단됨
```
편집 후 항상 `cc.save(d, p)` — 자동 백업 후 미러 6개에 기록한다.

### 1) 무음 컷
`ai-video-edit` 의 `detect_silence.sh` 로 컷 목록을 만든 뒤, 유지 구간을 재구성한다.
코드는 `references/recipes.md` 참조. 세그먼트 복제 시 material 고유 id 발급을 잊지 말 것.

### 2) 자막
`ai-video-edit` 의 `transcribe_words.py` → `segment_subtitles.py` 로 구간을 만든 뒤:
```python
d['materials']['texts'].append(cc.text_material(tid, "내용", size=15.0,
    color=(1,1,1), border=(0,0,0), shadow=True, bold=False))
seg = cc.base_segment(sid, tid, [anim_id], start_us, dur_us, y=-0.75)
```
- `y`: +0.3 상단 / 0.0 중앙 / -0.75 하단. 메인 타이틀은 크고 색이 있게, 하단 자막은 작고 희게.
- **겹치는 자막은 트랙을 나눈다.** 한 트랙에 겹쳐 넣으면 캡컷이 알아서 분리하지만 처음부터 나누는 게 낫다.

### 3) 트랜지션 · 애니메이션 · 필터 · 효과
2390개 내장 리소스를 이름으로 찾는다.
```python
m = cc.find_effect("transition_meta", "叠化")      # 트랜지션 1137개
m = cc.find_effect("video_intro", "放大")          # 등장 251 / video_outro 219
m = cc.find_effect("text_intro", "打字机 I")        # 텍스트 등장 182 / text_outro 100
m = cc.find_effect("filter_meta", "BW 2")          # 필터 274
m = cc.find_effect("video_scene_effect", "抖动运镜") # 영상효과 119
```
- 카탈로그 이름은 **중국어**다. 없는 이름을 넣으면 비슷한 후보를 알려주니 그걸로 다시 찾는다.
- 트랜지션은 **앞 세그먼트**의 `extra_material_refs` 에 붙인다.
- 필터는 `materials.effects` + `filter` 트랙, 영상효과는 `materials.video_effects` + `effect` 트랙.

### 4) 오버레이 · 모션그래픽
**ProRes 4444 알파 MOV 가 캡컷에서 그대로 동작한다** — 프리미어용 렌더를 재사용할 수 있다.
```python
src = cc.asset_path("<알파MOV 경로>")        # ~/Movies/CapCut/claude-assets/ 로 복사
vm = cc.video_material(cc.uid("OVL",0), src, width=W, height=H, duration_us=D, has_audio=False)
cc.register_material(p, src, W, H, D)        # 등록부 필수
```
새 `video` 트랙에 올리고 `track_render_index` 를 메인보다 크게 준다.

### 5) 배경음악
`materials.audios` (type `extract_music`) + `audio` 트랙. `asset_path()` + `register_material()` 필수.

### 6) 키프레임
`segment['common_keyframes']` 에 `property_type` 별로 넣는다
(`KFTypeScaleX/Y`, `KFTypePositionX/Y`, `KFTypeRotation`, `KFTypeAlpha`, `KFTypeVolume`).
크기는 X·Y 둘 다 넣는다.

## 사용자가 디테일 조정을 요청할 때

첫 결과는 **초안**이다. 사용자가 보고 고쳐달라고 하면 해당 부분만 다시 만든다.
전체를 다시 돌리지 말고 **바꿀 트랙만** 교체한다 (예: 자막만 → `text` 트랙만 재생성).

### 자막 모양 — `text_material()` / `base_segment()`

| 사용자가 이렇게 말하면 | 조정 |
|---|---|
| "자막이 작아 / 커" | `size` (하단 자막 8~10, 중간 11~14, 메인 타이틀 20~26) |
| "글씨가 안 보여" | `border=(0,0,0)` + `border_width` ↑, `shadow=True` |
| "색 바꿔줘" | `color=(r,g,b)` 0~1 — 노랑 `(1,0.83,0.37)`, 하늘 `(0.3,0.64,1)` |
| "위로 / 아래로" | `y` — 상단 `+0.3`, 중앙 `0.0`, 하단 `-0.72`, 더 아래 `-0.85` |
| "굵게" | `bold=True` |
| "자막이 영상 가려" | `y` 를 더 아래로, `size` ↓ |

분할 자체(길이·개수)를 바꾸려면 `ai-video-edit` 의 `--soft`/`--gap` 을 조정해 다시 뽑는다.

### 전환·애니메이션 교체

| 사용자가 이렇게 말하면 | 조정 |
|---|---|
| "전환이 촌스러워 / 다른 걸로" | `find_effect("transition_meta", ...)` 로 다른 이름. 무난한 것: `叠化`(디졸브), `白色闪光`, `向右` |
| "전환이 너무 길어 / 짧아" | transition material 의 `duration` (기본은 카탈로그 값) |
| "등장 효과 바꿔줘" | `video_intro` 251개 / `text_intro` 182개 중 선택 |
| "효과 다 빼줘" | 해당 material 과 `extra_material_refs` 항목을 함께 제거 (짝 규칙) |

### 오버레이·모션그래픽

| 사용자가 이렇게 말하면 | 조정 |
|---|---|
| "타이틀 문구 바꿔줘" | 컴포지션 HTML 수정 → 다시 렌더 → `asset_path()` 로 교체 |
| "더 일찍 / 늦게 나오게" | 오버레이 세그먼트의 `target_timerange.start` |
| "타이틀이 커 / 작아" | 세그먼트의 `clip.scale` |
| "위치 옮겨줘" | `clip.transform` |

### 되돌리기

`save()` 가 매번 `/tmp/capcut_bak_<타임스탬프>/` 에 미러 6개를 백업한다.
"이전 걸로 돌려줘" 요청을 받으면 해당 백업을 그대로 복사해 되돌린다.

## 결과 보고

파일 편집 방식이라 **사용자가 캡컷을 열어야 확인된다.** 무엇을 어디서 봐야 하는지
시각별로 알려준다. 겹치는 효과가 있으면 판별이 흐려지니 검증용은 격리해서 넣는다.

## 그 밖의 요청 — `references/recipes.md` 를 먼저 볼 것

기능별 ✅/⬜ 매트릭스와 검증된 코드가 있다. 목록에 없는 기능은 `ai-video-edit` 의
"만들어서 쓴다" 절차를 따르고, 결과를 매트릭스에 기록한다.
