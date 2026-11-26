# nle-auto-edit — 편집 프로그램 자동화

> [video_use](../README.md) 저장소의 한 갈래입니다. 편집 프로그램 **없이** mp4를 바로 만들려면 저장소 루트의 motion-pipeline을 쓰세요.

Claude가 **영상 편집 프로그램을 직접 조작해** 자동 편집하는 스킬 모음입니다.
무음 구간 컷편집 · 자막 생성 · 모션그래픽 · 전환 · 배경음악을 사람 손 없이 처리합니다.

**프로그램 이름을 말할 때만 동작합니다.** "프리미어 무음 잘라줘", "캡컷 자막 달아줘", "파이널컷으로 컷편집해줘"처럼요.
이름 없이 "무음 잘라줘", "영상 편집해줘"라고 하면 이 스킬들은 끼어들지 않고, 편집 프로그램 없이 처리합니다.

프로그램마다 **연결 방식만 다르고** 분석·검증 절차는 공통이라,
`core` 뼈대 하나에 프로그램별 **어댑터**를 붙이는 구조로 되어 있습니다.
각 스킬의 절차와 레시피는 **안전장치만 고정한 출발점**이며, 더 나은 최신 API·MCP 도구·편집 기법·레퍼런스 분석·3단계 모션그래픽이 있으면 AI가 구식 절차에 얽매이지 않고 스스로 판단해 적용합니다.

```
core/          공통 뼈대 — 프로그램 판별, 무음 감지, 받아쓰기, 자막 분할, 검증 규칙
├ premiere/    Adobe Premiere Pro   (premiere-pro MCP 기본 도구 — 실시간 반영)
├ capcut/      CapCut               (draft JSON 편집 — 앱 종료 후 반영)
└ finalcut/    Final Cut Pro        (FCPXML 생성 → 임포트)
```

## 지원 현황

| | Premiere Pro | CapCut | Final Cut Pro |
|---|---|---|---|
| 연결 방식 | premiere-pro MCP 기본 도구 | draft JSON 파일 편집 | FCPXML 임포트 |
| 반영 시점 | **실시간** | 앱 종료 후 | 임포트 시 |
| 사용자 개입 | 없음 | ⌘Q 종료·재실행 | 보관함 선택 클릭 |
| 무음 컷편집 | ✅ | ✅ | ✅ |
| 자막 | ✅ 기본 스타일 | ✅ 스타일·위치 | ✅ 스타일·위치 |
| 모션그래픽 오버레이 | — | ✅ | ✅ |
| 전환 | — | ✅ 1,137종 | ✅ |
| 속도 변경 | — | ✅ | ✅ |
| 키프레임 | — | ✅ | ✅ |
| 배경음악 | — | ✅ | ✅ |
| 필터·효과 | — | ✅ 393종 | ⬜ |
| 검증 항목 | ✅ 무음 컷·오디오 export·자막 (macOS·Windows 11) | ✅18 / ⬜1 | ✅10 |

모든 ✅는 **실제로 실행해 눈으로 확인한 것**입니다. 추정은 넣지 않았습니다.
프리미어의 `—`는 스킬에 정해진 절차가 없다는 뜻입니다. 요청하면 Claude가 premiere-pro MCP 기본 도구
(1.31.0 기준 451개)로 직접 처리하지만, 이 저장소에서 검증하지는 않았습니다.

## 설치

저장소를 clone 한 뒤 이 폴더에서 실행하세요.

```bash
git clone https://github.com/wonhp1/video_use
cd video_use/nle-auto-edit
./install.sh                 # 전체 (코어 + 어댑터 3개)
./install.sh capcut          # 필요한 것만 골라도 됩니다 (premiere / capcut / finalcut)
```

```powershell
# Windows (Premiere만 지원)
powershell -ExecutionPolicy Bypass -File install.ps1
```

`~/.claude/skills/` 에 `ai-video-edit`(코어)와 어댑터를 설치하고, 아래 도구가 없으면 설치합니다.
여기까지는 **어느 프로그램을 쓰든 공통**입니다. 이후는 프로그램별로 다릅니다.

> ⚠️ `install.ps1`은 아직 Windows에서 실행해 보지 않았습니다. 안의 설치 명령은 원본 레포가 Windows 11에서 검증한 것입니다.

### 설치하는 도구

