#!/usr/bin/env bash
#
# detect_silence.sh — 영상에서 무음 구간을 감지해 컷 목록(JSON)을 만든다.
#
# 사용법:
#   bash detect_silence.sh <영상경로> [noise_dB=-30] [min_sec=2.0] [pad=0.08]
#
# 출력:
#   /tmp/premiere_cuts.json  → 제거할 컷 구간 배열 [[start,end],...] (초, 패딩 적용)
#   stdout 에 요약(감지 개수, 총 제거시간, 예상 결과 길이)
#
# 파라미터 의미:
#   noise_dB : 이 값 이하를 "무음"으로 판단 (-20=공격적, -30=중간, -40=보수적)
#   min_sec  : 이 길이 이상 조용해야 컷 대상
#   pad      : 컷 양끝에 남길 여유(초). 말의 시작/끝이 잘리지 않게 함.
#
set -euo pipefail

VIDEO="${1:?영상 경로를 넘겨주세요}"
NOISE_DB="${2:--30}"
MIN_SEC="${3:-2.0}"
PAD="${4:-0.08}"
OUT="/tmp/premiere_cuts.json"
RAW="/tmp/premiere_silence_raw.txt"

[ -f "$VIDEO" ] || { echo "파일 없음: $VIDEO" >&2; exit 1; }

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO")

ffmpeg -nostats -hide_banner -i "$VIDEO" \
  -af "silencedetect=noise=${NOISE_DB}dB:d=${MIN_SEC}" -f null - 2>&1 \
  | grep -E "silence_(start|end)" > "$RAW" || true

python3 - "$RAW" "$OUT" "$PAD" "$DUR" "$NOISE_DB" "$MIN_SEC" <<'PY'
import re, json, sys
raw_path, out_path, pad, dur, ndb, msec = sys.argv[1:7]
pad = float(pad); dur = float(dur)
raw = open(raw_path).read()
starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", raw)]
ends   = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", raw)]
segs = list(zip(starts, ends))
cuts = []
for s, e in segs:
    cs, ce = s + pad, e - pad
    if ce - cs >= 0.3:
        cuts.append([round(cs, 3), round(ce, 3)])
json.dump(cuts, open(out_path, "w"))
removed = sum(b - a for a, b in cuts)
print(f"기준: {ndb}dB 이하, {msec}초 이상 무음")
print(f"감지: {len(segs)}개  →  컷 구간(패딩 후): {len(cuts)}개")
print(f"제거 예정: {removed/60:.1f}분  /  원본 {dur/60:.1f}분  →  예상 결과 {(dur-removed)/60:.1f}분")
print(f"컷 목록 저장: {out_path}")
PY
