#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
detect_silence.py — 영상에서 무음 구간을 감지해 컷 목록(cuts.json)을 만든다. (크로스플랫폼)

사용법:
  python detect_silence.py <영상경로> [--noise -30] [--min-sec 2.0] [--pad 0.08] [--workdir .]

출력:
  <workdir>/cuts.json   → 제거할 컷 구간 [[start,end],...] (초, 패딩 적용)
  콘솔에 요약

ffmpeg 탐색 순서: PATH 의 ffmpeg → pip 패키지(imageio-ffmpeg) → 없으면 안내.
모든 산출물은 --workdir(기본: 현재 폴더 = 세션 프로젝트 폴더)에 저장한다.
"""

import argparse, json, os, re, shutil, subprocess, sys


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit(
            "ffmpeg 를 찾을 수 없습니다. `pip install imageio-ffmpeg` 하거나 ffmpeg 를 설치하세요."
        )


def find_ffprobe():
    return shutil.which("ffprobe")  # 없으면 None → duration 추정 생략


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--noise", default="-30")  # dB 임계값
    ap.add_argument("--min-sec", default="2.0")  # 최소 무음 길이(초)
    ap.add_argument("--pad", type=float, default=0.08)  # 컷 양끝 여유(초)
    ap.add_argument("--workdir", default=".")
    a = ap.parse_args()

    if not os.path.isfile(a.video):
        sys.exit(f"파일 없음: {a.video}")
    os.makedirs(a.workdir, exist_ok=True)
    ff = find_ffmpeg()

    # 총 길이(있으면)
    dur = None
    fp = find_ffprobe()
    if fp:
        try:
            dur = float(
                subprocess.run(
                    [
                        fp,
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "csv=p=0",
                        a.video,
                    ],
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            )
        except Exception:
            dur = None

    # silencedetect
    proc = subprocess.run(
        [
            ff,
            "-nostats",
            "-hide_banner",
            "-i",
            a.video,
            "-af",
            f"silencedetect=noise={a.noise}dB:d={a.min_sec}",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    log = proc.stderr
    starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", log)]
    segs = list(zip(starts, ends))

    cuts = []
    for s, e in segs:
        cs, ce = s + a.pad, e - a.pad
        if ce - cs >= 0.3:
            cuts.append([round(cs, 3), round(ce, 3)])

    out = os.path.join(a.workdir, "cuts.json")
    with open(out, "w") as f:
        json.dump(cuts, f)

    removed = sum(b - a_ for a_, b in cuts)
    print(f"기준: {a.noise}dB 이하, {a.min_sec}초 이상 무음")
    print(f"감지: {len(segs)}개  →  컷 구간(패딩 후): {len(cuts)}개")
    if dur:
        print(
            f"제거 예정: {removed/60:.1f}분 / 원본 {dur/60:.1f}분 → 예상 결과 {(dur-removed)/60:.1f}분"
        )
    else:
        print(f"제거 예정: {removed/60:.1f}분")
    print(f"컷 목록 저장: {out}")


if __name__ == "__main__":
    main()
