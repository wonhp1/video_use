// export_sequence_audio.jsx — 현재 활성 시퀀스의 "오디오만" 16kHz 모노 WAV로 내보낸다.
//
// execute_extendscript 로 실행. 결과 파일: /tmp/cut_audio.wav (Whisper 입력용).
//
// 왜 이 방식인가:
//   자막은 "지금 타임라인" 의 오디오에 맞아야 한다. AI 컷 후 사람이 더 다듬었어도
//   시퀀스를 그대로 export 하면 현재 상태가 정확히 반영된다(cuts.json 같은 낡은 데이터 의존 X).
//   MCP 의 export 도구는 2026에서 불안정하므로 exportAsMediaDirect 를 직접 호출한다.
//   영상까지 렌더할 필요 없이 오디오만 뽑으면 훨씬 빠르다.
//
// 16kHz 모노 = whisper.cpp 가 바로 받는 포맷이라 추가 변환 불필요.

var seq = app.project.activeSequence;
if (!seq)
  return __error("활성 시퀀스가 없습니다. 타임라인을 열고 다시 실행하세요.");

// 설치된 Premiere 버전의 EncoderPresets 에서 16kHz 모노 WAV 프리셋을 찾는다.
var versions = ["2027", "2026", "2025", "2024", "2023"];
var preset = null;
for (var i = 0; i < versions.length; i++) {
  var p =
    "/Applications/Adobe Premiere Pro " +
    versions[i] +
    "/Adobe Premiere Pro " +
    versions[i] +
    ".app/Contents/Settings/EncoderPresets/WAV_Mono_16bit_16kHz.epr";
  if (new File(p).exists) {
    preset = p;
    break;
  }
}
if (!preset)
  return __error(
    "WAV_Mono_16bit_16kHz.epr 프리셋을 못 찾음. 프리미어 설치 경로를 확인하세요.",
  );

var out = "/tmp/cut_audio.wav";
var r = seq.exportAsMediaDirect(out, preset, 0); // 0 = 전체 시퀀스(work area 무시)
return __result({ exportReturn: String(r), out: out, presetUsed: preset });
