"""캡컷 draft 안전 편집 헬퍼.

핵심 규칙 (실측으로 확인, 2026-08-23):
  1. draft_info.json 은 미러가 6개 더 있다. 전부 같이 써야 반영된다.
     하나만 고치면 캡컷이 사본에서 복구해 되돌려버린다.
  2. 캡컷이 실행 중이면 무조건 중단. 가드는 pgrep -x CapCut.
  3. 세그먼트와 material 은 짝이다. 한쪽만 고치면 캡컷이 전체를 리셋한다.
     (예: segment.speed 만 바꾸면 materials.speeds 와 충돌 → 되돌아감)
"""
import json, os, glob, shutil, time, subprocess

import sys as _sys

US = 1_000_000  # 캡컷 시간 단위 = 마이크로초
WINDOWS = _sys.platform.startswith("win")

# 캡컷 draft 위치와 파일명이 OS 마다 다르다 (실측: macOS / 문서 확인: Windows)
#   macOS   ~/Movies/CapCut/User Data/Projects/com.lveditor.draft   draft_info.json
#   Windows %LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft  draft_content.json
if WINDOWS:
    _root = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    BASE = os.path.join(_root, "CapCut", "User Data", "Projects", "com.lveditor.draft")
    DRAFT_NAMES = ("draft_content.json", "draft_info.json")
    PROC_NAME = "CapCut.exe"
else:
    BASE = os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft")
    DRAFT_NAMES = ("draft_info.json", "draft_content.json")
    PROC_NAME = "CapCut"


def draft_file(proj_dir):
    """이 프로젝트가 실제로 쓰는 draft 파일명을 찾는다. 없으면 OS 기본값."""
    for n in DRAFT_NAMES:
        if os.path.exists(os.path.join(proj_dir, n)):
            return n
    return DRAFT_NAMES[0]


def _mirrors(proj_dir):
    paths = [proj_dir]
    tl = os.path.join(proj_dir, "Timelines")
    if os.path.isdir(tl):
        pj = os.path.join(tl, "project.json")
        if os.path.exists(pj):
            main = json.load(open(pj, encoding="utf-8")).get("main_timeline_id")
            if main and os.path.isdir(os.path.join(tl, main)):
                paths.append(os.path.join(tl, main))
        else:
            paths += [p for p in glob.glob(os.path.join(tl, "*-*")) if os.path.isdir(p)]
    name = draft_file(proj_dir)
    files = [os.path.join(p, f) for p in paths
             for f in (name, name + ".bak", "template-2.tmp")]
    return [f for f in files if os.path.exists(f)]


def guard():
    """캡컷 실행 중이면 예외. 실행 중에 고치면 앱이 통째로 덮어쓴다."""
    if WINDOWS:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {PROC_NAME}"],
                             capture_output=True, text=True).stdout
        running = PROC_NAME.lower() in out.lower()
        how = "완전 종료(트레이 아이콘까지)"
    else:
        running = bool(subprocess.run(["pgrep", "-x", PROC_NAME],
                                      capture_output=True).stdout.strip())
        how = "⌘Q 로 완전 종료"
    if running:
        raise SystemExit(f"❌ 캡컷 실행 중 — {how} 후 다시 실행하세요")


def projects():
    return sorted(d for d in os.listdir(BASE)
                  if os.path.isdir(os.path.join(BASE, d)) and not d.startswith("."))


def load(name):
    """(draft_dict, project_dir) 반환."""
    guard()
    p = os.path.join(BASE, name)
    if not os.path.isdir(p):
        raise SystemExit(f"❌ 프로젝트 없음: {name}\n   가능: {projects()}")
    return json.load(open(os.path.join(p, draft_file(p)), encoding="utf-8")), p


def save(d, proj_dir, backup=True):
    """미러 전체에 동일하게 기록. 반드시 이 함수로만 저장할 것."""
    guard()
    ms = _mirrors(proj_dir)
    if backup:
        bak = f"/tmp/capcut_bak_{int(time.time())}"
        os.makedirs(bak, exist_ok=True)
        for m in ms:
            shutil.copy2(m, os.path.join(bak, m.replace("/", "_")))
        print(f"백업: {bak}")
    blob = json.dumps(d, ensure_ascii=False)
    for m in ms:
        open(m, "w", encoding="utf-8").write(blob)
    print(f"✅ 미러 {len(ms)}개 동기화")
    return ms


