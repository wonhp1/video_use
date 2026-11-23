#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plan_cut_ranges.py — 무음 컷 목록(원본 초)을 premiere-pro MCP 도구 입력(타임라인 초)으로 바꾼다. (크로스플랫폼)

사용법:
  python plan_cut_ranges.py <cuts.json> --frame-ticks <N> [--clip-start 0] [--clip-in 0] [--clip-end <초>]
  python plan_cut_ranges.py <cuts.json> --fps 30000/1001 ...

  cuts.json      detect_silence 가 만든 [[start,end],...] (원본 파일 기준 초)
  --frame-ticks  get_active_sequence 결과의 syncCheck.frameTicks (예: 29.97 = 8475667200)
  --fps          frame-ticks 대신 분수로 줄 때 (예: 24000/1001)
  --clip-start   V1 클립의 타임라인 시작(초). get_active_sequence 의 clips[0].start
  --clip-in      V1 클립의 원본 시작점(초). clips[0].inPoint
  --clip-end     V1 클립의 타임라인 끝(초). 이 밖의 컷은 버리고 걸치는 컷은 자른다.
  --chunk        ripple_remove_timeline_ranges 한 번에 넣을 구간 수(도구 상한 50)

출력(stdout, JSON):
  ranges        전체 컷 구간 [{start,end}] — 타임라인 초, 프레임 경계로 반올림
  chunks        ripple_remove_timeline_ranges 에 넣을 묶음. **배열 순서대로(뒤쪽 묶음부터)** 적용한다.
                뒤쪽을 먼저 지워야 앞쪽 구간의 타임라인 시간이 그대로 유지된다.
  razor_times   대체 경로(razor_all_tracks + ripple_delete)용 자를 시각. 큰 시각부터.
  removed_*     지울 길이(초·프레임)

왜 필요한가:
  - 도구는 타임라인 초를 받는다. 컷 목록은 원본 초라서 클립 위치(start/inPoint)만큼 옮겨야 한다.
  - 경계를 미리 프레임에 맞춰 두면 dry run 의 adjustments 와 결과 readback 을 프레임 단위로 대조할 수 있다.
    (1.31.0 실측: 29.97/23.976/30fps 모두 도구가 가장 가까운 프레임으로 반올림했고, 이 스크립트 값과 같았다.)
"""

import argparse, json, sys
from fractions import Fraction

TICKS_PER_SECOND = 254016000000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cuts")
    ap.add_argument("--frame-ticks", type=int)
    ap.add_argument("--fps")
    ap.add_argument("--clip-start", default="0")
    ap.add_argument("--clip-in", default="0")
    ap.add_argument("--clip-end")
    ap.add_argument("--chunk", type=int, default=50)
    a = ap.parse_args()

    if a.frame_ticks:
        fps = Fraction(TICKS_PER_SECOND, a.frame_ticks)
    elif a.fps:
        fps = Fraction(a.fps)
    else:
        sys.exit("--frame-ticks 또는 --fps 가 필요합니다 (get_active_sequence 의 syncCheck.frameTicks)")
    chunk = max(1, min(50, a.chunk))

    cuts = json.load(open(a.cuts, encoding="utf-8"))
    start, cin = Fraction(a.clip_start), Fraction(a.clip_in)
    end = Fraction(a.clip_end) if a.clip_end else None

    frames = []  # 타임라인 프레임 [fs, fe)
    for s, e in cuts:
        ts = start + (Fraction(str(s)) - cin)
        te = start + (Fraction(str(e)) - cin)
        if end is not None:
            if te <= start or ts >= end:
                continue
            ts, te = max(ts, start), min(te, end)
        fs, fe = round(ts * fps), round(te * fps)
        if fe > fs:
            frames.append((fs, fe))
    frames.sort()
    merged = []
    for fs, fe in frames:  # 겹치거나 맞닿은 구간은 합친다(도구는 겹치는 구간을 거부)
        if merged and fs <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], fe))
        else:
            merged.append((fs, fe))

    sec = lambda f: round(float(Fraction(f) / fps), 9)
    ranges = [{"start": sec(fs), "end": sec(fe)} for fs, fe in merged]
    chunks = [ranges[i:i + chunk] for i in range(0, len(ranges), chunk)][::-1]
    razor = sorted({sec(f) for pair in merged for f in pair}, reverse=True)
    removed_frames = sum(fe - fs for fs, fe in merged)
    out = {
        "fps": float(fps),
        "fpsFraction": f"{fps.numerator}/{fps.denominator}",
        "cuts": len(cuts),
        "ranges": ranges,
        "chunks": chunks,
        "razor_times": razor,
        "removed_frames": removed_frames,
        "removed_seconds": sec(removed_frames),
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(
        f"컷 {len(cuts)}개 → 타임라인 구간 {len(ranges)}개, 묶음 {len(chunks)}개, 지울 길이 {out['removed_seconds']:.3f}초 ({removed_frames}프레임)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
