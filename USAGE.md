# 사용 방법 (편집 프로그램 없이 갈래)

이 가이드는 **편집 프로그램 없이** `ffmpeg` + `faster-whisper` + `yt-dlp` + 자동 선택 모션그래픽만으로 영상을 편집하는 방법입니다. **Windows와 macOS(Linux 포함) 모두 지원하며, 기본 비용 $0 / API 키 0개**입니다.

> Premiere Pro / CapCut / Final Cut Pro 안에서 직접 편집하려면 [nle-auto-edit/README.md](nle-auto-edit/README.md)를 참고하세요.

---

## 1. 시작하기 (사전 셋업 불필요)

별도 설치 스크립트를 미리 돌릴 필요 없이, 이 레포에서 AI 에이전트(Claude Code, Codex, Cursor, Antigravity 등)를 열고 자연어로 영상 경로와 편집 내용을 말하면 됩니다.

AI가 처음 실행 시 현재 OS를 확인해 없는 도구만 자동으로 설치합니다:

- **`ffmpeg` / `ffprobe`**: macOS `brew`, Windows `winget`(`Gyan.FFmpeg`) / `choco` / `scoop`, Linux `apt`
- **`Python 3` + `faster-whisper` (`av<16`)**: 전용 가상환경(`~/.video-edit-venv`)에 격리 설치
- **`yt-dlp`**: 레퍼런스 URL을 넘긴 경우에만 전용 가상환경에 설치
- **모션그래픽 도구**: 필요할 때만 `pillow` 또는 `Node.js` / `npx hyperframes` 점검

---

## 2. 사용 예시

### A. 기본 컷편집 + 한국어 자막

```text
/Users/me/Desktop/interview.mp4
1.5초 이상 무음 잘라주고, 한국어 1줄 자막 번인하고, 오디오 볼륨 평준화해줘.
```

Windows 경로도 그대로 가능합니다:

```text
C:\Users\me\Videos\강의원본.mp4
무음 잘라주고 세로 9:16 쇼츠로 크롭해서 자막 달아줘.
```

진행 흐름:
1. `ffprobe`로 해상도·FPS·타임코드·한글 경로 사전 점검
2. `ffmpeg silencedetect` + `faster-whisper` 단어 단위 음성인식 (`edit/words.json` 캐싱)
3. **컷 실행 전 평문 편집 계획 보고 → 확인** (필요 시 AI 추천 연출 개선안 포함)
4. 세그먼트별 추출 + 30ms 오디오 페이드 + `-c copy` concat + 자막 마지막 번인 → `edit/final.mp4`
5. `ffprobe` 메타데이터 확인 + 주요 프레임 PNG 추출 **직접 시각 검수** 후 보고

---

### B. 레퍼런스 영상 스타일 분석 & 적용 (`yt-dlp` + 프레임 분석)

유튜브·쇼츠·릴스·틱톡 URL이나 로컬 레퍼런스 영상을 함께 주면 됩니다.

```text
원본: footage/talk.mp4
레퍼런스: https://www.youtube.com/shorts/XXXXXXXXXXX
이 레퍼런스의 컷 템포, 자막 디자인, 색감 톤을 분석해서 원본에 맞게 적용해줘.
```

진행 흐름:
1. `yt-dlp`로 레퍼런스 다운로드 (로컬 파일이면 그대로 사용)
2. `ffmpeg`로 씬 전환(평균 컷 길이 ASL), 무음 기준, 라우드니스 측정
3. 일정 간격 + 씬 전환 직후 **4x4 프레임 그리드 & 대표 프레임** 추출 → AI가 직접 시각 분석해 `edit/ref_style.json` 생성
4. 원본 영상에 어울리도록 스타일만 재해석해 매핑표 제시 → 적용
5. 완성 후 **레퍼런스 대표 프레임과 결과물 프레임을 나란히 비교 검증**

---

### C. 모션그래픽 자동 생성 (3단계 자동 선택)

```text
footage/demo.mp4 편집하면서
오프닝 타이틀 카드, 화자 이름표 로어써드, 핵심 수치 강조 카드도 같이 만들어 넣어줘.
```

