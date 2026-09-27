// add_subtitles.jsx (Windows판) — SRT import + 자막 캡션 트랙 자동 생성.
//
// execute_extendscript 실행 전에 __SRT_PATH__ 를 실제 SRT 경로(슬래시)로 치환한다.
//   예: "C:/Users/me/myproject/premiere-auto-edit/cut_audio.srt"
//
// 핵심: createCaptionTrack(projectItem, 0, Sequence.CAPTION_FORMAT_SUBTITLE) 직접 호출.
//   (for..in 으로는 안 보이는 네이티브 메서드지만 실제로 동작.) 수동 드래그 불필요.

var seq = app.project.activeSequence;
if (!seq)
  return __error("활성 시퀀스가 없습니다. 타임라인을 열고 다시 실행하세요.");

var SRT = "__SRT_PATH__"; // ← 실행 전 실제 경로로 치환
if (!new File(SRT).exists)
  return __error(SRT + " 가 없습니다. 먼저 받아쓰기(SRT 생성)를 하세요.");

var base = SRT.replace(/\\/g, "/").split("/").pop();
function findCap() {
  for (var i = 0; i < app.project.rootItem.children.numItems; i++) {
    var it = app.project.rootItem.children[i];
    if (it.name === base) return it;
  }
  return null;
}
var cap = findCap();
if (!cap) {
  app.project.importFiles([SRT], true, app.project.rootItem, false);
  cap = findCap();
}
if (!cap) return __error("SRT 캡션 아이템을 찾지 못함: " + base);

var r = seq.createCaptionTrack(cap, 0, Sequence.CAPTION_FORMAT_SUBTITLE);
return __result({ created: String(r), caption: cap.name });
