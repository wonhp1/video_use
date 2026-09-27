# 캡컷 편집 검증 매트릭스

실측으로 확인된 것만 ✅. 추정은 절대 ✅로 적지 않는다.
모든 저장은 `capcut_edit.py` 의 `save()` 를 통해서만 한다.

## 절대 규칙 (위반하면 편집이 통째로 되돌아감)

1. **미러 6개 동시 기록** — `draft_info.json` 하나만 고치면 캡컷이 사본에서 복구한다.
   `draft_info.json` / `.bak` / `template-2.tmp` × (프로젝트 루트, `Timelines/<main_timeline_id>/`)
2. **캡컷 종료 확인** — 가드는 `pgrep -x CapCut`.
   `pgrep -f ".../MacOS/CapCut "` (끝 공백)은 본체를 못 잡는다.
3. **세그먼트 ↔ material 은 짝** — 한쪽만 고치면 캡컷이 전체를 리셋한다.
4. **외부 파일은 `~/Movies/CapCut/` 아래에 둔다** — macOS TCC 가 데스크탑/문서/다운로드를 막는다.
   파일이 존재해도 캡컷이 못 읽어 '미디어를 찾을 수 없음' 이 뜬다. `asset_path()` + `register_material()`.
5. 시간 단위는 **마이크로초**(1초 = 1_000_000).

## 검증 현황

| # | 기능 | 상태 | 비고 |
|---|---|---|---|
| 1 | 무음 구간 컷편집 | ✅ | 세그먼트 재구성. ffmpeg silencedetect 로 구간 산출 |
| 2 | 크기 (scale) | ✅ | `clip.scale{x,y}` |
| 3 | 위치 (transform) | ✅ | `clip.transform{x,y}` — 정규화 좌표, 우상단 = (+,−) |
| 4 | 회전 (rotation) | ✅ | `clip.rotation` 도 단위 |
| 5 | 좌우/상하 반전 | ✅ | `clip.flip{horizontal,vertical}` |
| 6 | 불투명도 (alpha) | ✅ | `clip.alpha` |
| 7 | 볼륨 | ✅ | `segment.volume` + `last_nonzero_volume` |
| 8 | 속도 (speed) | ✅ | 세그먼트별 고유 speeds material 발급 필수 |
| 9 | 자막 / 텍스트 | ✅ | `text_material()` — 외부 리소스 불필요 |
| 10 | 오버레이 (2번째 영상 트랙) | ✅ | 새 video 트랙 + `track_render_index` 크게 |
| 11 | 트랜지션 | ✅ | 카탈로그 1137개. **앞** 세그먼트에 붙인다 |
| 12 | 효과 / 필터 | ✅ | 필터→`effects`+filter트랙, 효과→`video_effects`+effect트랙 |
| 13 | 배경음악 (오디오 트랙) | ✅ | `audios`(extract_music) + audio 트랙 |
| 14 | 키프레임 애니메이션 | ✅ | `common_keyframes`, 크기는 X·Y 둘 다 |
| 15 | 자막 스타일링 (메인/중간/하단) | ✅ | 크기·색·테두리·그림자·굵기·위치 |
| 16 | 텍스트 등장/퇴장 애니메이션 | ✅ | `text_intro` 182 / `text_outro` 100 |
| 17 | 영상 등장/퇴장 애니메이션 | ✅ | `video_intro` 251 / `video_outro` 219 |
| 18 | 알파 모션그래픽 (ProRes 4444) | ✅ | **캡컷도 알파 지원** — 프리미어 렌더 재사용 가능 |
| 19 | 스티커 | ⬜ | pyCapCut 카탈로그에 없음 |

## 검증된 코드

