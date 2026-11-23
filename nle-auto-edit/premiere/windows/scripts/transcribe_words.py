#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transcribe_words.py — faster-whisper로 단어별 타임스탬프를 뽑아 어절 JSON을 만든다. (Windows판)

사용법:
  python transcribe_words.py [audio=<workdir>/cut_audio.wav] [--lang ko] [--model large-v3] [--device auto] [--workdir .]

출력:
  <workdir>/words.json   → [{start, end, text}, ...] (어절 단위, 정확한 시간)

왜 faster-whisper인가:
  단어별 타임스탬프가 정확하다(whisper.cpp는 세그먼트 첫 단어가 늘어나는 버그가 있어 부정확).
  GPU(CUDA) 있으면 빠름. CPU에서 large-v3는 느리니(7분 영상에 ~20분) 급하면 --model medium/small 권장.
  모델은 공용 캐시(HF cache)에 자동 다운로드/재사용.

--device (기본 auto):
  auto  CUDA로 먼저 받아쓰고, 실패하면 CPU(int8)로 다시 받아쓴다.
  cuda  CUDA만 쓴다. cpu  CPU만 쓴다.
  Windows에서 NVIDIA GPU는 있는데 CUDA 런타임(cuBLAS/cuDNN)이 없으면 모델 생성은 성공하고
  실제 추론에서 "Library cublas64_12.dll is not found"로 죽는다(2026-11-22 Windows 11 실측).
  그래서 모델 생성만이 아니라 받아쓰기까지 끝나야 그 장치를 쓴 것으로 본다.
"""

import argparse, json, os, sys

# Windows: 출력을 파이프로 읽을 때(Claude Code 셸 등) 한글이 cp949로 나가 깨지지 않게 UTF-8로 고정한다.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

DEVICES = {
    "auto": [("cuda", "float16"), ("cpu", "int8")],
    "cuda": [("cuda", "float16")],
    "cpu": [("cpu", "int8")],
}


def transcribe(audio, a):
    from faster_whisper import WhisperModel

    last = None
    for dev, ct in DEVICES[a.device]:
        try:
            model = WhisperModel(a.model, device=dev, compute_type=ct)
            segs, _info = model.transcribe(audio, language=a.lang, word_timestamps=True)
            # transcribe()는 제너레이터를 돌려준다. 실제 추론(그리고 CUDA DLL 로드 실패)은 순회할 때 일어나므로
            # 여기서 끝까지 돌려 실패를 이 try 안에서 잡는다.
            return list(segs), dev
        except Exception as e:
            last = e
            if dev == "cuda" and a.device == "auto":
                print(f"CUDA로 받아쓰기 실패 → CPU(int8)로 다시 시도: {e}", file=sys.stderr)
    sys.exit(f"받아쓰기 실패({a.device}): {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", nargs="?", default=None)
    ap.add_argument("--lang", default="ko")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--device", choices=sorted(DEVICES), default="auto")
    ap.add_argument("--workdir", default=".")
    a = ap.parse_args()
    audio = a.audio or os.path.join(a.workdir, "cut_audio.wav")
    if not os.path.isfile(audio):
        sys.exit(f"오디오 없음: {audio} (먼저 시퀀스 오디오를 export 하세요)")
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        sys.exit('faster-whisper 미설치 → python -m pip install faster-whisper "av<16"')

    segs, device = transcribe(audio, a)
    # 어절 단위로 모음 (faster-whisper word.word는 새 어절 앞에 공백이 붙음 → 서브워드 연속은 앞 어절에 합침)
    ej = []
    for s in segs:
        if not s.words:
            continue
        for w in s.words:
            raw = w.word
            if raw.startswith(" ") or not ej:
                ej.append({"start": w.start, "end": w.end, "text": raw})
            else:
                ej[-1]["text"] += raw
                ej[-1]["end"] = w.end
    out = []
    for e in ej:
        t = e["text"].strip()
        if t:
            out.append(
                {"start": round(e["start"], 3), "end": round(e["end"], 3), "text": t}
            )

    dst = os.path.join(a.workdir, "words.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"어절 {len(out)}개 -> {dst} (언어={a.lang}, 모델={a.model}, 장치={device})")


if __name__ == "__main__":
    main()
