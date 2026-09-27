// export_sequence_audio.jsx (Windows판) — 현재 시퀀스의 "오디오만" 16kHz 모노 WAV로 export.
//
// execute_extendscript 실행 전에 __OUT_WAV__ 를 실제 출력 경로로 치환한다.
//   예: "C:/Users/me/myproject/premiere-auto-edit/cut_audio.wav"
//
// Windows Premiere 설치 경로의 EncoderPresets 에서 16kHz 모노 WAV 프리셋을 찾는다.
// 표준 설치 기준: C:\Program Files\Adobe\Adobe Premiere Pro <버전>\Settings\EncoderPresets\
//
// 현재 타임라인을 그대로 export 하므로 사람이 다듬은 결과까지 정확히 반영된다.
// MCP export 도구는 2026에서 불안정 → exportAsMediaDirect 직접 호출.

var seq = app.project.activeSequence;
if (!seq)
  return __error("활성 시퀀스가 없습니다. 타임라인을 열고 다시 실행하세요.");

var versions = ["2027", "2026", "2025", "2024", "2023"];
var roots = [
  "C:/Program Files/Adobe/Adobe Premiere Pro VER/Settings/EncoderPresets/WAV_Mono_16bit_16kHz.epr",
  "C:/Program Files/Adobe/Adobe Premiere Pro VER/Adobe Premiere Pro VER/Settings/EncoderPresets/WAV_Mono_16bit_16kHz.epr",
];
var preset = null;
for (var vi = 0; vi < versions.length && !preset; vi++) {
  for (var ri = 0; ri < roots.length; ri++) {
    var p = roots[ri].replace(/VER/g, versions[vi]);
    if (new File(p).exists) {
      preset = p;
      break;
    }
  }
}
if (!preset)
  return __error(
    "WAV_Mono_16bit_16kHz.epr 프리셋을 못 찾음. Premiere 설치 경로를 확인하세요.",
  );

var out = "__OUT_WAV__"; // ← 실행 전 실제 경로로 치환
var r = seq.exportAsMediaDirect(out, preset, 0); // 0 = 전체 시퀀스
return __result({ exportReturn: String(r), out: out, presetUsed: preset });
