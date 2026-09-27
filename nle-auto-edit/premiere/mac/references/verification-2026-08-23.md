# Premiere 26.2.2 + premiere-pro-mcp 1.13.0 전수 재검증 (2026-08-23)

## 승격 (❌ → ✅) — 3개

| 항목 | 답이었던 것 |
|---|---|
| 트랜지션 | 트랙 아닌 **클립**에 `addTransition` + **한글 이름** |
| 키프레임 | 일반 영상 클립의 `비율 조정`은 렌더 반영됨 |
| MOGRT | `import_mogrt` 정상 동작, 렌더 확인 |

## 검증됨 (렌더 프레임으로 눈 확인)

| 항목 | 방법 |
|---|---|
| 컷 | CTI 이동 + `razor(timecode)` — 1→4 클립 |
| 크기·위치·회전·불투명도 | Motion/불투명도 컴포넌트 `setValue` |
| 볼륨 | 오디오 클립 볼륨.레벨 |
| 속도 | `setSpeed(2.0, tc, false, true, false)` — **5인자 필수** |
| 트림 | `clip.end = ticks` |
| 클립 이동 | **`clip.start = ticks`** (qe.move 는 거짓 성공) |
| 갭 찾기 | 클립 start/end 순회 |
| 효과 적용 | `qeClip.addVideoEffect()` + **한글 이름** |
| Lumetri 색보정 | 속성 인덱스로 채도/노출/대비 제어 |
| 자막 | SRT 임포트 → `createCaptionTrack` |
| 알파 오버레이 | `videoTracks[n].insertClip(item, ticks)` |
| 프레임 캡처 | `exportAsMediaDirect(path, PNG프리셋, 1)` |

## 여전히 안 되는 것

| 항목 | 상태 |
|---|---|
| 씬 감지 | QE 메서드 자체 없음 → ffmpeg 폴백 |
| 오디오 전환 | 등록 이름을 못 찾음 |

## 🚨 거짓 성공 목록 (true 반환하고 아무 일도 안 함)

- MCP `razor_all_tracks` / `split_clip` → 이제는 정직하게 실패 보고 (개선됨)
- `qe.move(timecode)` → `true` 반환, 클립 안 움직임
- `clip.addTransition(영문이름)` → `false` (한글이면 성공)

## 🚨 로케일 함정

전환·효과 레지스트리가 **현지화 이름**을 쓴다. 영문 이름은 오류 없이 **빈 객체**(`name=""`)를 반환하고 호출이 조용히 실패한다.

- 전환: `교차 디졸브` `검정으로 물들이기` `흰색으로 물들이기` `필름 디졸브` `페이지 넘기기`
- 효과: `Lumetri 색상` `가우시안 흐림` `흑백` `자르기`

## 환경 변화

- `execute_extendscript` 는 **기본 차단**. `PREMIERE_MCP_CAPABILITIES=inspect,edit,export,filesystem,unsafe-script` 필요
- CSInterface CEP12 패치는 **1.13.0 에서 업스트림 반영됨** → 별도 패치 불필요
