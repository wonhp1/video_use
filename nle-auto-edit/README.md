# nle-auto-edit — 편집 프로그램 자동화

> [video_use](../README.md) 저장소의 한 갈래입니다. 편집 프로그램 **없이** mp4를 바로 만들려면 저장소 루트의 motion-pipeline을 쓰세요.

Claude가 **영상 편집 프로그램을 직접 조작해** 자동 편집하는 스킬 모음입니다.
무음 구간 컷편집 · 자막 생성 · 모션그래픽 · 전환 · 배경음악을 사람 손 없이 처리합니다.

프로그램마다 **연결 방식만 다르고** 분석·검증 절차는 공통이라,
`core` 뼈대 하나에 프로그램별 **어댑터**를 붙이는 구조로 되어 있습니다.

```
core/          공통 뼈대 — 프로그램 판별, 무음 감지, 받아쓰기, 자막 분할, 검증 규칙
├ premiere/    Adobe Premiere Pro   (MCP + ExtendScript — 실시간 반영)
├ capcut/      CapCut               (draft JSON 편집 — 앱 종료 후 반영)
└ finalcut/    Final Cut Pro        (FCPXML 생성 → 임포트)
```

## 지원 현황

| | Premiere Pro | CapCut | Final Cut Pro |
|---|---|---|---|
| 연결 방식 | MCP + ExtendScript | draft JSON 파일 편집 | FCPXML 임포트 |
| 반영 시점 | **실시간** | 앱 종료 후 | 임포트 시 |
| 사용자 개입 | 없음 | ⌘Q 종료·재실행 | 보관함 선택 클릭 |
| 무음 컷편집 | ✅ | ✅ | ✅ |
| 자막 (스타일·위치) | ✅ | ✅ | ✅ |
| 모션그래픽 오버레이 | ✅ | ✅ | ✅ |
| 전환 | ❌ 렌더 미반영 | ✅ 1,137종 | ✅ |
| 속도 변경 | ✅ | ✅ | ✅ |
| 키프레임 | ❌ 렌더 미반영 | ✅ | ✅ |
| 배경음악 | ✅ | ✅ | ✅ |
| 필터·효과 | ✅ | ✅ 393종 | ⬜ |
| 검증 항목 | ✅18 / ⚠️1 / ❌4 | ✅18 / ⬜1 | ✅10 |

모든 ✅는 **실제로 실행해 눈으로 확인한 것**입니다. 추정은 넣지 않았습니다.
프리미어의 ❌ 4개는 "API 호출은 성공하는데 렌더 결과에 반영되지 않는" 항목이라,
움직이는 그래픽은 외부에서 알파 영상으로 렌더해 배치하는 방식으로 우회합니다.

## 설치

저장소를 clone 한 뒤 이 폴더에서 실행하세요.

```bash
git clone https://github.com/wonhp1/video_use
cd video_use/nle-auto-edit
chmod +x install.sh premiere/mcp-setup/install.sh
./install.sh                 # 전체 (코어 + 어댑터 3개)
./install.sh capcut          # 필요한 것만 골라도 됩니다
```

`~/.claude/skills/` 에 `ai-video-edit`(코어)와 어댑터를 설치합니다.
여기까지는 **어느 프로그램을 쓰든 공통**입니다. 이후는 프로그램별로 다릅니다.

### 필요한 것

| | 용도 | 설치 |
|---|---|---|
| `ffmpeg` / `ffprobe` | 무음 감지, 미디어 정보 | `brew install ffmpeg` |
| `faster-whisper` | 단어 단위 받아쓰기 | `pip3 install faster-whisper` |
| `npx hyperframes` | 모션그래픽 렌더 | 설치 불필요 |

> ⚠️ `python3` 가 anaconda 로 잡히면 faster-whisper 를 못 찾습니다.
> 시스템 python 에 설치하거나, 그 인터프리터 경로를 명시해 쓰세요.

---

## 🎬 Premiere Pro 시작하기

셋 중 설정이 가장 복잡합니다. **순서대로** 하세요.

**1) MCP 서버 설치**

```bash
npm install -g premiere-pro-mcp
npx premiere-pro-mcp --install-cep      # Premiere 용 CEP 패널 설치
```

**2) 설정·패치 적용**

```bash
./premiere/mcp-setup/install.sh
```

이 스크립트가 하는 일:

