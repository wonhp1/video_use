// cut_silence.jsx (Windows판) — 프레임 정확 무음 일괄 컷 (Premiere ExtendScript / QE DOM)
//
// execute_extendscript 로 실행하기 전에, 아래 __CUTS_JSON__ 토큰을
// 실제 cuts.json 경로로 치환한다. (예: "C:/Users/me/myproject/premiere-auto-edit/cuts.json")
// ExtendScript File 은 Windows 에서도 슬래시(/) 경로를 받는다.
//
// 편집 로직은 Mac판과 동일(프리미어 내부에서 도는 코드라 OS 무관).
// 핵심: QE razor 는 타임코드 문자열만 정확 → setPlayerPosition(frameTicks) → CTI.timecode → razor(tc).
//       ripple delete = qeItem.remove(true,true). QE 객체는 매번 새로 fetch. 컷은 역순 처리.

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

var CUTS_PATH = "__CUTS_JSON__"; // ← 실행 전 실제 경로로 치환
var f = new File(CUTS_PATH);
if (!f.exists) {
  return __error(
    CUTS_PATH + " 가 없습니다. 먼저 detect_silence.py 를 실행하세요.",
  );
}
f.open("r");
var raw = f.read();
f.close();
var cuts = eval(raw);

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
