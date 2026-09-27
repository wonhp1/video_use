// add_subtitles.jsx — SRT를 import하고 활성 시퀀스에 "자막(Subtitle) 캡션 트랙"으로 올린다.
//
// execute_extendscript 로 실행. 타임라인에 자막이 시간 맞춰 자동으로 올라간다(수동 드래그 불필요).
//
// 핵심: createCaptionTrack(projectItem, startSec, Sequence.CAPTION_FORMAT_SUBTITLE) 직접 호출.
//   (이 메서드는 ExtendScript for..in 으로는 안 보이지만 — 네이티브 메서드라 — 실제로는 존재한다.)
//   CAPTION_FORMAT_SUBTITLE(0) = 크리에이터 자막. 방송용 CC는 _708(2)/_608(1).

var seq = app.project.activeSequence;
if (!seq)
  return __error("활성 시퀀스가 없습니다. 타임라인을 열고 다시 실행하세요.");

var SRT = "/tmp/cut_audio.srt"; // mac판: detect/transcribe 가 쓰는 경로
var f = new File(SRT);
if (!f.exists)
  return __error(SRT + " 가 없습니다. 먼저 받아쓰기(SRT 생성)를 하세요.");

// 1) SRT 를 프로젝트로 import (이미 있으면 중복 import 될 수 있으니 먼저 탐색)
var base = SRT.replace(/\\/g, "/").split("/").pop(); // "cut_audio.srt"
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

// 2) 자막 캡션 트랙 생성 (시작 0초)
var r = seq.createCaptionTrack(cap, 0, Sequence.CAPTION_FORMAT_SUBTITLE);
return __result({ created: String(r), caption: cap.name });