def video_track(d):
    return next(t for t in d["tracks"] if t["type"] == "video")


def segments(d):
    return video_track(d)["segments"]


def material(d, mid):
    """id 로 material 찾기 → (딕셔너리, 카테고리)."""
    for cat, v in d["materials"].items():
        if isinstance(v, list):
            for m in v:
                if isinstance(m, dict) and m.get("id") == mid:
                    return m, cat
    return None, None


# ─────────────────────────────────────────────────────────────
# 생성 헬퍼 — 전부 실측 검증됨
# ─────────────────────────────────────────────────────────────
import copy as _copy

_CAT = None
def catalog():
    """pyCapCut 에서 추출한 리소스 카탈로그 (트랜지션/애니메이션/필터/효과)."""
    global _CAT
    if _CAT is None:
        here = os.path.dirname(os.path.abspath(__file__))
        _CAT = json.load(open(os.path.join(here, "meta", "catalog.json"), encoding="utf-8"))
    return _CAT


def find_effect(kind, name, vip=False):
    """이름으로 리소스 찾기. kind: transition_meta / video_intro / video_outro /
    video_group_animation / filter_meta / video_scene_effect / text_intro / text_outro"""
    items = catalog()[kind]
    for x in items:
        if x["name"] == name and (vip or not x.get("is_vip")):
            return x
    cands = [x["name"] for x in items if name in x["name"]][:8]
    raise SystemExit(f"❌ '{name}' 없음 ({kind}). 비슷한 이름: {cands}")


def uid(tag, i=0):
    """결정적 id 생성 — 같은 입력이면 같은 id."""
    return f"{tag[:8].upper():X<8}-0000-4000-8000-{i:012d}"


def new_track(ttype, tid, segments):
    return {"id": tid, "type": ttype, "flag": 0, "attribute": 0,
            "name": "", "is_default_name": True, "segments": segments}


def transition_material(mid, meta):
    return {"id": mid, "type": "transition", "name": meta["name"],
            "effect_id": meta["effect_id"], "resource_id": meta["resource_id"],
            "duration": int(meta["duration"] * US),
            "is_overlap": bool(meta.get("is_overlap", True)),
            "category_id": "", "category_name": "", "path": "",
            "platform": "all", "request_id": "", "algorithm_artifact_path": ""}


def animation_material(mid, entries):
    """entries: [(meta, 'in'|'out'|'group', start_sec)]"""
    anims = []
    for meta, kind, start in entries:
        anims.append({"id": meta["effect_id"], "name": meta["name"],
            "resource_id": meta["resource_id"], "type": kind,
            "category_id": kind, "category_name": {"in": "入场", "out": "出场"}.get(kind, "组合"),
            "start": int(start * US), "duration": int(meta["duration"] * US),
            "material_type": "video", "panel": "video", "platform": "all",
            "anim_adjust_params": None, "path": "", "request_id": ""})
    return {"id": mid, "type": "sticker_animation",
            "multi_language_current": "none", "animations": anims}


