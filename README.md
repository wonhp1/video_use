# 비디오유즈 https://github.com/wonhp1/video_use

**기본은 무료 / 로컬 / API 키 0개.** Windows와 macOS(Linux 포함) 모두에서 편집 프로그램 없이 또는 기존 NLE(Premiere / CapCut / Final Cut) 안에서 AI로 영상을 편집합니다.

> Repo: https://github.com/wonhp1/video_use
> License: [MIT](LICENSE)

## 두 갈래 — 편집 프로그램을 쓰시나요?

| 선택                                                     | 이런 분께                                          | 시작                                                              |
| -------------------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------- |
| **편집 프로그램 없이** (기본, 이 문서)                   | 프로그램·별도 셋업 없이 완성 `final.mp4`를 받고 싶다 | **별도 설치 없이 바로 요청** (누락된 도구는 AI가 자동 설치)       |
| **편집 프로그램 사용** → [nle-auto-edit](nle-auto-edit/) | Premiere / CapCut / Final Cut 안에서 편집하고 싶다 | `bash nle-auto-edit/install.sh <프로그램>` (Windows: `install.ps1`) |

Claude Code(또는 `AGENTS.md`를 읽는 에이전트)는 **따로 묻지 않습니다.** "이 영상 편집해줘"처럼 말하면 편집 프로그램 없이 처리하고, "프리미어로 무음 잘라줘", "캡컷 자막 달아줘"처럼 **프로그램 이름을 말할 때만** 그 프로그램을 씁니다.

---

## 편집 프로그램 없이 — 핵심 기능

[`.claude/skills/motion-pipeline/SKILL.md`](.claude/skills/motion-pipeline/SKILL.md) 하나로 별도 외부 스킬·수동 셋업 없이 아래 전체를 처리합니다.

| 영역                       | 동작 방식                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------- |
| **의존성 자동 설치**       | Windows(`winget`/venv) · macOS(`brew`/venv) · Linux에서 `ffmpeg`, `faster-whisper`, `yt-dlp`, 모션 도구를 자동 점검·설치 |
| **무음 컷 & 음성인식**     | `ffmpeg silencedetect` + `faster-whisper`(`word_timestamps=True`, CUDA/CPU 자동 폴백) → 단어 경계 스냅 + 30ms 오디오 페이드 |
| **한국어 쉼 기반 자막**    | 말할 때만 뜨는 1줄 자막 기본값(의존명사·관형어 분리 금지), 영상·레퍼런스에 따라 자유 조정   |
| **레퍼런스 프레임 분석**   | 유튜브·쇼츠·릴스 URL을 `yt-dlp`로 다운로드 → `ffmpeg` 4x4 프레임 그리드 & 씬 전환 분석 → 스타일만 원본에 재해석 적용 |
| **모션그래픽 3단계 선택**  | 난이도·환경에 따라 **① Python(Pillow/SVG)+ffmpeg → ② Hyperframes → ③ Remotion** 자동 선택   |
| **AI 자율 판단 & 시각 검증** | 6개 Hard Rules 외에는 AI가 더 나은 연출을 스스로 판단·제안하고, 완성 후 프레임 PNG 추출로 직접 눈 검증 |

---

## 빠른 시작 (편집 프로그램 없이)

별도의 `setup.sh` 실행 없이 이 레포를 열고(또는 `.claude/skills/motion-pipeline/SKILL.md`를 사용해) 바로 자연어로 요청하면 됩니다.

- **기본 컷 + 자막**: `"C:\videos\talk.mp4 무음 잘라주고 한국어 자막 달아줘."`
- **레퍼런스 스타일 적용**: `"footage/raw.mp4를 https://youtube.com/shorts/... 이 레퍼런스 컷 템포랑 자막·색감 스타일로 편집해줘."`
- **모션그래픽 포함**: `"인터뷰 영상 편집하고 핵심 숫자랑 이름표 로어써드 모션그래픽도 넣어줘."`
- **즉시 피드백 조정**: `"말이 좀 끊기는 것 같아"`, `"자막 한 줄이 너무 길어"` → AI가 파라미터를 바로 조정해 재실행하고 전/후 수치 보고

자세한 사용 예시와 트러블슈팅은 [USAGE.md](USAGE.md)를 참고하세요.

---

## 사용 도구 (전부 무료 / 로컬)

| 도구                                                         | 역할                                                          | 비용 |
| ------------------------------------------------------------ | ------------------------------------------------------------- | ---- |
| **ffmpeg / ffprobe**                                         | 소스 점검, 무음 감지, 세그먼트 컷·합성, 색감, 자막 번인, 프레임 추출 | $0   |
| **faster-whisper**                                           | 단어 단위 정확한 타임스탬프 음성인식 (CUDA 자동 가속 / CPU 폴백) | $0   |
| **yt-dlp**                                                   | 레퍼런스 영상 URL 다운로드 (레퍼런스 제공 시에만 사용)        | $0   |
| **Pillow / [Hyperframes](https://github.com/heygen-com/hyperframes) / Remotion** | 모션그래픽 생성 (난이도·환경에 따라 3단계 자동 선택)          | $0   |

---

## AI 에이전트 호환성

| 에이전트                       | 자동 트리거 (자연어 요청)                                            | 수동 프롬프트 복붙 |
| ------------------------------ | -------------------------------------------------------------------- | ------------------ |
| **Claude Code**                | ✅ `CLAUDE.md` + `.claude/skills/motion-pipeline/SKILL.md` 자동 인식 | ✅                 |
| **Codex / Cursor / Antigravity** | ✅ `AGENTS.md` (= `CLAUDE.md` 심볼릭) 자동 인식                      | ✅                 |
| **그 외 CLI/코딩 에이전트**    | `.claude/skills/motion-pipeline/SKILL.md` 내용을 프롬프트로 붙여넣기 | ✅                 |

---

## 디렉토리

```
.
├── .claude/skills/
│   └── motion-pipeline/
│       ├── SKILL.md            ← 편집 프로그램 없이 범용 영상편집 스킬 (Windows/macOS 호환)
│       ├── helpers/            ← (선택/호환) NLE XML 변환 등 기존 보조 스크립트
│       └── examples/edl.example.json
├── nle-auto-edit/              ← 편집 프로그램 사용 갈래 (Premiere / CapCut / Final Cut 직접 조작)
├── footage/                    ← 영상 배치용 기본 폴더 (어느 절대경로든 작업 가능)
├── hyperframes/                ← (선택) Hyperframes 컴포지션 작업 폴더
├── scripts/                    ← (선택/호환) NLE XML export 등 기존 유틸리티
├── USAGE.md                    ← 상세 사용법, 레퍼런스/모션그래픽 예시, FAQ, 트러블슈팅
├── CLAUDE.md                   ← Claude Code 진입 컨텍스트
├── AGENTS.md → CLAUDE.md       ← Codex / Cursor / Antigravity 등 호환 심볼릭
└── README.md
```

---

## 라이선스 / 출처

이 repo: [MIT](LICENSE) — 자유롭게 사용/수정/재배포 가능(라이선스 문구만 보존).

주요 오픈소스 도구 및 영감:

- [ffmpeg](https://ffmpeg.org/) — LGPL/GPL
- [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) — MIT
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — Unlicense
- [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) — Apache 2.0
- [browser-use/video-use](https://github.com/browser-use/video-use) — Hard Rules 아키텍처 영감
