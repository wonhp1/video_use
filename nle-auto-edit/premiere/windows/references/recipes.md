# Premiere 기능 검증 매트릭스 (execute_extendscript 직접 호출)

> ⚠️ **Windows 주의**: 경로는 macOS 기준. Windows는 `C:/Program Files/Adobe/Adobe Premiere Pro 2026/...`,
> 작업 경로는 프로젝트 폴더(`<WORK>`)로 치환. 한글 폰트는 `local("Malgun Gothic")` 등. ExtendScript 로직은 OS 무관.

Premiere **26.2.2** 에서 실제 실행 → **읽기로 상태 재확인**까지 통과한 것만 ✅. "성공 응답"은 믿지 않는다(MCP 기본 도구가 성공만 보고하고 미실행되는 사례 다수).

테스트 소스: `C0323.MP4` 12.5초 / 2160×3840 세로 / 119.88fps.

## 이 문서를 늘리는 방법 (새 기능 검증 후)

매트릭스에 없는 기능을 요청받아 검증했으면 **결과를 여기에 남긴다** — 성공이든 실패든. 그래야 다음에 같은
요청이 왔을 때 즉시 실행하거나, 같은 삽질을 반복하지 않는다.

- **성공** → 해당 차수 표에 `| 번호 | 기능 | ✅ | 핵심 API |` 한 줄 + 아래에 `### 기능명` 절로 **검증된 코드**와
  걸렸던 함정을 적는다. 판정은 읽기 재확인까지(그래픽·애니메이션은 렌더 프레임 확인까지).
- **실패** → `❌` 로 넣고 **"시도한 것"** 목록을 남긴다(메서드 이름/인자 조합/위치/다른 계층 시도까지).
  양식은 아래 "트랜지션(2-1) — 시도한 것" 참고. 우회 대안이 있으면 함께 적는다.
- 무거운 작업(대량 렌더 등)은 🚨 경고를 함께 남긴다.

---

## 공통 함정 (먼저 읽기)

- **컴포넌트/속성 이름이 로케일 언어로 나온다** (한국어면 "모션","불투명도","볼륨","텍스트"). 이름 매칭 대신
  **구조로 판별**하라: 모션=속성 11개, 불투명도=3개, 텍스트=첫 속성이 string.
- **QE 객체는 stale** 된다 → 매 작업 직전 `qe.project.getActiveSequence()...` 새로 fetch.
- **비표준 fps**(119.88 등)에서 razor는 타임코드 문자열만 정확 → `setPlayerPosition(frameTicks)` → `CTI.timecode` → `razor(tc)`.
- 파괴적 작업 전 **안전장치**(아래 0차) 먼저.

---

## 0차 안전장치

| #   | 기능               | 상태 | 핵심                       |
| --- | ------------------ | ---- | -------------------------- |
| 0-1 | 프로젝트 백업 저장 | ✅   | `app.project.saveAs(path)` |
| 0-2 | 시퀀스 복제        | ✅   | `seq.clone()`              |

```javascript
// 0-1 백업 스냅샷 만들고 원래 프로젝트로 복귀 (saveAs는 "현재 작업본"을 새 경로로 바꾼다)
var orig = app.project.path;
var backup = orig.replace(/\.prproj$/i, "_BACKUP.prproj");
app.project.saveAs(backup); // 이제 작업본 = backup
app.project.saveAs(orig); // 원래 경로로 복귀 → backup 파일이 스냅샷으로 남음

// 0-2 복제본에서 안전하게 실험 (복제하면 복제본이 자동 활성화됨)
app.project.activeSequence.clone();
```

---

## 1차 — 기본 편집 (8/8 판정 완료)