def text_material(tid, txt, size=15.0, color=(1.0, 1.0, 1.0),
                  border=None, border_width=0.08, shadow=False, bold=False):
    """border: (r,g,b) 0~1 또는 None."""
    style = {"fill": {"alpha": 1.0, "content": {"render_type": "solid",
                      "solid": {"alpha": 1.0, "color": list(color)}}},
             "font": {"id": "", "path": ""}, "range": [0, len(txt)],
             "size": size, "bold": bold, "useLetterColor": True}
    if border:
        style["strokes"] = [{"content": {"render_type": "solid",
                             "solid": {"alpha": 1.0, "color": list(border)}},
                             "width": border_width}]
    content = json.dumps({"styles": [style], "text": txt}, ensure_ascii=False)
    return {"id": tid, "type": "text", "content": content,
        "alignment": 1, "background_alpha": 1.0, "background_color": "",
        "background_height": 0.14, "background_horizontal_offset": 0.0,
        "background_round_radius": 0.0, "background_style": 0,
        "background_vertical_offset": 0.0, "background_width": 0.14,
        "bold_width": 1.0 if bold else 0.0, "border_alpha": 1.0,
        "border_color": "" if not border else "#000000",
        "border_width": border_width, "check_flag": 7,
        "combo_info": {"text_templates": []}, "fixed_height": -1.0, "fixed_width": -1.0,
        "font_category_id": "", "font_category_name": "", "font_id": "", "font_name": "",
        "font_path": "", "font_resource_id": "", "font_size": size,
        "font_source_platform": 0, "font_team_id": "", "font_title": "none",
        "font_url": "", "fonts": [], "force_apply_line_max_width": False,
        "global_alpha": 1.0, "group_id": "", "has_shadow": shadow, "initial_scale": 1.0,
        "inner_padding": -1.0, "is_rich_text": False, "italic_degree": 0,
        "ktv_color": "", "language": "", "layer_weight": 1, "letter_spacing": 0.0,
        "line_feed": 1, "line_max_width": 0.82, "line_spacing": 0.02,
        "multi_language_current": "none", "name": "", "original_size": [],
        "preset_category": "", "preset_category_id": "", "preset_has_set_alignment": False,
        "preset_id": "", "preset_index": 0, "preset_name": "", "recognize_task_id": "",
        "recognize_type": 0, "relevance_segment": [], "shadow_alpha": 0.9,
        "shadow_angle": -45.0, "shadow_color": "#000000" if shadow else "",
        "shadow_distance": 5.0,
        "shadow_point": {"x": 0.6363961030678928, "y": -0.6363961030678928},
        "shadow_smoothing": 1.0, "shape_clip_x": False, "shape_clip_y": False,
        "style_name": "", "sub_type": 0, "subtitle_keywords": None, "text_alpha": 1.0,
        "text_color": "#FFFFFF", "text_preset_resource_id": "", "text_size": 30,
        "text_to_audio_ids": [], "tts_auto_update": False, "typesetting": 0,
        "underline": False, "underline_offset": 0.22, "underline_width": 0.05,
        "use_effect_default_color": True,
        "words": {"end_time": [], "start_time": [], "text": []}}


