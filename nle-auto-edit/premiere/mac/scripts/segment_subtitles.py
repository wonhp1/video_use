#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
segment_subtitles.py — 어절 JSON(words.json)을 "말할 때만 뜨는" 1줄 자막 SRT로 분할한다. (크로스플랫폼)

사용법:
  python segment_subtitles.py [--workdir .] [--soft 16] [--gap 0.4]

입력:  <workdir>/words.json   ([{start,end,text}, ...] 어절 + 정확한 시간)
출력:  <workdir>/cut_audio.srt

원칙:
  - **쉼(pause) 기반**: 단어 사이 간격이 --gap(기본 0.4초) 이상이면 자막을 끊고,
    그 자막의 끝을 "마지막 단어 끝 + 여운(0.2초)"으로 닫는다 → 쉼 구간엔 자막이 사라짐(빈 화면).
    말이 이어지는 한 덩어리 안에서는 자막이 연속(다음 자막에 붙음).
  - **1줄 고정**, 길이는 내용 따라 적응. --soft는 화면 넘침 방지 소프트 상한(하드 상한=soft+8).
  - glue: 의존명사("수","것")·"하는/할/있는" 등 앞에서 안 끊음. look-ahead로 상한 내 최적 지점 선택.
  - **최소 표시 0.5초** 보장(너무 짧게 깜빡이지 않게): 같은 덩어리 연속이면 앞 자막에 병합, 고립이면 끝을 연장.
"""

import argparse, json, os, sys

NO_START = (
    "수",
    "것",
    "거",
    "게",
    "때",
    "줄",
    "등",
    "들",
    "점",
    "중",
    "후",
    "전",
    "데",
    "만큼",
    "뿐",
    "채",
    "척",
    "분",
    "개",
    "명",
    "번",
    "건",
    "걸",
    "하는",
    "한",
    "할",
    "해서",
    "하고",
    "하던",
    "하지",
    "했",
    "있는",
    "있다",
    "있고",
    "있어",
    "없는",
    "없다",
    "같은",
    "같이",
    "위해",
    "통해",
    "대해",
    "대한",
    "위한",
    "수도",
    "수가",
    "코딩",
)
NO_END = (
    "그",
    "이",
    "저",
    "한",
    "두",
    "세",
    "네",
    "매우",
    "아주",
    "정말",
    "너무",
    "좀",
    "막",
    "딱",
    "그냥",
    "더",
    "덜",
    "꼭",
    "잘",
    "바이브",
)
CONN = (
    "고",
    "며",
    "면",
    "서",
    "데",
    "만",
    "나",
    "까",
    "요",
    "죠",
    "는데",
    "지만",
    "어서",
    "아서",
    "거나",
    "니까",
    "는데요",
)


def conn(w):
    if w and w[-1] in ".?!,":
        return 3
    return 2 if any(w.endswith(c) for c in CONN) else 0


def fmt(t):
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=".")
    ap.add_argument("--soft", type=float, default=16)  # 1줄 소프트 상한(자)
    ap.add_argument("--gap", type=float, default=0.4)  # 이 이상 쉬면 분리 + 화면 비움
    a = ap.parse_args()
    SOFT = a.soft
    GAP = a.gap
    HARD = SOFT + 8
    LEADOUT = 0.2
    MIN = 0.5
    src = os.path.join(a.workdir, "words.json")
    if not os.path.isfile(src):
        sys.exit(f"words.json 없음: {src} (먼저 transcribe_words.py)")
    W = json.load(open(src, encoding="utf-8"))
    if not W:
        sys.exit("words.json 비어 있음")

    def gap_after(i):
        return (W[i + 1]["start"] - W[i]["end"]) if i + 1 < len(W) else 99

    def valid(i):
        return (W[i]["text"] not in NO_END) and (
            i + 1 >= len(W) or W[i + 1]["text"] not in NO_START
        )

    lines = []
    i = 0
    while i < len(W):
        j = i
        length = 0
        best = None
        bestsc = -1e9
        while j < len(W):
            length += len(W[j]["text"]) + (1 if j > i else 0)
            if gap_after(j) >= GAP and j >= i:  # 쉼 → 강제 분리(글자수 무관)
                best = j
                break
            if j > i and valid(j) and length <= HARD:
                sc = conn(W[j]["text"]) * 3 - max(0, length - SOFT) * 1.5
                if sc > bestsc:
                    bestsc = sc
                    best = j
            if length >= HARD:
                break
            j += 1
        if best is None:
            best = min(j, len(W) - 1)
        s = W[i]["start"]
        ew = W[best]["end"]
        g = gap_after(best)
        if g >= GAP or best + 1 >= len(W):  # 뒤에 쉼 → 끝을 말끝+여운으로(화면 비움)
            e = max(ew + LEADOUT, s + MIN)
            if best + 1 < len(W):
                e = min(e, W[best + 1]["start"] - 0.03)
            e = max(e, ew + 0.05)
        else:  # 같은 덩어리 연속 → 다음 자막에 붙임
            e = W[best + 1]["start"]
        lines.append(
            [
                round(s, 3),
                round(e, 3),
                " ".join(W[k]["text"] for k in range(i, best + 1)),
            ]
        )
        i = best + 1

    # 너무 짧은 자막 보정(깜빡임 방지)
    out = []
    for ln in lines:
        if (
            out
            and (ln[1] - ln[0]) < MIN
            and abs(out[-1][1] - ln[0]) < 0.05
            and len(out[-1][2]) + 1 + len(ln[2]) <= HARD + 4
        ):
            out[-1][1] = ln[1]
            out[-1][2] = out[-1][2] + " " + ln[2]  # 같은 덩어리 연속 → 앞에 병합
        else:
            out.append(ln)
    lines = out
    for k in range(len(lines)):
        if lines[k][1] - lines[k][0] < MIN:
            ns = lines[k + 1][0] if k + 1 < len(lines) else lines[k][1] + MIN
            lines[k][1] = min(lines[k][0] + MIN, max(lines[k][1], ns - 0.03))
            if lines[k][1] <= lines[k][0]:
                lines[k][1] = lines[k][0] + 0.4

    dst = os.path.join(a.workdir, "cut_audio.srt")
    with open(dst, "w", encoding="utf-8") as f:
        for k, (s, e, t) in enumerate(lines, 1):
            f.write(f"{k}\n{fmt(s)} --> {fmt(e)}\n{t}\n\n")
    L = [len(t) for _, _, t in lines]
    D = [e - s for s, e, t in lines]
    print(
        f"자막 {len(lines)}개 -> {dst} (글자 평균 {sum(L)//len(L)}/최대 {max(L)}, 표시 평균 {sum(D)/len(D):.1f}초)"
    )


if __name__ == "__main__":
    main()
