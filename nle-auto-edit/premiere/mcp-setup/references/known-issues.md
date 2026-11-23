# 실측으로 확인된 사실과 알려진 문제

기준 환경: macOS, Adobe Premiere Pro 2027(27.0.0), premiere-pro-mcp 1.31.0, CEP 브리지(UXP는 설정하지 않음), 2026-11-22 테스트.

이 문서는 위 버전 기준이다. `scripts/check-upstream.mjs`가 더 새 버전이 있다고 하면 CHANGELOG에서 고쳐진 항목부터 다시 확인한다.

## 목차
1. 도구 전체 테스트 집계
2. 메뉴 이름(영어·한국어 UI)
3. Premiere UI 언어 바꾸기
4. 한국어 UI에서만 실패하는 도구
5. 한글 경로에서만 실패하는 도구
6. 언어·경로와 상관없이 안 되는 도구
7. 연결이 막히는 상황

## 1. 도구 전체 테스트 집계

전체 453개(등록 451 + unsafe-script 권한이 있어야 등록되는 2).

| 조건 | 성공 | 부분 | 실패 | 건너뜀 |
|---|---:|---:|---:|---:|
| 한국어 UI | 362 | 30 | 43 | 18 |
| 영어 UI | 390 | 26 | 19 | 18 |

건너뜀은 After Effects 필요 11개, UXP 필요 2개, 외부 업로드(`transcribe_audio`, ElevenLabs) 1개, CC Libraries 1개, unsafe-script 2개 등이다.

## 2. 메뉴 이름

| 용도 | 영어 UI | 한국어 UI |
|---|---|---|
| 앱 메뉴 / 종료 | `Premiere` › `Quit Premiere` | `Premiere` › 종료 항목(`list`로 확인) |
| 패널 | `Window` › `Extensions` › `MCP for Adobe Premiere Pro` | `창` › `확장명` › `MCP for Adobe Premiere Pro` |
| 최근 프로젝트 | `File` › `Open Recent` | `파일` › 최근 항목(`list`로 확인) |
| 새 프로젝트(홈 화면 버튼) | `New project` | `새 프로젝트` |

computer use의 `app_menu`는 백그라운드에서 메뉴를 읽고 누를 수 있다. 최상위 목록을 보려면 `list`에 배열(`["Window"]`처럼)을 넘긴다. 문자열 `"null"`은 동작하지 않았다.

## 3. Premiere UI 언어 바꾸기

재설치는 필요 없다. Premiere의 Debug Database 설정만 바꾼다.