- Claude Desktop / Claude Code 양쪽에 `premiere-pro` MCP 등록
- **`PREMIERE_MCP_CAPABILITIES` 에 `unsafe-script` 주입** ← 없으면 모든 편집이 실패합니다
- `PlayerDebugMode` 활성화 (서명 없는 CEP 확장 허용)
- CEP 12 `evalScript` 버그 패치 — **필요할 때만** (1.13.0+ 는 업스트림에 반영돼 건너뜁니다)
- `--install-cep` 이 패치 전 원본을 복사하는 순서 문제를 보정

**3) Claude 재시작** (완전 종료 후 다시 실행)

**4) Premiere 재시작 후 브릿지 켜기** ← 매번 필요합니다

```
Premiere Pro 를 ⌘Q 로 완전 종료 → 다시 실행 → 프로젝트와 시퀀스 열기

Window ▸ Extensions ▸ MCP Bridge
  ├ Temp Directory : /tmp/premiere-mcp-bridge
  ├ [Save Config]
  └ [Start Bridge]
```

패널 로그에 **`Premiere Pro: 26.x`** 처럼 버전이 뜨면 성공입니다.
`Could not detect Premiere Pro version` 이 뜨면 CEP 패치가 안 먹은 상태입니다 →
`premiere/mcp-setup/TROUBLESHOOTING.md`

**5) 확인** — Claude 에게 `"프리미어 연결 확인해줘"` 라고 하면 4개 항목이 모두 ready 여야 합니다.

> 💡 창만 닫는 건 종료가 아닙니다. CEP 확장은 실행 중에 설치하면 인식되지 않으니 반드시 ⌘Q.
> 💡 Premiere 2025·2026 을 동시에 켜고 Bridge 를 둘 다 돌리면 같은 폴더를 감시해 충돌합니다.

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

프로그램을 안 밝히면 Claude가 먼저 물어봅니다.
결과를 보고 `"자막이 너무 짧게 끊겨"`, `"전환 다른 걸로"` 처럼 말하면 그 부분만 다시 만듭니다.

## 안 될 때 먼저 볼 것

| 증상 | 원인 | 해결 |
|---|---|---|
| Premiere: 모든 명령이 실패 / `CAPABILITY_DENIED` | `unsafe-script` 미설정 | `premiere/mcp-setup/install.sh` 재실행 후 Claude 재시작 |
| Premiere: `Could not detect Premiere Pro version` | CEP `evalScript` 버그 | 위 스크립트 실행 → **Premiere ⌘Q 후 재시작** |
| Premiere: `Window ▸ Extensions` 에 MCP Bridge 없음 | 실행 중에 CEP 설치함 | Premiere ⌘Q 후 재시작 |
| Premiere: 연결은 되는데 편집이 안 먹음 | 브릿지 미시작 | 패널에서 **Start Bridge** |
| CapCut: 편집이 반영 안 됨 | 캡컷이 실행 중이었음 | ⌘Q 후 다시 시도 |
| CapCut: "미디어를 찾을 수 없음" | macOS 권한(TCC) | 파일이 `~/Movies/CapCut/` 아래 있어야 함 (스킬이 자동 처리) |
| Final Cut: 임포트했는데 자막이 없음 | FCPXML 구조 문제 | 오류 없이 사라지는 케이스 — `finalcut/references/recipes.md` |
| Final Cut: MCP 가 즉시 크래시 | `mcp` 2.0 이 설치됨 | `--with "mcp<2.0"` 을 반드시 붙일 것 |

각 어댑터의 `references/recipes.md` 에 **실측으로 확인한 함정과 원인**이 코드와 함께 있습니다.

---

## 이 저장소의 값어치

각 어댑터의 `references/recipes.md` 에는 **실제로 부딪힌 함정과 그 원인**이 코드와 함께 적혀 있습니다.
문서 어디에도 없고 직접 겪어야만 나오는 것들입니다.

- **Premiere** — CEP 12의 `evalScript` 가 콜백을 네이티브에 넘기지 않아 항상 `undefined` 를 반환하는 버그
  (이것 하나가 모든 걸 막고 있었습니다. 패치 포함)
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

- `premiere/mcp-setup/patches/CSInterface.js` 는 Adobe CEP 의 `CSInterface.js` 를 고친 파일로, 원 저작권 고지(Adobe)를 그대로 두었습니다.
- `capcut/scripts/meta/catalog.json` 은 CapCut 내장 리소스의 이름·ID 목록이며, 리소스 파일 자체는 들어 있지 않습니다.
