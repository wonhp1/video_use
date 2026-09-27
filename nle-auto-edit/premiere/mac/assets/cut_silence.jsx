// cut_silence.jsx — 프레임 정확 무음 일괄 컷 (Premiere ExtendScript / QE DOM)
//
// 이 코드를 premiere-pro MCP 의 execute_extendscript 로 실행한다.
// /tmp/premiere_cuts.json 의 컷 구간([[s,e],...] 초 단위)을 읽어
// 활성 시퀀스의 V1·A1 트랙에서 해당 구간을 razor + ripple delete 한다.
//
// 왜 직접 QE 를 쓰는가:
//   premiere-pro-mcp 의 razor_all_tracks / ripple_delete 도구는 Premiere 2026 에서
//   "성공 보고만 하고 실제로는 미실행"되는 버그가 있다. 직접 QE 호출은 정상 동작한다.
//
// 비표준 fps(예: 25.504) 대응 — 프레임 정확 컷의 핵심:
//   QE razor 는 "타임코드 문자열"만 정확히 받는다(초/ticks 문자열은 부정확/무시됨).
//   정확히 자르려면: setPlayerPosition(프레임 경계 ticks) → CTI.timecode 읽기 → razor(tc).
//   ripple delete 는 qeItem.remove(true, true).
//   QE 객체는 호출마다 stale 될 수 있어 매번 새로 fetch 한다.
//   여러 컷은 역순(뒤→앞)으로 처리해 앞쪽 절대 시간이 안 틀어지게 한다.

app.enableQE();
var TPS = 254016000000;
var seq = app.project.activeSequence;
if (!seq) {
  return __error(
    "활성 시퀀스가 없습니다. 타임라인에 영상을 올리고 다시 실행하세요.",
  );
}
var tb = parseFloat(seq.timebase);
var fps = TPS / tb;

var f = new File("/tmp/premiere_cuts.json");
if (!f.exists) {
  return __error(
    "/tmp/premiere_cuts.json 이 없습니다. 먼저 detect_silence.sh 를 실행하세요.",
  );
}
f.open("r");
var raw = f.read();
f.close();
var cuts = eval(raw); // [[s,e],...]

function tcAt(sec) {
  var ticks = Math.round(Math.round(sec * fps) * tb);
  seq.setPlayerPosition(ticks.toFixed(0));
  return qe.project.getActiveSequence().CTI.timecode;
}
function razorBoth(sec) {
  var tc = tcAt(sec);
  qe.project.getActiveSequence().getVideoTrackAt(0).razor(tc);
  qe.project.getActiveSequence().getAudioTrackAt(0).razor(tc);
}
function ripple(sec) {
  var okV = false,
    okA = false;
  var v = qe.project.getActiveSequence().getVideoTrackAt(0);
  for (var i = 0; i < v.numItems; i++) {
    var it = v.getItemAt(i);
    var s = parseFloat(it.start.ticks) / TPS;
    if (it.type === "Clip" && s >= sec - 0.15 && s <= sec + 0.15) {
      it.remove(true, true);
      okV = true;
      break;
    }
  }
  var a = qe.project.getActiveSequence().getAudioTrackAt(0);
  for (var j = 0; j < a.numItems; j++) {
    var jt = a.getItemAt(j);
    var sa = parseFloat(jt.start.ticks) / TPS;
    if (jt.type === "Clip" && sa >= sec - 0.15 && sa <= sec + 0.15) {
      jt.remove(true, true);
      okA = true;
      break;
    }
  }
  return okV && okA;
}

var done = 0,
  fail = 0,
  errs = [];
for (var k = cuts.length - 1; k >= 0; k--) {
  try {
    var s = cuts[k][0],
      e = cuts[k][1];
    razorBoth(e);
    razorBoth(s);
    if (ripple(s)) done++;
    else {
      fail++;
      if (errs.length < 6) errs.push("noseg@" + Math.round(s * 10) / 10);
    }
  } catch (ex) {
    fail++;
    if (errs.length < 6) errs.push(ex.toString());
  }
}
var v1 = app.project.activeSequence.videoTracks[0];
var lastEnd = 0;
for (var c = 0; c < v1.clips.numItems; c++) {
  if (v1.clips[c].end.seconds > lastEnd) lastEnd = v1.clips[c].end.seconds;
}
return __result({
  totalCuts: cuts.length,
  done: done,
  fail: fail,
  errs: errs,
  resultClips: v1.clips.numItems,
  resultSeconds: Math.round(lastEnd * 10) / 10,
  resultMinutes: Math.round((lastEnd / 60) * 10) / 10,
});