| #   | 기능                      | 상태 | 핵심 API                                                                          |
| --- | ------------------------- | ---- | --------------------------------------------------------------------------------- |
| 1-1 | 속도/슬로모션             | ✅   | QE `clip.setSpeed(speed, durTC, reverse, maintainPitch, ripple)` — **5인자 필수** |
| 1-2 | 스케일·위치·회전·불투명도 | ✅   | `clip.components[].properties[].setValue(v, true)`                                |
| 1-3 | 트림(길이 조정)           | ✅   | `var t=clip.end; t.seconds=N; clip.end=t;`                                        |
| 1-4 | 클립 이동                 | ✅   | `clip.move(Time)` — **상대 오프셋**(절대 위치 아님)                               |
| 1-5 | 영상 export               | ✅   | `seq.exportAsMediaDirect(out, preset, 0)` + H264 Match Source 프리셋              |
| 1-6 | 프레임 캡처(썸네일) | ✅ | PNG 시퀀스 프리셋 + in/out + **workArea=1** (ffmpeg 폴백도 가능) |
| 1-7 | 텍스트/타이틀(MOGRT) | ❌ | 클립·텍스트값은 들어가나 **화면에 렌더 안 됨** → 모션그래픽 절(아래) 사용 |
| 1-8 | 오디오 볼륨               | ✅   | 볼륨 컴포넌트 `properties[1]`(레벨) setValue                                      |

### 1-1 속도 / 슬로모션

```javascript
app.enableQE();
var qeClip = qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(0);
qeClip.setSpeed(0.5, "00:00:25:02", false, true, true); // 50% 속도
// 인자 부족하면 "Not Enough Parameters". speed는 배율(0.5=50%).
// 주의: 속도만 바꾸면 클립 길이는 그대로 → 길이도 늘리려면 1-3 트림 병행:
var d = app.project.activeSequence.videoTracks[0].clips[0];
var t = d.end;
t.seconds = 25.02;
d.end = t;
```

### 1-2 스케일·위치·회전·불투명도 (로케일 무관 판별)

```javascript
var clip = app.project.activeSequence.videoTracks[0].clips[0];
var motion = null,
  opacity = null;
for (var i = 0; i < clip.components.numItems; i++) {
  var c = clip.components[i];
  if (c.properties.numItems >= 11) motion = c; // 모션
  if (c.properties.numItems === 3) opacity = c; // 불투명도
}
motion.properties[0].setValue([0.3, 0.5], true); // 위치 (0~1 정규화)
motion.properties[1].setValue(50, true); // 비율 조정 %
motion.properties[4].setValue(15, true); // 회전 도
opacity.properties[0].setValue(60, true); // 불투명도 %
// 모션 속성 순서: 0위치 1비율 2폭비율 3균일비율 4회전 5기준점 6깜박임 7~10 자르기(좌상우하)
```

### 1-4 클립 이동 (상대 오프셋)

```javascript
var d = app.project.activeSequence.videoTracks[0].clips[0];
var t = d.start;
t.seconds = 2;
d.move(t); // +2초 뒤로
var t2 = d.start;
t2.seconds = -2;
d.move(t2); // 원위치(음수 오프셋)
```

### 1-5 영상 export (세로 4K·고프레임 그대로 유지 확인됨)

```javascript
var preset =
  "/Applications/Adobe Premiere Pro 2026/Adobe Premiere Pro 2026.app/Contents/MediaIO/systempresets/3F3F3F3F_4D6F6F56/H264 Match Source - High bitrate.epr";
app.project.activeSequence.exportAsMediaDirect("/tmp/out.mp4", preset, 0); // 0=시퀀스 전체
```

검증: 2160×3840 / 119.88fps / H.264 그대로 출력됨. 오디오 전용은 `WAV_Mono_16bit_16kHz.epr`(자막용).

### 1-6 프레임 캡처 ✅ (PNG 시퀀스 프리셋 + in/out 방식)

`seq.exportFramePNG/JPEG`는 없고 QE `exportFramePNG`도 파일을 못 만든다. 대신 **검증된 export 경로를 재활용**한다:
시퀀스 in/out을 원하는 지점 1~2프레임으로 잡고 **PNG 시퀀스 프리셋 + workArea=1**로 내보내면 그 구간만 PNG가 나온다.

