# 파이널컷 FCPXML — 실측 검증 기록

파이널컷은 잘못된 FCPXML을 **오류 없이 조용히 버리기도** 한다. 아래는 전부 실제로 겪은 것.

## 🚨 파이널컷이 거부하거나 버리는 조건

| # | 증상 | 원인 | 해결 |
|---|---|---|---|
| 1 | `Element effect does not carry attribute uid` | `<effect>` 에 uid 없음 | Basic Title uid 상수 주입 |
| 2 | `항목이 편집 프레임 경계에 있지 않음` | 시간값이 frameDuration 정수배가 아님 | 전 값을 프레임에 스냅 |
| 3 | **자막이 오류 없이 사라짐** | `<title>` 을 spine 의 형제로 둠 | **`<asset-clip>` 의 자식으로 중첩** |
| 4 | `이름에는 '/' 를 사용할 수 없습니다` | 프로젝트/이벤트 이름에 `/` | 이름 살균 |
| 5 | 플래시 프레임 경고 | 3프레임 미만 클립 | 최소 유지 길이 필터 |
| 6 | 자막 겹침 | 같은 lane 중첩 | 다음 자막 시작까지 트림 |
| 7 | **자막이 화면 밖으로 사라짐** | `adjust-transform position` 을 픽셀로 착각 | **값 × (높이÷100) = 픽셀** |
| 8 | **키프레임이 무시됨** | `scale` 키프레임에 `interp`/`curve` 지정 | 두 속성을 빼면 적용됨 |
| 9 | 전환이 `유효하지 않은 편집` | 전환 옆에 속도 변경 클립 | 전환과 속도를 인접시키지 않는다 |
| 10 | 속도 클립이 `미디어 없음` | `timept` 의 `time` 을 0부터 시작 | `time` 은 클립 `start` 와 같은 시간계 |
| 11 | 전환이 회색 빈칸 | `<filter-video>` 생략 | `uid="FFTransition_CrossDissolve"` 효과를 참조 |

### 3번이 가장 위험하다 — 조용한 실패

DTD 주석: *"The 'lane' attribute specifies where the object is anchored **relative to its parent**"*
`<spine>` 의 자식으로 두면 부모가 spine 이라 앵커가 성립하지 않고, 파이널컷은 **경고 없이 버린다.**

```xml
<!-- ❌ 조용히 사라짐 -->
<spine>
  <asset-clip .../>
  <title lane="1" .../>
</spine>

<!-- ✅ -->
<spine>
  <asset-clip ...>
    <title lane="1" offset="<클립 start 기준 상대시간>" .../>
  </asset-clip>
</spine>
```
연결 클립이 앵커 클립 범위를 **넘어가는 것은 정상**이다. 이걸 문제로 착각해 spine 으로 옮기면 안 된다.

자막 offset 환산: `local = clip.start + (자막 절대시각 − clip.타임라인offset)`

### 자막 위치 — `adjust-transform` (템플릿 param 을 추측하지 말 것)

```xml
<title ...>
  <text>…</text>
  <text-style-def>…</text-style-def>
  <adjust-transform position="0 -36"/>   <!-- DTD 내용 모델상 맨 뒤 -->
</title>
```

🚨 **position 은 픽셀이 아니다.** 실측: `값 × (프레임높이 ÷ 100) = 화면상 픽셀`.
1920 높이에서 `-691` 을 주면 인스펙터에 **-13267.2px** 로 찍히고 자막이 화면 밖으로 날아간다.
하단 자막은 대략 `-36` (= -691px).

DTD 는 `position CDATA "0 0"` 이라고만 해서 단위를 알려주지 않는다.
**인스펙터에 찍힌 값과 비교해 배율을 역산하는 것이 유일한 확인법이다.**

### 자막 줄바꿈
세로 영상(1080 폭)은 13자쯤에서 어절 단위로 끊지 않으면 좌우가 잘린다.
글자 크기는 캔버스 폭의 약 4.5% (1080 → 49px).

### 자막 기본값 (사용자 확정, 2026-08-23)