1. 사용자 허락을 받는다. Premiere 언어가 바뀌는 일이라 사용자가 정해야 한다.
2. 설치본에 대상 언어 사전이 있는지 확인한다. macOS는 `.../Adobe Premiere Pro 20xx.app/Contents/Dictionaries/en_US`.
3. Premiere를 **완전히 종료**한다. 켜진 상태에서 고치면 종료할 때 덮어써진다.
4. 설정 파일을 백업한다.
   - macOS: `~/Library/Preferences/Adobe/Premiere Pro/<버전, 예: 27.0>/Debug Database.txt`
   - Windows: 위치를 찾아 확인한다. 보통 `%APPDATA%\Adobe\Premiere Pro\<버전>\` 근처다.
5. `ApplicationLanguage` 줄의 현재값(두 번째 칸)을 `en_US`로 바꾼다. 예: `ApplicationLanguage	en_US	ko_KR`. 세 번째 칸은 기본값이라 그대로 둔다.
6. Premiere를 다시 실행한다.
7. 되돌릴 때는 Premiere를 종료하고, 두 번째 칸을 원래 값(예: `ko_KR`)으로 바꾸거나 백업 파일을 복원한다.

`ApplicationLanguageBilingual` 줄은 다른 설정이니 헷갈리지 않는다.

## 4. 한국어 UI에서만 실패하는 도구 (영어 UI에서 성공)

| 묶음 | 도구 |
|---|---|
| 모션·불투명도 단축 도구 | `set_clip_opacity`, `set_clip_scale`, `set_clip_position`, `set_clip_rotation`, `set_clip_anchor_point`, `set_uniform_scale`, `set_scale_width_height`, `set_clip_properties`, `set_clip_properties_batch`, `set_blend_mode`, `set_anti_alias_quality` |
| 오디오 | `get_clip_volume`, `set_clip_volume`, `adjust_audio_levels`, `set_clips_volume`, `add_audio_keyframes`, `setup_ducking` |
| 색·안정화 | `color_correct`, `stabilize_clip` |
| 효과 제거 | `remove_effect`, `remove_effect_by_name`, `remove_all_effects` |
| 텍스트·그래픽 | `add_title`(한국어 UI에선 성공이라 보고하지만 클립이 생기지 않음), `add_caption_graphics` |
| 기타 | `paste_clip_attributes`, `consolidate_and_transfer`('복사_' 폴더를 'Copied_'로 찾음) |

한국어 UI를 그대로 쓸 때의 우회 방법: `set_effect_property`·`apply_effect`에 한국어 이름을 넣는다. 예: '모션'/'비율 조정', '볼륨'/'레벨', 'Lumetri 색상'/'노출', '크로스 디졸브'. 단, `add_caption_graphics`는 대체 방법이 없다.

메타데이터에 한국어 값을 쓰면 읽을 때 깨지고, XMP에 한국어를 쓰면 검증 단계에서 실패한다.

## 5. 한글 경로에서만 실패하는 도구 (영문 경로에서 해결)

- **원인**: macOS 디스크의 한글 이름은 자모 분리형(NFD)이고, 손으로 입력한 경로는 완성형(NFC)이다. 서버가 두 형태를 같은 것으로 맞추지 않고 그대로 비교한다.
- **증상**
  - `expected_project_path` 가드가 같은 프로젝트를 `active project differs`로 거부한다.
  - 가드를 넣은 `verify_premiere_connection`은 이를 `PREMIERE_CONNECTOR_UNREACHABLE`로 잘못 안내한다.
  - `create_project`는 파일을 만들고도 실패라고 보고한다.
  - `close_project`는 `project_path`를 완성형으로 주면 `No open project`라고 답한다.
- **해결**: 작업 폴더와 프로젝트 파일 이름을 영문으로 둔다. 경로를 꼭 한글로 둬야 하면 디스크에서 읽은 경로 문자열을 그대로 가드에 넣는다.

## 6. 언어·경로와 상관없이 안 되는 도구

- **설계상 지원하지 않음**: `set_poster_frame`, `reverse_clip`, `speed_change`, `set_clip_speed_qe`, `nest_clips`, `unnest_sequence`, `apply_lut`, `add_text_overlay`, `replace_clip_media`, `import_edl`
- **Premiere 2027 API 문제**: `get_render_queue_status`, `set_work_area`, `add_adjustment_layer`, `export_aaf`(CEP), `attach_custom_property`, `set_clip_pan`, `crop_clip`(`apply_effect`에 'Crop (Legacy)'로 우회)
- **도구 결함으로 보이는 것**
  - `consolidate_duplicates`, `delete_multiple_project_items`(여러 개 삭제는 실패, 하나씩 삭제는 정상)
  - `move_clip`: 오디오가 따라오지 않음
  - `unlink_selection`, `remove_keyframe_range`
  - `detect_audio_transients`: 시각이 약 2.4% 밀림
  - `manage_media_watch`, `preview_watched_media_import`: 새 파일을 잡지 못함(영문 경로에서도 같음)
  - `export_sequence_job_start`, `get_export_job_status`: 파일은 만들어졌는데 상태가 'encoding'에 머묾

## 7. 연결이 막히는 상황

- **대화상자**: Scratch Disk Settings, 미디어 연결, 저장 확인 같은 Premiere 대화상자가 떠 있으면 브리지가 멈춘다. 프로젝트를 다른 폴더로 옮겨서 열었을 때 Scratch Disk Settings가 떠서 `open_project`가 120초 타임아웃으로 끝났다. 대화상자에서 OK를 누르자 프로젝트는 정상으로 열려 있었다.
- **편집 잠금**: 타임아웃 뒤에는 편집 도구가 잠긴다(`HOST_RECOVERY_REQUIRED`). 다음 순서로 푼다.
  1. `inspect_operation_recovery`
  2. 실제 상태를 다시 조회해 확인(예: `get_project_info`)
  3. `acknowledge_operation_recovery`(앞에서 받은 revision 값을 넣는다)
- **미디어 재연결**: 프로젝트 폴더를 통째로 옮기면 미디어는 Premiere가 상대 경로로 대부분 자동 재연결한다. 단, 모션 그래픽 템플릿 미디어는 옛 경로를 가리킨 채 오프라인으로 남을 수 있다.