```javascript
var TPS = 254016000000,
  seq = app.project.activeSequence;
var fps = TPS / parseFloat(seq.timebase),
  tb = parseFloat(seq.timebase);
function ticksAt(s) {
  return String(Math.round(Math.round(s * fps) * tb));
}
var preset =
  "/Applications/Adobe Premiere Pro 2026/Adobe Premiere Pro 2026.app/Contents/MediaIO/systempresets/3F3F3F3F_504E4720/PNG Sequence (Match Source).epr";
seq.setInPoint(ticksAt(5));
seq.setOutPoint(ticksAt(5 + 2 / fps)); // 5초 지점 몇 프레임만
seq.exportAsMediaDirect("/tmp/thumb.png", preset, 1); // ⚠️ 3번째 인자 1 = in/out 구간
// → /tmp/thumb0.png, thumb1.png 생성 (2160×3840 확인). 파일명에 번호가 붙는다.
```

> 🚨 **workArea 인자 주의**: `0`(전체)이나 `2`로 주면 **시퀀스 전 프레임을 PNG로 쏟아낸다**
> (12.5초·119fps = 1500장, 렌더가 몇 분간 프리미어를 점유). 반드시 **1**을 쓰고 in/out을 좁게 잡을 것.

**더 가볍게 하려면 ffmpeg 폴백**도 여전히 유효(프리미어를 점유하지 않아 빠름):

```bash
ffmpeg -y -ss 5 -i "<video>" -frames:v 1 /tmp/thumb.png
```

### 1-7 타이틀(MOGRT) 삽입 + 텍스트 변경

```javascript
var seq = app.project.activeSequence,
  TPS = 254016000000;
var mogrt =
  "/Applications/Adobe Premiere Pro 2026/Adobe Premiere Pro 2026.app/Contents/Essential Graphics/Basic Title.mogrt";
seq.importMGT(mogrt, String(Math.round(1 * TPS)), 1, 0); // 1초 지점, V2 트랙

// 텍스트 내용 변경 — getMGTComponent()는 null이라 못 쓴다. 컴포넌트를 직접 찾을 것:
var g = seq.videoTracks[1].clips[0];
for (var i = 0; i < g.components.numItems; i++) {
  var c = g.components[i];
  if (
    c.properties.numItems > 0 &&
    typeof c.properties[0].getValue() === "string"
  ) {
    c.properties[0].setValue("원하는 문구", true); // "소스 텍스트"
    break;
  }
}
```

템플릿 154개가 `/Applications/Adobe Premiere Pro 2026/.../Contents/Essential Graphics/` 및
`~/Library/Application Support/Adobe/Common/Motion Graphics Templates/` 에 있다(Basic Title, Basic Lower Third 등).

### 1-8 오디오 볼륨

```javascript
var a = app.project.activeSequence.audioTracks[0].clips[0];
a.components[0].properties[1].setValue(0.5, true); // 볼륨 컴포넌트 → [1]=레벨
```

---

## 2차 — 범용 편집 (7/7 판정 완료)

| #   | 기능                  | 상태 | 핵심                                                             |
| --- | --------------------- | ---- | ---------------------------------------------------------------- |
| 2-1 | 트랜지션 | ❌ | 모든 접근 소진 — 아래 "시도한 것" 참고 |
| 2-2 | 비디오 효과           | ✅   | QE `getVideoEffectByName` + `clip.addVideoEffect`                |
| 2-3 | Lumetri/LUT           | ✅   | 위와 동일, 이름 `"Lumetri 색상"`                                 |
| 2-4 | 볼륨 키프레임(페이드) | ❌ | 키는 생기나 **렌더 미반영**(불투명도·위치로 실측 확인) |
| 2-5 | 모션 키프레임(줌/팬) | ❌ | 동일 — API 성공·렌더 미반영 |
| 2-6 | 갭 찾기               | ✅   | DOM 순회로 계산 (읽기)                                           |
| 2-7 | 씬 감지 | ⚠️ | Scene Edit Detection **스크립트 미노출 확정** → ffmpeg 폴백 |

