#!/usr/bin/env python3
"""
transcribe_local.py — faster-whisper(로컬, 무료) → Scribe 호환 word-level JSON.

`npx hyperframes transcribe`는 whisper-cpp 바이너리가 PATH에 있어야 동작한다
(Windows에선 기본 미설치 → {"ok":false,"reason":"whisper_unavailable"}).
이 helper는 pip만으로 설치되는 faster-whisper로 같은 역할을 하고, 출력을
video-use helpers(pack_transcripts.py 등)가 바로 읽는 Scribe 형식
words[].{type,text,start,end,speaker_id} 로 쓴다. word-level verbatim (Hard Rule 8).

Usage:
    python transcribe_local.py footage/clip.mp4 -o footage/edit/transcripts/clip.json
    python transcribe_local.py clip.mp4 -o out.json --model large-v3 --language ko

모델은 첫 실행 시 Hugging Face에서 자동 다운로드 (large-v3-turbo ≈ 1.6GB).
메모리가 넉넉하면(여유 4GB+) --model large-v3 가 조금 더 정확.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="오디오/비디오 파일")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Scribe 호환 JSON 출력 경로")
    ap.add_argument("--model", default="large-v3-turbo", help="faster-whisper 모델 (기본 large-v3-turbo)")
    ap.add_argument("--language", default="ko", help="언어 코드 (기본 ko)")
    ap.add_argument("--compute-type", default="int8", help="CPU 기본 int8")
    args = ap.parse_args()

    if not args.input.exists():
        sys.exit(f"파일 없음: {args.input}")
    if args.output.exists():
        # Hard Rule 9 — 소스가 같으면 재전사하지 않는다
        print(f"✓ 캐시 사용 (이미 존재): {args.output}")
        return

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper 미설치 — bash scripts/setup.sh 재실행")

    model = WhisperModel(args.model, device="cpu", compute_type=args.compute_type)
    segments, info = model.transcribe(
        str(args.input),
        language=args.language,
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=False,
    )

    words: list[dict] = []
    prev_end = 0.0
    for seg in segments:
        for w in seg.words or []:
            if w.start > prev_end:
                words.append({"type": "spacing", "text": " ", "start": round(prev_end, 3),
                              "end": round(w.start, 3), "speaker_id": "S0"})
            words.append({"type": "word", "text": w.word.strip(), "start": round(w.start, 3),
                          "end": round(w.end, 3), "speaker_id": "S0",
                          "probability": round(w.probability, 3)})
            prev_end = w.end

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"language_code": args.language, "model": args.model, "words": words},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    n = sum(1 for w in words if w["type"] == "word")
    print(f"✓ {n} words → {args.output} (lang_prob={info.language_probability:.2f})")


if __name__ == "__main__":
    main()