AI가 요청 난이도와 PC 환경을 보고 자동으로 선택합니다:
1. **1단계 (`Python Pillow/SVG + ffmpeg`)**: 텍스트 카드, 로어써드, 화살표, 간단 차트/카운터 — 추가 설치 없이 초고속
2. **2단계 (`Hyperframes`, `npx hyperframes`)**: 글래스모피즘, 키네틱 타이포, 부드러운 GSAP 모션 — 단일 HTML로 투명 배경 알파 렌더
3. **3단계 (`Remotion`)**: 복잡한 React 멀티씬·데이터 기반 풀 모션, 또는 사용자가 직접 지정한 경우

---

### D. 결과 보고 피드백으로 바로 조정하기

결과를 본 뒤 자연어로 피드백하면 AI가 되묻지 않고 파라미터를 바꿔 즉시 재실행하고 **전/후 수치 변화**를 보고합니다.

- `"너무 많이 잘렸어 / 말이 끊겨"` → 무음 기준 `-30 → -40dB`, 최소초 ↑, 패딩 `0.08 → 0.15초`
- `"덜 잘렸어 / 빈 곳이 남아"` → 무음 기준 `-30 → -25dB`, 최소초 `2.0 → 0.5초`
- `"숨소리까지 빼줘"` → `-40dB / 0.3초`
- `"자막이 너무 짧게 끊겨"` → 글자 상한·쉼 간격 확대
- `"한 줄이 너무 길어"` → 글자 상한 축소

---

## 3. 자주 묻는 질문 & 트러블슈팅

### Q. 스킬 없이 다른 AI 채팅/에이전트에 프롬프트로만 쓰고 싶다면?
[`.claude/skills/motion-pipeline/SKILL.md`](.claude/skills/motion-pipeline/SKILL.md)의 YAML 머리말(`--- ... ---`) 아래 본문을 그대로 복사해 시스템 프롬프트나 대화 첫 메시지로 붙여넣어 사용할 수 있습니다.

### Q. Windows에서 `ffmpeg` 설치 직후 인식이 안 됩니다
`winget` 설치 직후 현재 터미널의 `PATH`가 갱신되지 않을 수 있습니다. 스킬이 자동으로 `%LOCALAPPDATA%\Microsoft\WinGet\Packages`·레지스트리 `PATH`를 재조회하지만, 그래도 안 잡히면 터미널을 한 번 닫고 다시 열어 주세요.

### Q. 첫 Whisper 실행이 오래 걸립니다
`faster-whisper` 모델(`medium` 약 1.5GB, `large-v3` 약 3GB)을 처음 한 번 다운로드합니다. 한 번 받으면 캐시되어 재사용되며, NVIDIA GPU(CUDA)가 있으면 자동으로 GPU 가속됩니다. CPU에서 빠르게 처리하고 싶으면 `"whisper 모델은 medium으로 써줘"`라고 말하면 됩니다.

### Q. 한글 자막이 네모(□□□)로 깨집니다
시스템에 설치된 한글 폰트가 지정되지 않을 때 발생합니다. 스킬은 OS별 기본 한글 폰트(Windows `Malgun Gothic`, macOS `AppleSDGothicNeo`, Linux `Noto Sans CJK KR`)를 자동 선택하고, 완료 전 프레임 PNG를 직접 열어 깨짐 여부를 시각 검증합니다.

### Q. DJI / GoPro 영상이나 한글 파일명에서 싱크·필터 오류가 납니다
스킬의 Step 1 사전 점검이 `00:00:00:00`이 아닌 타임코드와 한글/특수문자 경로를 감지해, OS 임시 폴더에 무손실(`-c copy`) 사본을 만들어 우회합니다.

### Q. 결과물을 Premiere Pro / Final Cut Pro 타임라인(XML)으로도 받고 싶다면?
기본 산출물은 `<영상 폴더>/edit/final.mp4`이지만, 원할 경우 레포에 남아 있는 기존 헬퍼(`scripts/export_nle_files.sh`, `.claude/skills/motion-pipeline/helpers/edl_to_fcpxml.py`, `edl_to_fcp7_xml.py`)를 통해 `edl.json`에서 FCPXML/Premiere XML을 생성할 수 있습니다.