### 2-2 / 2-3 효과 · Lumetri 적용

```javascript
app.enableQE();
// 사용 가능한 효과 이름 목록(134개, 로케일 언어로 나옴)
var list = qe.project.getVideoEffectList(); // "빠른 흐림", "Lumetri 색상", "가우시안 흐림(기존)" ...
var fx = qe.project.getVideoEffectByName("빠른 흐림");
qe.project
  .getActiveSequence()
  .getVideoTrackAt(0)
  .getItemAt(0)
  .addVideoEffect(fx);
// 확인: DOM clip.components.numItems 가 늘어야 성공
```

효과 파라미터는 추가 후 `clip.components[N].properties[i].setValue(v,true)` 로 조정(1-2와 동일 패턴).

### 2-6 갭 찾기

```javascript
var v1 = app.project.activeSequence.videoTracks[0],
  gaps = [],
  prev = 0;
for (var c = 0; c < v1.clips.numItems; c++) {
  var cl = v1.clips[c];
  if (cl.start.seconds - prev > 0.04) gaps.push([prev, cl.start.seconds]);
  prev = cl.end.seconds;
}
```

갭 "제거"는 무음컷과 동일하게 QE ripple delete(`assets/cut_silence.jsx` 패턴) 사용.

### 2-7 씬 감지 — ffmpeg 폴백

```bash
ffmpeg -i "<video>" -filter:v "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep -oE "pts_time:[0-9.]+"
```

나온 초 단위 지점을 컷 목록으로 삼아 `cut_silence.jsx`의 razor 패턴으로 분할.

### 2-4 / 2-5 키프레임 ❌ — API는 성공, **렌더에는 반영 안 됨** (실측 확인)

키를 "만드는" 것까지는 된다. **CTI 이동 + ticks 문자열**이면 `getKeys().length`도 늘고 `getValueAtKey()`도 값을 돌려준다:

```javascript
function setKeyframe(prop, sec, val){
  seq.setPlayerPosition(ticksAt(sec));   // CTI 이동 — 없으면 키 자체가 안 생김
  prop.addKey(ticksAt(sec));             // 초 숫자·Time 객체로는 실패
  prop.setValueAtKey(ticksAt(sec), val, true);
}
```

**그런데 렌더 결과에는 적용되지 않는다.** 실측: 오버레이 불투명도에 페이드(0→100→0) 키를 걸고 export 하면
그 오버레이가 **화면에 아예 안 나온다**(불투명도 0에 머문 것처럼). 키프레임을 지우고 정적 값 100으로
바꾸면 **즉시 정상 렌더**. 위치 키프레임도 동일(설정한 y가 렌더 시 기본값으로 돌아감).

→ **프리미어 키프레임으로 애니메이션을 만들지 말 것.** 움직이는 그래픽은 아래 **모션그래픽** 절을 쓴다.
정적 값 변경(1-2)은 렌더에 정상 반영되므로 문제없다.

> ⚠️ 이 항목은 한때 ✅로 잘못 기록했었다. `getKeys()`/`getValueAtKey()` 반환값만 보고 판정했고
> **화면 결과를 확인하지 않았기 때문**이다. 그래픽·애니메이션은 반드시 export → 프레임 추출로 눈으로 볼 것.
## 3차 — 프로젝트 관리 (5/5 판정 완료)

| #   | 기능                 | 상태 | 핵심                                              |
| --- | -------------------- | ---- | ------------------------------------------------- |
| 3-1 | import + 빈 생성     | ✅   | `rootItem.createBin(name)`, `importFiles([...])`  |
| 3-2 | 이름 변경            | ✅   | `projectItem.name = "새이름"`                     |
| 3-3 | 오프라인 재연결      | ✅   | `projectItem.changeMediaPath(path, true)`         |
| 3-4 | 미사용 미디어 리포트 | ✅   | 시퀀스 클립의 `projectItem.nodeId` 집합과 대조    |
| 3-5 | 프록시 연결          | ✅   | `projectItem.attachProxy(path, 0)` → `hasProxy()` |

