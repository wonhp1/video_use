#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transcribe_words.py — faster-whisper로 단어별 타임스탬프를 뽑아 어절 JSON을 만든다. (크로스플랫폼)

사용법:
  python transcribe_words.py [audio=<workdir>/cut_audio.wav] [--lang ko] [--model large-v3] [--workdir .]

출력:
  <workdir>/words.json   → [{start, end, text}, ...] (어절 단위, 정확한 시간)

왜 faster-whisper인가:
  단어별 타임스탬프가 정확하다(whisper.cpp는 세그먼트 첫 단어가 늘어나는 버그가 있어 부정확).
  GPU(CUDA) 있으면 빠름. Mac CPU는 large-v3가 느리니(7분 영상에 ~20분) 급하면 --model medium 권장.
  모델은 공용 캐시(HF cache)에 자동 다운로드/재사용.
"""

import argparse, json, os, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", nargs="?", default=None)
    ap.add_argument("--lang", default="ko")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--workdir", default=".")
    a = ap.parse_args()
    audio = a.audio or os.path.join(a.workdir, "cut_audio.wav")
    if not os.path.isfile(audio):
        sys.exit(f"오디오 없음: {audio} (먼저 시퀀스 오디오를 export 하세요)")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper 미설치 → pip install faster-whisper")

    model = None
    for dev, ct in [("cuda", "float16"), ("cpu", "int8")]:
        try:
            model = WhisperModel(a.model, device=dev, compute_type=ct)
            break
        except Exception:
            continue
    if model is None:
        sys.exit("WhisperModel 로드 실패")

    segs, info = model.transcribe(audio, language=a.lang, word_timestamps=True)
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
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"어절 {len(out)}개 -> {dst} (언어={a.lang}, 모델={a.model})")


if __name__ == "__main__":
    main()
