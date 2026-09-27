# premiere-auto-edit — Claude로 Premiere Pro 무음 컷 + 자막 자동화 (스킬)

Claude(Claude Code/Desktop)가 `premiere-pro` MCP로 **Adobe Premiere Pro를 직접 조작**해서:

- 🔇 영상의 **무음 구간 자동 컷편집** (dB·최소 길이 지정 가능)
- 💬 **자막 자동 생성** (시퀀스 오디오 → Whisper 받아쓰기 → SRT → import)

을 수행하는 Claude **스킬**입니다. 편집이 실제 프리미어 타임라인에 반영됩니다.

## 두 가지 버전

| 폴더                   | 대상    | 상태                                              | 구현                  |
| ---------------------- | ------- | ------------------------------------------------- | --------------------- |
| [`mac/`](mac/)         | macOS   | ✅ **검증됨** (Premiere 2025/2026, Apple Silicon) | bash + ExtendScript   |
| [`windows/`](windows/) | Windows | ⚠️ **미검증** (macOS본 기반 크로스플랫폼 설계)    | Python + ExtendScript |

> Windows판은 실제 Windows에서 아직 검증되지 않았습니다. 동작 보고/PR 환영합니다.

## 설치

자기 OS 폴더(`mac/` 또는 `windows/`)를 Claude 스킬 폴더에 복사하세요:

- macOS: `~/.claude/skills/premiere-auto-edit/`
- Windows: `%USERPROFILE%\.claude\skills\premiere-auto-edit\`

```bash
# 예 (macOS)
cp -R mac "$HOME/.claude/skills/premiere-auto-edit"
```

그다음 Claude에게 "이 영상 무음 -30dB로 잘라줘" / "자막 달아줘" 라고 하면 스킬이 자동 발동합니다.

## 사전 조건 (공통)

1. **premiere-pro MCP 연결 + CSInterface.js 패치** — 가장 중요. 설치 키트는 이 레포의 [`../mcp-setup/`](../mcp-setup/) 참고.
   (Premiere 2025/2026의 CEP 12 evalScript 버그를 고쳐야 모든 게 동작함. Windows 경로는 windows/references 참고.)
2. **의존성** (Python3 필요)
   - 자막: `pip install faster-whisper` (모델 자동 다운로드; large-v3는 Mac CPU 느림→`--model medium`, Windows GPU 빠름)
   - 컷: `ffmpeg` (macOS `brew install ffmpeg` / Windows `pip install imageio-ffmpeg`)

## 동작 원리

```
ffmpeg/Whisper = 귀(무음·음성 인식)   →   Claude = 두뇌+손(판단·명령)   →   Premiere = 작업대
```

Claude는 영상을 직접 듣지 못하므로, ffmpeg(무음 타임스탬프)·Whisper(받아쓰기)로 정보를 뽑은 뒤
`execute_extendscript`로 프리미어를 직접 편집합니다. (MCP 기본 편집 도구는 2026에서 버그라 우회.)

## 핵심 기술 메모

- **프레임 정확 컷**(비표준 fps): `setPlayerPosition(frameTicks)` → `CTI.timecode` → `razor(tc)`, ripple는 `qeItem.remove(true,true)`.
- **오디오 export**: `exportAsMediaDirect(out, WAV_Mono_16bit_16kHz.epr, 0)` — 현재 타임라인 그대로(사람이 다듬어도 정확).
- **자막 한계**: 캡션 트랙은 스크립트로 못 올림(2026 API 미노출) → SRT import 후 수동 드래그 1회.

자세한 내용은 각 버전의 `references/` 참고.

## 라이선스

MIT