```javascript
// 3-1 빈 생성 + 3-2 이름 변경
var bin = app.project.rootItem.createBin("소스");
bin.name = "원본소스";

// 3-3 재연결 (외장 드라이브 경로 바뀌었을 때)
projectItem.changeMediaPath("/new/path/clip.mp4", true);

// 3-4 미사용 미디어 찾기
var used = {},
  seq = app.project.activeSequence;
for (var t = 0; t < seq.videoTracks.numTracks; t++) {
  var tr = seq.videoTracks[t];
  for (var c = 0; c < tr.clips.numItems; c++) {
    try {
      used[tr.clips[c].projectItem.nodeId] = 1;
    } catch (e) {}
  }
}
// rootItem.children 순회하며 type===1(미디어) 이고 used에 없으면 미사용

// 3-5 프록시 연결
projectItem.attachProxy("/path/proxy.mp4", 0); // → hasProxy() === true
```

---

## 모션그래픽 (움직이는 타이틀·오버레이) ✅ — hyperframes로 미리 렌더

**프리미어 안에서 애니메이션을 만들려 하지 말 것.** 키프레임(2-4/2-5)·트랜지션(2-1)·MOGRT(1-7)는 모두
렌더에 반영되지 않는다. 대신 **애니메이션은 밖에서 알파 영상으로 렌더**하고, 프리미어는 그 클립을
**정적으로 배치**만 한다(정적 배치·위치·크기는 ✅ 검증됨).

### 절차 (실측 검증됨)

1. **작업 폴더 + 초기화** — 추가 설치 불필요(`npx`가 자동 다운로드; Node는 MCP 때문에 이미 필요)
   ```bash
   mkdir -p <work>/mograph/<name> && cd <work>/mograph/<name>
   npx --yes hyperframes@latest init --example blank    # → ./my-video/ 생성
   ```
2. **컴포지션 작성** — `my-video/index.html`. 상세 규칙은 `/hyperframes` 스킬 계열이 관리하니 그쪽을 따르되,
   최소 계약은 다음과 같다(이걸 어기면 렌더가 깨진다):
   - 루트에 `data-composition-id` + `data-width/height` + **명시적 `width/height` CSS**
   - 타임드 요소는 `class="clip"` + `data-start/data-duration/data-track-index` + 고유 `id`
   - `gsap.timeline({paused:true})` **하나**를 `window.__timelines["<id>"]`에 등록하고 `tl.seek(0)`
   - 등장은 `fromTo()`(autoAlpha 사용), 결정론적만(`Date.now()`/`Math.random()` 금지)
   - 오버레이는 `body/html` 배경을 `transparent`로 (알파 보존)
   - **한글 폰트**: 시스템 폰트는 `@font-face { font-family:"Apple SD Gothic Neo"; src: local("AppleSDGothicNeo-Bold"); }`
     로 선언해야 lint를 통과하고 렌더에 실제 적용된다.
3. **검증** — `npm run check` (0 에러여야 함) → `npx hyperframes snapshot --at 0.4,1.2,4.6` 후 **contact-sheet.jpg를 눈으로 확인**
4. **렌더** — 알파는 `--format mov`가 자동으로 ProRes 4444(`yuva444p12le`)로 나온다. `--codec` 플래그는 없다.
   ```bash
   npx --yes hyperframes@<pinned> render . --format mov -q high -o ./renders/title.mov   # 알파(프리미어용)
   npx --yes hyperframes@<pinned> render . -q high -o ./renders/title.mp4                # 번인/미리보기용
   ```
5. **프리미어에 배치** (검증된 API만 사용)
   ```javascript
   app.project.importFiles(["<...>/renders/title.mov"], true, app.project.rootItem, false);
   // 프로젝트에서 title.mov projectItem 찾은 뒤:
   app.project.activeSequence.videoTracks[1].overwriteClip(item, ticksAt(1));  // V2, 1초 지점
   // 위치·크기 조정이 필요하면 1-2의 정적 setValue 사용 (키프레임 X)
   ```