def base_segment(sid, material_id, refs, start, dur, src_start=0,
                 y=0.0, x=0.0, scale=1.0, render_index=14000, track_render_index=1):
    return {"id": sid, "material_id": material_id, "extra_material_refs": list(refs),
        "source_timerange": {"start": src_start, "duration": dur},
        "target_timerange": {"start": start, "duration": dur},
        "render_timerange": {"start": 0, "duration": 0},
        "clip": {"scale": {"x": scale, "y": scale}, "rotation": 0.0,
                 "transform": {"x": x, "y": y},
                 "flip": {"horizontal": False, "vertical": False}, "alpha": 1.0},
        "speed": 1.0, "volume": 1.0, "last_nonzero_volume": 1.0, "visible": True,
        "uniform_scale": {"on": True, "value": 1.0},
        "render_index": render_index, "track_render_index": track_render_index,
        "keyframe_refs": [], "common_keyframes": [],
        "enable_adjust": False, "enable_color_curves": True, "enable_color_wheels": True,
        "enable_hsl_curves": False, "enable_lut": False, "enable_hsl": False,
        "enable_video_mask": True, "enable_adjust_mask": False, "enable_mask_stroke": False,
        "enable_mask_shadow": False, "enable_color_match_adjust": False,
        "enable_color_correct_adjust": False, "enable_smart_color_adjust": False,
        "enable_color_adjust_pro": False, "cartoon": False, "intensifies_audio": False,
        "is_loop": False, "is_placeholder": False, "is_tone_modify": False,
        "reverse": False, "state": 0, "group_id": "", "desc": "", "template_id": "",
        "template_scene": "default", "raw_segment_id": "", "caption_info": None,
        "hdr_settings": None, "track_attribute": 0, "lyric_keyframes": None,
        "source": "", "color_correct_alg_result": "", "digital_human_template_group_id": "",
        "responsive_layout": {"enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0}}


def clone_refs(d, seg, tag, i):
    """세그먼트의 부속 material 들을 새 id 로 복제해 반환 → (새 refs, 추가할 material 목록)."""
    new_refs, extra = [], []
    for rid in seg["extra_material_refs"]:
        m, cat = material(d, rid)
        if m is None:
            continue
        nm = _copy.deepcopy(m)
        nm["id"] = uid(f"{tag}{cat[:2]}", i)
        d["materials"][cat].append(nm)
        new_refs.append(nm["id"])
    return new_refs, extra


def video_material(mid, path, name=None, width=1920, height=1080,
                   duration_us=0, has_audio=True):
    path = real_path(path)
    return {"id": mid, "type": "video", "path": path,
        "material_name": name or os.path.basename(path),
        "width": width, "height": height, "duration": duration_us,
        "has_audio": has_audio, "category_id": "", "category_name": "local",
        "check_flag": 62978047, "crop": {"upper_left_x": 0.0, "upper_left_y": 0.0,
            "upper_right_x": 1.0, "upper_right_y": 0.0, "lower_left_x": 0.0,
            "lower_left_y": 1.0, "lower_right_x": 1.0, "lower_right_y": 1.0},
        "crop_ratio": "free", "crop_scale": 1.0, "extra_type_option": 0,
        "source_platform": 0, "audio_fade": None, "cartoon_path": "",
        "intensifies_audio_path": "", "intensifies_path": "", "is_ai_generate_content": False,
        "is_copyright": False, "is_text_edit_overdub": False, "is_unified_beauty_mode": False,
        "local_id": "", "local_material_id": "", "material_id": "", "material_url": "",
        "matting": {"flag": 0, "has_use_quick_brush": False, "has_use_quick_eraser": False,
            "interactiveTime": [], "path": "", "strokes": []},
        "media_path": "", "object_locked": None, "origin_material_id": "",
        "picture_from": "none", "picture_set_category_id": "",
        "picture_set_category_name": "", "request_id": "", "reverse_intensifies_path": "",
        "reverse_path": "", "smart_motion": None, "source": 0, "source_material_id": "",
        "stable": None, "team_id": "", "video_algorithm": {"algorithms": [],
            "complement_frame_config": None, "deflicker": None, "gameplay_configs": [],
            "motion_blur_config": None, "noise_reduction": None, "path": "",
            "quality_enhance": None, "time_range": None}, "aigc_type": "none",
        "audio_fade_id": "", "beauty_body_preset_id": "", "gameplay": None,
        "multi_camera_info": None}


def real_path(path):
    """디스크에 실제로 저장된 표기 그대로 반환.
    macOS APFS 는 한글을 NFD(자모 분리)로 저장하는데, JSON 에 NFC 로 쓰면
    캡컷이 문자열 매칭에 실패해 '미디어를 찾을 수 없음' 이 뜬다."""
    import unicodedata
    if os.path.exists(path) and all(ord(c) < 128 for c in path):
        return path
    parts = path.split(os.sep)
    cur = os.sep if path.startswith(os.sep) else ""
    for part in parts:
        if not part:
            continue
        nxt = os.path.join(cur, part) if cur else part
        if os.path.exists(nxt) and part in (os.listdir(cur or "/") if os.path.isdir(cur or "/") else []):
            cur = nxt; continue
        found = None
        try:
            for e in os.listdir(cur or "/"):
                if unicodedata.normalize("NFC", e) == unicodedata.normalize("NFC", part):
                    found = e; break
        except OSError:
            pass
        if found is None:
            raise SystemExit(f"❌ 경로 없음: {nxt}")
        cur = os.path.join(cur, found)
    return cur


def register_material(proj_dir, path, width, height, duration_us, mtype="video"):
    """draft_meta_info.json 의 draft_materials 등록부에 미디어를 추가한다.
    여기 없는 파일은 캡컷이 '미디어를 찾을 수 없음' 으로 처리한다."""
    import time as _t, uuid as _u
    mp = os.path.join(proj_dir, "draft_meta_info.json")
    meta = json.load(open(mp, encoding="utf-8"))
    groups = meta.setdefault("draft_materials", [])
    grp = next((g for g in groups if g.get("type") == 0), None)
    if grp is None:
        grp = {"type": 0, "value": []}
        groups.append(grp)
    if any(v.get("file_Path") == path for v in grp["value"]):
        return False
    now = int(_t.time())
    grp["value"].append({
        "ai_group_type": "", "create_time": now, "duration": duration_us,
        "enter_from": 0, "extra_info": os.path.basename(path), "file_Path": path,
        "height": height, "id": str(_u.uuid4()).upper(),
        "import_time": now, "import_time_ms": now * 1000000,
        "item_source": 1, "material_color_tag": 0, "md5": "", "metetype": mtype,
        "roughcut_time_range": {"duration": duration_us, "start": 0},
        "sub_time_range": {"duration": -1, "start": -1},
        "type": 0, "width": width})
    json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False)
    return True


ASSETS = (os.path.join(os.path.dirname(os.path.dirname(BASE)), "claude-assets")
          if WINDOWS else os.path.expanduser("~/Movies/CapCut/claude-assets"))

def asset_path(src):
    """외부 파일을 캡컷이 읽을 수 있는 위치로 복사하고 그 경로를 반환.

    macOS 는 데스크탑/문서/다운로드를 TCC 로 보호한다. 캡컷에 해당 폴더 권한이
    없으면 파일이 존재해도 '미디어를 찾을 수 없음' 이 뜬다.
    ~/Movies/CapCut/ 아래는 캡컷 자신의 영역이라 항상 읽을 수 있다."""
    import shutil as _sh
    src = src if WINDOWS else real_path(src)   # NFD 정규화는 macOS 전용
    os.makedirs(ASSETS, exist_ok=True)
    dst = os.path.join(ASSETS, os.path.basename(src))
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
        _sh.copy2(src, dst)
    return dst


def cut_silence(d, cuts, track=None):
    """무음 구간을 제거하고 세그먼트를 재구성한다.

    cuts: [(시작초, 끝초), ...]  — 원본 기준
    세그먼트를 복제할 때 material 도 세그먼트별 고유 id 로 새로 발급한다.
    (deepcopy 만 하면 전부 같은 id 를 가리켜 나중에 speed·효과 변경이 실패한다)
    """
    vt = track or video_track(d)
    segs = vt["segments"]
    if not segs:
        raise SystemExit("❌ 영상 세그먼트가 없다")
    base = segs[0]
    src0 = base["source_timerange"]["start"] / US
    src_end = src0 + base["source_timerange"]["duration"] / US

    keeps, prev = [], src0
    for s, e in sorted(cuts):
        if s > prev + 0.01:
            keeps.append((prev, min(s, src_end)))
        prev = max(prev, e)
    if prev < src_end - 0.01:
        keeps.append((prev, src_end))
    if not keeps:
        raise SystemExit("❌ 남는 구간이 없다 — 임계값을 조정하세요")

    new_segs, tl = [], 0
    for i, (a, b) in enumerate(keeps):
        s = _copy.deepcopy(base)
        length = b - a
        s["id"] = uid("CUTSEG", i)
        s["source_timerange"] = {"start": int(round(a * US)), "duration": int(round(length * US))}
        s["target_timerange"] = {"start": tl, "duration": int(round(length * US))}
        s["common_keyframes"] = []
        # material 을 세그먼트별로 새로 발급
        refs = []
        for rid in s["extra_material_refs"]:
            m, cat = material(d, rid)
            if m is None:
                continue
            nm = _copy.deepcopy(m)
            nm["id"] = uid(f"CS{cat[:2]}", i)
            d["materials"][cat].append(nm)
            refs.append(nm["id"])
        s["extra_material_refs"] = refs
        new_segs.append(s)
        tl += s["target_timerange"]["duration"]

    vt["segments"] = new_segs
    d["duration"] = tl
    return keeps, tl / US