| | 용도 | 설치 방법 (macOS) |
|---|---|---|
| Node 22 이상 | premiere-pro MCP, 셋업 스크립트, `npx hyperframes` | 없으면 `brew install node` (22 미만이면 안내만) |
| `ffmpeg` / `ffprobe` | 무음 감지, 미디어 정보 | 없으면 `brew install ffmpeg` |
| `faster-whisper` + `av<16` | 단어 단위 받아쓰기 | 가상환경 `~/.local/share/nle-auto-edit/venv` 에 설치 (`uv` 가 있으면 uv, 없으면 `python3 -m venv`) |
| `hyperframes` | 모션그래픽 렌더 | npx 캐시에 미리 받기 |
| `premiere-pro-mcp` + 커넥터(CEP) | Premiere 조작 | `premiere` 대상이고 Premiere가 설치돼 있을 때만. 이미 있으면 건드리지 않음 |

> faster-whisper 1.2.1 은 PyAV 16 이상에서 실패해서 `av<16` 을 같이 설치합니다.
> 가상환경을 따로 두는 이유: macOS 기본 python3 나 anaconda 에는 faster-whisper 가 없고, Homebrew python 은 `pip install` 을 막습니다.
> 받아쓰기 모델은 처음 자막을 만들 때 내려받습니다 (medium 약 1.5GB).

---

## 🎬 Premiere Pro 시작하기

원본: [wonhp1/claude-premiere-auto-edit](https://github.com/wonhp1/claude-premiere-auto-edit) (premiere-pro-mcp 1.31.0, Premiere Pro 2027에서 검증)

**1) 설치** — `./install.sh premiere` (Windows는 `install.ps1`)

스킬 `premiere-auto-edit`·`premiere-mcp-setup`과 도구, `premiere-pro-mcp`, Premiere 커넥터(CEP)까지 설치합니다.

**2) Claude 재시작** (완전 종료 후 다시 실행)

**3) 연결** — Premiere 작업을 할 폴더에서 Claude 에게 `"프리미어 연결해줘"`

`premiere-mcp-setup` 스킬이 이어서 진행합니다:

- 원본 최신 버전과 변경 기록 확인
- 설치 상태 점검
- Claude Code 등록 (`--scope local`: 그 폴더에서 연 세션에서만 Premiere 도구가 보입니다)
- Premiere 켜기·패널 확인
- `verify_premiere_connection` = `overall: ready` 확인

> 💡 예전 방식(`mcp-setup/install.sh`의 CSInterface.js 패치, `unsafe-script` 주입, MCP Bridge 패널의 Start Bridge)은 1.31.0에서 필요 없습니다.
> 패치는 오히려 최신 커넥터를 옛 파일로 덮어써 망가뜨립니다. 예전에 실행했다면 `"프리미어 MCP 다시 세팅해줘"`라고 하세요.
> 💡 작업 폴더와 프로젝트 파일 이름은 영문으로 두세요. 한글 경로는 프로젝트 가드가 다른 프로젝트로 보고 거부합니다.
> 💡 한국어 UI에서는 MCP 도구 28개가 실패합니다. 무음 컷·자막은 한국어 UI에서도 동작합니다. 자세한 건 [`premiere/README.md`](premiere/README.md).

---

## 🎬 CapCut 시작하기

**추가 설정이 없습니다.** 스킬만 설치하면 됩니다.

다만 편집할 때 규칙이 하나 있습니다:

```
캡컷을 ⌘Q 로 완전히 종료한 뒤 편집 → 다시 열어서 확인
```

캡컷이 실행 중이면 앱이 파일을 덮어써서 편집이 사라집니다.
스킬이 `pgrep -x CapCut` 로 검사해 실행 중이면 **자동으로 중단**하니, 안내가 뜨면 종료하고 다시 시키면 됩니다.

> 외부 파일(모션그래픽·음악)은 macOS 권한 때문에 `~/Movies/CapCut/` 아래로 자동 복사됩니다.
> 데스크탑·문서·다운로드 폴더는 캡컷이 읽지 못합니다.

---

## 🎬 Final Cut Pro 시작하기

**1) MCP 등록** — `mcp<2.0` 고정이 필수입니다(안 하면 즉시 크래시).

```bash
uvx --from fcp-mcp --with "mcp<2.0" fcp-mcp     # 동작 확인
```

`~/.claude.json` 의 `mcpServers` 에 추가:

```json
"fcp": {
  "type": "stdio",
  "command": "uvx",
  "args": ["--from", "fcp-mcp", "--with", "mcp<2.0", "fcp-mcp"]
}
```

**2) Claude 재시작**

**3) 편집 흐름** — Final Cut 은 FCPXML 을 만들어 임포트합니다.
임포트할 때 **"보관함 열기" 대화상자가 뜨니 라이브러리를 선택**해주세요. 이 클릭은 생략할 수 없습니다.

> 임포트는 항상 **새 이벤트**를 만듭니다(같은 이름이면 `이름 2`, `이름 3`…).
> 여러 번 시도하면 헷갈리니, Claude 가 알려주는 이벤트/프로젝트 이름을 확인하세요.

