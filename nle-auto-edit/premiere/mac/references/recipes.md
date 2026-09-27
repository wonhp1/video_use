# Premiere 기능 검증 매트릭스 (execute_extendscript 직접 호출)

Premiere **26.2.2** 에서 실제 실행 → **읽기로 상태 재확인**까지 통과한 것만 ✅. "성공 응답"은 믿지 않는다(MCP 기본 도구가 성공만 보고하고 미실행되는 사례 다수).

테스트 소스: `C0323.MP4` 12.5초 / 2160×3840 세로 / 119.88fps.

## 이 문서를 늘리는 방법 (새 기능 검증 후)

매트릭스에 없는 기능을 요청받아 검증했으면 **결과를 여기에 남긴다** — 성공이든 실패든. 그래야 다음에 같은
요청이 왔을 때 즉시 실행하거나, 같은 삽질을 반복하지 않는다.

- **성공** → 해당 차수 표에 `| 번호 | 기능 | ✅ | 핵심 API |` 한 줄 + 아래에 `### 기능명` 절로 **검증된 코드**와
  걸렸던 함정을 적는다. 판정은 읽기 재확인까지(그래픽·애니메이션은 렌더 프레임 확인까지).
- **실패** → `❌` 로 넣고 **"시도한 것"** 목록을 남긴다(메서드 이름/인자 조합/위치/다른 계층 시도까지).
  실패는 시도한 접근까지 적는다. 우회 대안이 있으면 함께 적는다.
- 무거운 작업(대량 렌더 등)은 🚨 경고를 함께 남긴다.

---

## 공통 함정 (먼저 읽기)

- **컴포넌트/속성 이름이 로케일 언어로 나온다** (한국어면 "모션","불투명도","볼륨","텍스트"). 이름 매칭 대신
  **구조로 판별**하라: 모션=속성 11개, 불투명도=3개, 텍스트=첫 속성이 string.
- **QE 객체는 stale** 된다 → 매 작업 직전 `qe.project.getActiveSequence()...` 새로 fetch.
- **비표준 fps**(119.88 등)에서 razor는 타임코드 문자열만 정확 → `setPlayerPosition(frameTicks)` → `CTI.timecode` → `razor(tc)`.
- 파괴적 작업 전 **안전장치**(아래 0차) 먼저.

---

## 🚨 로케일 함정 — 전환·효과는 **현지화된 이름**을 쓴다 (2026-08-23 실측)

`getVideoTransitionByName` / `getVideoEffectByName` 은 **한글 UI 에서 한글 이름만** 받는다.
영문 이름을 넣으면 **오류 없이 빈 껍데기 객체**가 돌아오고, 그걸로 호출하면 조용히 실패한다.

```javascript
qe.project.getVideoTransitionByName("Cross Dissolve"); // {name: ""} ← 껍데기
qe.project.getVideoTransitionByName("교차 디졸브");     // {name: "교차 디졸브"} ← 진짜
```

`null` 체크로는 못 거른다. **`String(obj.name) !== ""` 를 확인해야 한다.**

| 종류 | 확인된 한글 이름 |
|---|---|
| 전환 | `교차 디졸브` `검정으로 물들이기` `흰색으로 물들이기` `필름 디졸브` `페이지 넘기기` |
| 효과 | `Lumetri 색상` `가우시안 흐림` `흑백` `자르기` |

이 함정 하나가 트랜지션을 오랫동안 ❌ 로 오판하게 만들었다.

## 🚨 거짓 성공 목록 (true 를 반환하고 아무 일도 안 함)

| 호출 | 반환 | 실제 |
|---|---|---|
| `qe.move(timecode)` | `true` | 클립이 안 움직인다 → `clip.start = ticks` 를 쓴다 |
| `clip.addTransition(영문이름)` | `false` | 위 로케일 함정 |
| MCP `razor_all_tracks` / `split_clip` | (1.13.0 은 정직하게 실패 보고) | 26.x 에서 QE 구조 편집이 no-op |

MCP 가 `"Unavailable"` 이라고 답해도 믿지 말 것. 실제로는 되는 경우가 있다.

| MCP 판정 | 실제 |
|---|---|
| `add_transition`: *"does not expose qeTrack.addTransition"* | 트랙엔 없지만 **클립엔 있다** |
| `speed_change`: *"no supported scripting API"* | **5인자 필수**였을 뿐 |

## 환경 (premiere-pro-mcp 1.13.0 기준)

- `execute_extendscript` 는 **기본 차단**된다. MCP 설정에 다음이 필요하다:
  `"env": {"PREMIERE_MCP_CAPABILITIES": "inspect,edit,export,filesystem,unsafe-script"}`
- **CSInterface CEP12 패치는 1.13.0 부터 불필요** — 업스트림에 반영됐다.
  구버전(1.1.x)에만 패치가 필요하다. 무조건 덮어쓰면 오히려 구버전으로 되돌린다.

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
| 2-1 | 트랜지션 | ✅ | **클립**에 `addTransition` + **한글 이름**(2026-08-23 승격) |
| 2-2 | 비디오 효과           | ✅   | QE `getVideoEffectByName` + `clip.addVideoEffect`                |
| 2-3 | Lumetri/LUT           | ✅   | 위와 동일, 이름 `"Lumetri 색상"`                                 |
| 2-4 | 볼륨 키프레임(페이드) | ⬜ | 미검증 — 모션 키프레임은 ✅ 이므로 재시도 가치 있음 |
| 2-5 | 모션 키프레임(줌/팬) | ✅ | **일반 영상 클립에서 렌더 반영 확인**(2026-08-23) |
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

### 2-4 / 2-5 키프레임 ✅ — 일반 영상 클립에서는 렌더에 반영됨 (2026-08-23 승격)