### 무음 컷 — 유지 구간 재구성
```python
keeps=[]; prev=src_start
for s,e in sorted(cuts):
    if s > prev+0.01: keeps.append((prev,s))
    prev=max(prev,e)
if prev < src_end-0.01: keeps.append((prev,src_end))

tl=0; new=[]
for a,b in keeps:
    s=copy.deepcopy(seg0); length=b-a
    s['source_timerange']={'start':int(a*US),'duration':int(length*US)}
    s['target_timerange']={'start':int(tl*US),'duration':int(length*US)}
    new.append(s); tl+=length
```
⚠️ deepcopy 하면 `extra_material_refs` 가 전부 같은 id를 가리킨다. material 을
세그먼트별로 새로 발급하지 않으면 나중에 speed·효과 변경이 실패한다.

### clip 속성 (2~7번, 전부 검증됨)
```python
s['clip'] = {
    "scale":     {"x":0.15, "y":0.15},          # 크기
    "transform": {"x":0.75, "y":-0.75},         # 위치 (우상단)
    "rotation":  180.0,                         # 회전
    "flip":      {"horizontal":True, "vertical":False},
    "alpha":     0.05,                          # 불투명도
}
s['volume']=0.0; s['last_nonzero_volume']=0.01  # 볼륨
```

### 속도 — 세그먼트별 고유 material 발급 필수
```python
# ❌ s['speed']=2.0 만 바꾸면 materials.speeds(공유 id)와 충돌해 되돌아감
mid = f"AAAAAAAA-0000-4000-8000-{i:012d}"
d['materials']['speeds'][i] = {"id":mid,"type":"speed","mode":0,
                               "speed":sp,"curve_speed":None}
s['extra_material_refs'] = [mid if cc.material(d,r)[1]=='speeds' else r
                            for r in s['extra_material_refs']]
s['speed'] = sp
# 타임라인 길이도 다시 계산해야 한다
s['target_timerange'] = {"start":tl, "duration":int(round(src/sp))}
```

## 실패했을 때 — 1회 실패로 ❌ 판정하지 않는다

1. 캡컷이 정말 종료돼 있었나? (`pgrep -x CapCut`)
2. 미러 6개에 전부 썼나?
3. 적용 직후 해시와 캡컷을 연 뒤의 해시가 다른가? → 다르면 캡컷이 덮어쓴 것
4. 바꾼 속성이 참조하는 material 도 같이 고쳤나?
5. material id 가 세그먼트끼리 중복되지 않았나?
6. 길이 관련 필드(`target_timerange`, `d['duration']`)를 다시 계산했나?
7. 변화가 미묘해서 못 알아본 건 아닌가? → **극단값으로 다시 시도**

## Windows 차이점 (⚠️ 실측 미검증 — macOS 검증본 기반)

| | macOS | Windows |
|---|---|---|
| draft 위치 | `~/Movies/CapCut/User Data/Projects/com.lveditor.draft` | `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft` |
| **draft 파일명** | `draft_info.json` | **`draft_content.json`** |
| 프로세스 가드 | `pgrep -x CapCut` | `tasklist /FI "IMAGENAME eq CapCut.exe"` |
| 외부 파일 권한 | **TCC 로 데스크탑 차단** → `~/Movies/CapCut/` 필수 | TCC 없음 → 아무 경로나 가능 |
| 한글 경로 | APFS 는 NFD 저장 | 해당 없음 |

`capcut_edit.py` 는 `sys.platform` 으로 위 항목을 자동 전환한다.
`draft_file()` 은 **실제로 존재하는 파일명을 먼저 찾고** OS 기본값으로 폴백하므로,
파일명 가정이 틀려도 동작한다.

**윈도우에서 아직 확인 못 한 것** (첫 사용자가 확인해 주면 좋을 것):
1. 미러 파일이 macOS 처럼 6개인지 (`draft_content.json` / `.bak` / `template-2.tmp` × 루트·Timelines)
2. `Timelines/<UUID>/` 구조가 동일한지
3. `materials` 스키마와 리소스 ID 가 같은지 (같은 서버를 쓰므로 같을 가능성이 높다)
4. `draft_meta_info.json` 등록부가 같은 방식인지

1번이 다르면 편집이 조용히 되돌아간다. 처음 쓸 때 **적용 직후 해시와
캡컷을 연 뒤 해시를 비교**해 확인할 것.