---

## 쓰는 법

Claude에게 그냥 말하면 됩니다.

```
프리미어 무음 구간 2초 이상 전부 잘라줘
캡컷 자막 달아줘
파이널컷으로 컷편집하고 타이틀 넣어줘
```

프로그램 이름을 말할 때만 이 스킬들이 동작합니다. 이름 없이 `"무음 잘라줘"`, `"영상 편집해줘"`라고 하면
어느 프로그램을 쓸지 묻지 않고 편집 프로그램 없이 처리합니다.
결과를 보고 `"자막이 너무 짧게 끊겨"`, `"전환 다른 걸로"` 처럼 말하면 그 부분만 다시 만듭니다.

## 안 될 때 먼저 볼 것

| 증상 | 원인 | 해결 |
|---|---|---|
| Premiere: 도구가 안 보이거나 연결이 안 됨 | MCP 미등록, 다른 폴더에 등록, 커넥터 미설치 | 그 폴더에서 `"프리미어 연결해줘"` — `premiere-mcp-setup` 스킬이 점검부터 합니다 |
| Premiere: `PREMIERE_CONNECTOR_UNREACHABLE` | Premiere가 꺼졌거나 대화상자가 떠 있음, 또는 한글 경로 | 대화상자 처리, 프로젝트를 영문 경로로 |
| Premiere: 예전 `mcp-setup/install.sh`를 실행한 적 있음 | 옛 CSInterface.js 패치가 최신 커넥터를 망가뜨림 | `"프리미어 MCP 다시 세팅해줘"` |
| Premiere: 편집 도구가 `HOST_RECOVERY_REQUIRED` | 직전 실패·타임아웃 | 스킬이 상태를 다시 읽고 복구합니다 — `premiere/mac/references/setup-and-troubleshooting.md` |
| CapCut: 편집이 반영 안 됨 | 캡컷이 실행 중이었음 | ⌘Q 후 다시 시도 |
| CapCut: "미디어를 찾을 수 없음" | macOS 권한(TCC) | 파일이 `~/Movies/CapCut/` 아래 있어야 함 (스킬이 자동 처리) |
| Final Cut: 임포트했는데 자막이 없음 | FCPXML 구조 문제 | 오류 없이 사라지는 케이스 — `finalcut/references/recipes.md` |
| Final Cut: MCP 가 즉시 크래시 | `mcp` 2.0 이 설치됨 | `--with "mcp<2.0"` 을 반드시 붙일 것 |

각 어댑터의 `references/` 에 **실측으로 확인한 함정과 원인**이 있습니다.

---

## 이 저장소의 값어치

각 어댑터의 `references/` 에는 **실제로 부딪힌 함정과 그 원인**이 적혀 있습니다.
문서 어디에도 없고 직접 겪어야만 나오는 것들입니다.

- **Premiere** — macOS 한글 경로(NFD)는 프로젝트 가드가 다른 프로젝트로 보고 거부하는데, 연결 확인은 원인을
  "커넥터 응답 없음"으로 잘못 안내합니다. 자막 도구는 성공해도 스스로 확인하지 못해(`committed_unverified`) 화면으로 확인합니다
- **CapCut** — `draft_info.json` 은 사본이 6개 더 있고, 전부 같이 쓰지 않으면 앱이 조용히 되돌립니다
- **Final Cut** — `<title>` 을 spine 의 형제로 두면 **오류 없이 사라집니다**.
  `adjust-transform` 의 position 은 픽셀이 아니라 화면 높이의 1/100 단위입니다

세 프로그램 모두에서 **"도구가 성공이라고 답해도 실제로는 반영되지 않는"** 경우를 겪었습니다.
그래서 `core/SKILL.md` 에 검증 프로토콜을 못 박아 뒀습니다 — 실행 후 반드시 읽어서 재확인하고,
그래픽·애니메이션은 눈으로 볼 때까지 ✅ 로 판정하지 않습니다.

## 새 프로그램 추가하기

어댑터 하나만 만들면 됩니다. 공통 분석·검증·자가확장 규칙은 `core` 를 그대로 씁니다.
`core/SKILL.md` 의 "새 프로그램을 추가할 때" 절에 조사 순서가 있습니다.

```
공식 API/플러그인 → 스크립팅 브리지 → 디버그 포트 → IPC 소켓
→ 프로젝트 파일 직접 편집 → 오픈소스 선례 검색
```

## 라이선스

MIT — 저장소 루트의 [LICENSE](../LICENSE)를 따릅니다.

- `capcut/scripts/meta/catalog.json` 은 CapCut 내장 리소스의 이름·ID 목록이며, 리소스 파일 자체는 들어 있지 않습니다.