| 항목 | 기본 | 비고 |
|---|---|---|
| 글자색 | **흰색** `1 1 1 1` | |
| 테두리 | **없음** | 요청이 있을 때만 `stroke=(색)` 로 켠다 |
| 글꼴 | Apple SD Gothic Neo / Bold | 이 시스템의 한글 폰트는 사실상 3종뿐 |
| 크기 | 캔버스 폭의 4.5% | 1080 → 49px |
| 위치 | 캔버스 높이의 -36% | 1080×1920 → -691px (하단) |
| 줄바꿈 | 세로 13자 / 가로 20자 | 어절 단위 |

🚨 **기본값에 판단을 심지 말 것.** 처음에 "자막은 테두리가 있어야 잘 보인다"고 검은 테두리를
기본으로 넣었다가 지적받았다. 가독성 보정은 **사용자가 요청할 때** 하는 것이지 강제할 게 아니다.
색 지정은 `"R G B A"` (0~1 실수): 흰 `1 1 1 1` / 검정 `0 0 0 1` / 노랑 `1 0.85 0.2 1`.

### 자막 텍스트 구조
```xml
<title ref="e1" lane="1" offset="..." duration="...">
  <text><text-style ref="ts1">내용</text-style></text>
  <text-style-def id="ts1">
    <text-style font="..." fontSize="64" fontColor="1 1 1 1"
                strokeColor="0 0 0 1" strokeWidth="4.0" alignment="center"/>
  </text-style-def>
</title>
```
`<param name="Text">` 형식은 DTD 는 통과하지만 표준이 아니다.

Basic Title uid:
`.../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti`

## 🚨 MCP 도구를 믿지 마라

| 도구 | 문제 |
|---|---|
| `fcpxml_validate` | **DTD 위반을 "VALID 0 errors" 로 통과시킴.** 반대로 `media-rep` 이 있는데 "no source path" 오탐 |
| `fcpxml_import_srt` | `<effect>` uid 누락 + 시간값 프레임 미정렬 |
| `fcpxml_create_timeline` | 크기 인자가 없어 **세로 프로젝트 불가** (`fcpxml_reformat` 으로 우회) |

**검증은 파이널컷과 같은 DTD 로 한다:**
```bash
# DOCTYPE 에 SYSTEM 식별자를 넣은 사본을 만들어야 한다. 안 그러면 xmllint 가
# "no DTD found" 를 내면서도 종료코드로만 알려줘 거짓 통과하기 쉽다.
xmllint --noout --valid <SYSTEM 식별자 넣은 사본>
echo $?   # 0 이어야 통과
```
DTD 도 프레임 정렬은 못 잡는다 → 자체 전수 검사 필요.

## 검증 현황

| # | 기능 | 상태 |
|---|---|---|
| 1 | 무음 컷 (구간 재구성) | ✅ |
| 2 | 자막 (색·글꼴·굵기·크기·위치·줄바꿈) | ✅ |
| 3 | 세로 프로젝트 (1080×1920) | ✅ |
| 4 | 비표준 fps 소스 (119.88) | ✅ ffprobe 실측 + 회전 플래그 반영 |
| 5 | AppleScript 읽기 (라이브러리·프로젝트) | ✅ |
| 6 | 트랜지션 (Cross Dissolve) | ✅ | `uid="FFTransition_CrossDissolve"` + `<filter-video>` 필수 |
| 7 | 오버레이 / 알파 모션그래픽 | ✅ | `<asset-clip lane="1">` 클립 자식. ProRes 4444 알파 동작 |
| 8 | 배경음악 | ✅ | `<audio lane="-1" role="music">` + `<adjust-volume amount="-12dB">` |
| 9 | 속도 변경 | ✅ | `<timeMap>` — time 은 클립 start 시간계 |
| 10 | 키프레임 (확대) | ✅ | `adjust-transform/param/keyframeAnimation`, interp·curve 금지 |

## 워크플로 특성

임포트 시 **"보관함 열기" 대화상자가 반드시 뜬다** — 사용자가 보관함을 골라야 한다.
프리미어(실시간)·캡컷(앱 종료 후)과 달리 파이널컷은 **임포트마다 클릭 1회**가 필요하다.

임포트는 항상 **새 이벤트**를 만든다(같은 이름이면 `이름 2`, `이름 3`…).
기존 프로젝트를 덮어쓰지 않으므로 안전하지만, 시도가 쌓이면 사용자가 어느 게 최신인지 헷갈린다.
→ **결과 보고 시 이벤트/프로젝트 이름을 정확히 알려줄 것.**