6. **결과 확인** — 시퀀스 in/out을 그 구간으로 잡고 `exportAsMediaDirect`(1-5) → ffmpeg로 프레임 추출해
   **오버레이가 실제로 보이는지** 눈으로 확인한다.

### 검증 기록

세로 4K(2160×3840) 5초 타이틀 카드 — 아래에서 슬라이드 + 페이드인/아웃, 한글 텍스트.
`title.mov` 75MB(ProRes 4444, 알파 확인) → 프리미어 V2 1~6초 배치 → export → 프레임 3장에서
**페이드인 → 등장완료 → 유지**가 영상 위에 정상 합성됨.

> 캔버스 크기를 소스 시퀀스와 동일하게(예: 2160×3840) 잡으면 배치 시 스케일 조정이 필요 없다.

---

## 최종 요약 (23개 항목 — 렌더 실측 반영)

**판정 기준을 "API 성공"이 아니라 "렌더 결과에 실제로 나타남"으로 통일한 최종 집계.**

- ✅ **18개 작동**: 백업·시퀀스복제 / 속도 · 정적 스케일·위치·회전·불투명도 · 트림 · 이동 · 볼륨 /
  영상 export / 프레임캡처 / 효과·Lumetri / 갭찾기 / 빈·이름·재연결·미사용·프록시 /
  **모션그래픽 오버레이(hyperframes 알파 mov)**
- ⚠️ **1개 ffmpeg 폴백**: 씬 감지 (Premiere가 스크립트로 노출 안 함)
- ❌ **4개 불가 — 전부 "호출은 성공, 렌더 미반영"**: 트랜지션(2-1), 볼륨 키프레임(2-4),
  모션 키프레임(2-5), MOGRT 타이틀(1-7) → **모션그래픽 절의 hyperframes 방식으로 대체**

### 판정 원칙 (아프게 배운 것)

1. **정적 값 변경은 렌더에 반영된다** — 크기·위치·불투명도·볼륨·효과.
2. **애니메이션·그래픽 생성은 반영되지 않는다** — 키프레임·트랜지션·MOGRT.
3. 그래서 **애니메이션은 밖에서 렌더하고 프리미어는 배치만** 한다.
4. 그래픽/애니메이션 판정은 **export → 프레임 추출 → 눈으로 확인**까지 해야 유효하다.
   `getKeys()`·`getValueAtKey()`·클립 수 증가는 "적용됨"의 증거가 아니다.

### 트랜지션(2-1) — 시도한 것 (같은 삽질 반복 방지용)

`qeItem.addTransition`만 존재하고 호출은 항상 "성공"하지만 타임라인에 **Transition 아이템이 생기지 않는다**.
소진한 조합:
- 트랜지션 이름 4종: `교차 디졸브`(없음) / `크로스 디졸브(레거시)` / `비추가 디졸브` / `추가 디졸브` — 객체는 정상 획득
- 인자 개수: `(tr)` / `(tr,true)` / `(tr,true,tc)` / `(tr,true,tc,dur)` / `(tr,true,tc,dur,align,...)`
- 위치: 클립 1개일 때 시작부 / 클립 2개(razor로 경계 생성) 후 첫 클립 끝·둘째 클립 시작
- 다른 레벨: `track.addTransition`·`seq.addTransition`·`addDefaultTransition`·`addAudioTransition` — **메서드 자체가 없음**

**대안**: 디졸브 느낌이 필요하면 **불투명도 키프레임**(2-4/2-5 패턴)으로 페이드 인/아웃을 직접 만든다.
오디오 크로스페이드도 마찬가지로 볼륨 키프레임으로 대체.

**교훈**: "호출 성공"과 "실제 적용"은 다르다. 반드시 읽기로 재확인할 것.