```javascript
var clip = seq.videoTracks[0].clips[0];
// 로케일 무관하게 모션 찾기 (첫 매치에서 break — Lumetri 도 속성이 많다)
var motion = null;
for (var i = 0; i < clip.components.numItems; i++) {
  var c = clip.components[i], d = String(c.displayName);
  if (c.properties.numItems >= 5 && d.indexOf("벡터") < 0 &&
      d.indexOf("Lumetri") < 0 && d.indexOf("불투명") < 0) { motion = c; break; }
}
var prop = null;                       // "비율 조정" / "Scale"
for (var q = 0; q < motion.properties.numItems; q++) {
  var d2 = String(motion.properties[q].displayName);
  if (d2.indexOf("비율 조정") >= 0 || d2.indexOf("Scale") >= 0) { prop = motion.properties[q]; break; }
}
prop.setTimeVarying(true);
prop.addKey(0);  prop.addKey(5);
prop.setValueAtKey(0, 100, true);
prop.setValueAtKey(5, 160, true);
```

🚨 **반드시 렌더로 확인한다.** 이 항목은 과거에 두 번 오판했다 —
한 번은 `getKeys()` 반환값만 보고 ✅, 한 번은 합성 클립에서 안 먹는 걸 보고 ❌.
**일반 영상 클립**에서는 정상 동작한다(2026-08-23 프레임 비교로 확인).

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

**복잡한 모션 그래픽은 여전히 밖에서 렌더하는 게 낫다.** 키프레임·트랜지션·MOGRT 는 2026-08-23 에
전부 ✅ 로 승격됐지만, 다중 요소가 얽힌 애니메이션은 hyperframes 알파 mov 가 더 안정적이다. 아래 절차는
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
   - **`class="clip"` 요소 자체에는 autoAlpha·opacity·visibility 를 걸지 않는다** — clip 의 표시는 프레임워크가 관리해서
     `check` 가 `gsap_animates_clip_element` 로 실패한다(hyperframes 0.8.79 확인). clip 은 전체 화면 래퍼로 두고
     애니메이션은 그 **안쪽 요소**에 건다: `<div id="layer" class="clip" ...><div id="card">…</div></div>` → `tl.fromTo("#card", …)`
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

## 최종 요약 (23개 항목 — 2026-08-23 재검증 반영)

**판정 기준을 "API 성공"이 아니라 "렌더 결과에 실제로 나타남"으로 통일한 최종 집계.**

- ✅ **21개 작동**: 백업·시퀀스복제 / 속도 · 정적 스케일·위치·회전·불투명도 · 트림 · 이동 · 볼륨 /
  영상 export / 프레임캡처 / 효과·Lumetri / 갭찾기 / 빈·이름·재연결·미사용·프록시 /
  **모션그래픽 오버레이(hyperframes 알파 mov)**
- ⚠️ **1개 ffmpeg 폴백**: 씬 감지 (QE 메서드 자체가 없음 — 2026-08-23 재확인)
- ❌ **1개 불가**: 오디오 전환 (등록 이름을 못 찾음)
- 🎉 **2026-08-23 승격**: 트랜지션 · 모션 키프레임 · MOGRT (❌ → ✅)

### 판정 원칙 (아프게 배운 것)

1. **API 성공 ≠ 렌더 반영.** 반드시 export → 프레임 추출 → 눈으로 확인한다.
   같은 항목을 두 번 오판했다 — `getKeys()` 반환값만 보고 ✅, 합성 클립 실패만 보고 ❌.
2. **빈 껍데기 객체를 조심한다.** 전환·효과 조회는 `null` 이 아니라 `name === ""` 로 실패한다.
3. **"불가능"은 대개 "인자/경로가 틀렸다"이다.** 트랜지션(클립 vs 트랙), 속도(5인자),
   MOGRT — 셋 다 ❌ 였다가 승격됐다. MCP 가 unavailable 이라 해도 직접 확인한다.
4. **QE 객체는 호출 사이에 무효화된다.** 매번 새로 가져온다.
5. **검증 경로가 다를 수 있다.** 전환은 QE 목록에 안 나오고 `videoTracks[n].transitions` 에 있다.
6. 복잡한 다중 요소 애니메이션은 여전히 **hyperframes 알파 mov** 가 안정적이다.

### 트랜지션(2-1) ✅ — 클립에 붙인다 + 한글 이름 (2026-08-23 승격)

오랫동안 ❌ 였던 이유는 두 가지가 겹쳐서였다.
**① 트랙이 아니라 클립에 붙인다** ② **레지스트리가 한글 이름을 쓴다**

```javascript
app.enableQE();
function vtrack() { return qe.project.getActiveSequence().getVideoTrackAt(0); }

// ⚠️ QE 객체는 호출 사이에 무효화된다 — 매번 새로 가져올 것
var tr = qe.project.getVideoTransitionByName("교차 디졸브");   // 한글!
if (!tr || String(tr.name) === "") throw new Error("빈 껍데기");
var clip = vtrack().getItemAt(0);                              // 앞 클립
clip.addTransition(tr, false);                                 // → true

// 🚨 검증은 QE 아이템 목록이 아니라 표준 DOM 으로
var trs = app.project.activeSequence.videoTracks[0].transitions;
// trs.numItems, trs[i].name / .start.seconds / .duration.seconds
```

QE 의 `numItems` 목록에는 전환이 **안 나온다**. `videoTracks[n].transitions` 를 봐야 한다.
트랙에는 `addTransition` 계열 메서드가 **하나도 없다**(6종 전부 undefined).
오디오 전환은 등록 이름을 못 찾아 여전히 ❌.

