"""파이널컷 FCPXML 생성기 — 실측으로 확인한 요구사항을 전부 만족시킨다.

파이널컷이 임포트를 거부하는 조건 (전부 실제로 겪음):
  1. <effect> 에 uid 속성이 없으면 DTD 위반으로 거부
  2. 모든 시간값이 프레임 경계(frameDuration 의 정수배)에 없으면 거부
  3. 같은 lane 의 연결 클립이 겹치면 안 됨
  4. 자막 텍스트는 <text><text-style> 구조여야 한다
     (<param name="Text"> 형식은 DTD 는 통과하나 화면에 안 나옴)
"""
from fractions import Fraction
import os, re, urllib.parse, xml.etree.ElementTree as ET
import subprocess, json

BASIC_TITLE_UID = (".../Titles.localized/Bumper:Opener.localized/"
                   "Basic Title.localized/Basic Title.moti")


class FCPXML:
    def __init__(self, width=1080, height=1920, fps=Fraction(30000, 1001),
                 project="Claude 자동편집", event="Claude 자동편집"):
        self.w, self.h = width, height
        self.fd = 1 / fps                       # 한 프레임 길이(초)
        self.project, self.event = project, event
        self._rid = 0
        self.assets = []                        # (id, path, dur, w, h, fd)
        self.clips = []                         # (asset_id, name, start, dur)
        self.titles = []                        # (text, offset, dur, style)
        self.overlays = []
        self.audios = []
        self.effects = []

    # ── 시간 유틸 ───────────────────────────────────────────
    def snap(self, sec, min_one=False):
        """초 → 프레임 경계에 맞춘 Fraction. 안 맞추면 파이널컷이 거부한다."""
        n = round(Fraction(sec).limit_denominator(10**6) / self.fd)
        if min_one and n < 1:
            n = 1
        return n * self.fd

    @staticmethod
    def t(f):
        f = Fraction(f)
        return f"{f.numerator}/{f.denominator}s" if f.denominator != 1 else f"{f.numerator}s"

    def _id(self, p="r"):
        self._rid += 1
        return f"{p}{self._rid}"

    # ── 구성 ────────────────────────────────────────────────
    def add_media(self, path):
        """미디어를 등록하고 asset id 반환. ffprobe 로 실제 정보를 읽는다."""
        path = os.path.realpath(path)
        info = json.loads(subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format",
             "-of", "json", path], capture_output=True, text=True).stdout)
        v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
        a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
        dur = Fraction(info["format"]["duration"]).limit_denominator(10**6)
        if v is None:                                  # 오디오 전용 (배경음악 등)
            src_fd = self.fd
            w = h = 0
        else:
            num, den = (int(x) for x in v["r_frame_rate"].split("/"))
            src_fd = Fraction(den, num)
            w, h = int(v["width"]), int(v["height"])
            if v.get("side_data_list"):                # 회전 플래그 → 표시 크기
                for sd in v["side_data_list"]:
                    if abs(int(sd.get("rotation", 0))) in (90, 270):
                        w, h = h, w
        dur = round(dur / src_fd) * src_fd             # 소스 프레임 경계로
        aid = self._id("a")
        self.assets.append(dict(id=aid, path=path, dur=dur, w=w, h=h, fd=src_fd,
                                audio=a is not None,
                                ch=int(a["channels"]) if a else 0,
                                rate=int(a["sample_rate"]) if a else 0))
        return aid

    def add_clip(self, asset_id, start_sec, dur_sec, name=None,
                 speed=1.0, zoom=None, transition_after=None):
        """speed: 2.0 = 2배속 / zoom: (시작배율, 끝배율) 키프레임 확대
        transition_after: 이 클립 뒤에 넣을 전환 길이(초)"""
        self.clips.append(dict(asset=asset_id, name=name or "clip",
                               start=self.snap(start_sec),
                               dur=self.snap(dur_sec / speed, min_one=True),
                               src_dur=self.snap(dur_sec, min_one=True),
                               speed=speed, zoom=zoom, trans=transition_after))

    def add_overlay(self, asset_id, start_sec, dur_sec, name="overlay",
                    src_start=0, lane=1, scale=1.0):
        """오버레이 영상(알파 MOV 등)을 위 레인에 얹는다."""
        self.overlays.append(dict(asset=asset_id, name=name, lane=lane,
                                  off=self.snap(start_sec),
                                  dur=self.snap(dur_sec, min_one=True),
                                  start=self.snap(src_start), scale=scale))

    def add_audio(self, asset_id, start_sec, dur_sec, name="audio",
                  volume_db=None, lane=-1, role="music"):
        """배경음악 등 오디오를 아래 레인에 붙인다."""
        self.audios.append(dict(asset=asset_id, name=name, lane=lane, role=role,
                                off=self.snap(start_sec),
                                dur=self.snap(dur_sec, min_one=True),
                                vol=volume_db))

    @staticmethod
    def wrap(text, per_line):
        """어절 단위 줄바꿈. 세로 영상은 폭이 좁아 안 하면 좌우가 잘린다."""
        if per_line <= 0 or len(text) <= per_line:
            return text
        out, cur = [], ""
        for w in text.split():
            if cur and len(cur) + 1 + len(w) > per_line:
                out.append(cur); cur = w
            else:
                cur = f"{cur} {w}".strip()
        if cur:
            out.append(cur)
        return "\n".join(out)

    def add_title(self, text, start_sec, dur_sec, size=None,
                  color="1 1 1 1", stroke=None, stroke_w=3.0,
                  y=None, per_line=None, font="Apple SD Gothic Neo", face="Bold"):
        """size/y/per_line 을 생략하면 캔버스 비율에 맞춰 자동으로 정한다.

        위치는 템플릿 내부 param 이 아니라 <adjust-transform> 으로 준다.
        (param key 는 템플릿마다 달라 추측하면 안 된다)
        """
        vertical = self.h > self.w
        if size is None:
            size = round(self.w * 0.045)          # 1080 폭 → 49
        if per_line is None:
            per_line = 13 if vertical else 20
        if y is None:
            y = -round(self.h * 0.36)             # 원하는 픽셀 오프셋 (1920 → -691)
        self.titles.append(dict(text=self.wrap(text, per_line), off=self.snap(start_sec),
                                dur=self.snap(dur_sec, min_one=True),
                                size=size, color=color, font=font, face=face,
                                stroke=stroke, sw=stroke_w, y=y))

    # ── 출력 ────────────────────────────────────────────────
    @staticmethod
    def safe_name(n):
        """파이널컷은 프로젝트/이벤트 이름을 폴더명으로 쓴다 → '/' 와 줄바꿈 금지."""
        return re.sub(r"[/\r\n:]", " ", n).strip() or "Untitled"

    def build(self, out_path):
        self.project = self.safe_name(self.project)
        self.event = self.safe_name(self.event)
        # 1) 자막 겹침 제거 — 같은 lane 에서 겹치면 거부된다
        ts = sorted(self.titles, key=lambda x: x["off"])
        for a, b in zip(ts, ts[1:]):
            if a["off"] + a["dur"] > b["off"]:
                a["dur"] = b["off"] - a["off"]
        ts = [x for x in ts if x["dur"] > 0]

        root = ET.Element("fcpxml", version="1.11")
        res = ET.SubElement(root, "resources")
        seq_fmt = self._id()
        ET.SubElement(res, "format", id=seq_fmt, name="FFVideoFormatRateUndefined",
                      frameDuration=self.t(self.fd), width=str(self.w),
                      height=str(self.h), colorSpace="1-1-1 (Rec. 709)")
        for a in self.assets:
            at = dict(id=a["id"], name=os.path.basename(a["path"]),
                      start="0s", duration=self.t(a["dur"]))
            if a["w"]:                                  # 영상이 있을 때만 format 생성
                afmt = self._id()
                ET.SubElement(res, "format", id=afmt, name="FFVideoFormatRateUndefined",
                              frameDuration=self.t(a["fd"]), width=str(a["w"]),
                              height=str(a["h"]), colorSpace="1-1-1 (Rec. 709)")
                at.update(hasVideo="1", videoSources="1", format=afmt)
            if a["audio"]:
                at.update(hasAudio="1", audioSources="1",
                          audioChannels=str(a["ch"]), audioRate=str(a["rate"]))
            ael = ET.SubElement(res, "asset", **at)
            ET.SubElement(ael, "media-rep", kind="original-media",
                          src="file://" + urllib.parse.quote(a["path"]))
        trans_eff = None
        if any(c.get("trans") for c in self.clips):
            trans_eff = self._id()
            ET.SubElement(res, "effect", id=trans_eff, name="Cross Dissolve",
                          uid="FFTransition_CrossDissolve")
        eff = None
        if ts:
            eff = self._id()
            ET.SubElement(res, "effect", id=eff, name="Basic Title",
                          uid=BASIC_TITLE_UID)     # ← 없으면 DTD 위반

        ev = ET.SubElement(root, "event", name=self.event)
        pr = ET.SubElement(ev, "project", name=self.project)
        total = sum(c["dur"] for c in self.clips)
        sq = ET.SubElement(pr, "sequence", format=seq_fmt,
                           duration=self.t(total), tcStart="0s", tcFormat="NDF")
        spine = ET.SubElement(sq, "spine")

        # 클립 배치.
        # DTD 순서 엄수: note? → conform-rate? → timeMap? → adjust-* → 앵커아이템 → ...
        # 자막·오버레이·오디오는 반드시 클립의 '자식'이어야 한다.
        # spine 의 형제로 두면 파이널컷이 조용히 버린다.
        off = Fraction(0)
        placed = []
        for c in self.clips:
            el = ET.SubElement(spine, "asset-clip", ref=c["asset"], name=c["name"],
                               offset=self.t(off), start=self.t(c["start"]),
                               duration=self.t(c["dur"]))
            # ① 속도 — timeMap (time=새 시간, value=원본 시간)
            if c.get("speed", 1.0) != 1.0:
                # ⚠️ timept 의 time 은 클립의 start 와 같은 시간계다.
                #    0 부터 시작하면 start 와 어긋나 "각각의 미디어가 없는
                #    유효하지 않은 편집입니다" 로 거부된다.
                tm = ET.SubElement(el, "timeMap")
                ET.SubElement(tm, "timept", time=self.t(c["start"]),
                              value=self.t(c["start"]), interp="smooth2")
                ET.SubElement(tm, "timept", time=self.t(c["start"] + c["dur"]),
                              value=self.t(c["start"] + c["src_dur"]), interp="smooth2")
            # ② 키프레임 확대 — adjust-transform 안의 param
            if c.get("zoom"):
                z0, z1 = c["zoom"]
                at = ET.SubElement(el, "adjust-transform")
                pm = ET.SubElement(at, "param", name="scale")
                ka = ET.SubElement(pm, "keyframeAnimation")
                # ⚠️ scale 파라미터는 interp/curve 속성을 받지 않는다.
                #    넣으면 "보간 속성을 지원하지 않아 무시됩니다" 로 키프레임 전체가 버려진다.
                ET.SubElement(ka, "keyframe", time="0s", value=f"{z0} {z0}")
                ET.SubElement(ka, "keyframe", time=self.t(c["dur"]), value=f"{z1} {z1}")
            placed.append((off, off + c["dur"], c["start"], el))
            off += c["dur"]

        first = placed[0][3] if placed else None

        # ③ 오버레이 (lane > 0) — 첫 클립에 앵커, offset 은 그 클립 시간계
        for i, o in enumerate(self.overlays):
            host = next((p for p in placed if p[0] <= o["off"] < p[1]), placed[0] if placed else None)
            if host is None:
                continue
            c_off, _, c_start, c_el = host
            ov = ET.SubElement(c_el, "asset-clip", ref=o["asset"], name=o["name"],
                               lane=str(o["lane"]),
                               offset=self.t(c_start + (o["off"] - c_off)),
                               start=self.t(o["start"]), duration=self.t(o["dur"]))
            if o["scale"] != 1.0:
                ET.SubElement(ov, "adjust-transform",
                              scale=f"{o['scale']} {o['scale']}")

        # ④ 자막 (lane 1)
        for i, x in enumerate(ts):
            if x["off"] >= total:
                continue
            if x["off"] + x["dur"] > total:
                x["dur"] = total - x["off"]
            host = next((p for p in placed if p[0] <= x["off"] < p[1]), placed[-1] if placed else None)
            if host is None:
                continue
            c_off, _, c_start, c_el = host
            ti = ET.SubElement(c_el, "title", ref=eff, lane="2",
                               offset=self.t(c_start + (x["off"] - c_off)),
                               name=x["text"][:40].replace("\n", " "),
                               duration=self.t(x["dur"]))
            txt = ET.SubElement(ti, "text")
            sid = f"ts{i+1}"
            ET.SubElement(txt, "text-style", ref=sid).text = x["text"]
            sd = ET.SubElement(ti, "text-style-def", id=sid)
            attrs = dict(font=x.get("font", "Helvetica"), fontSize=str(x["size"]),
                         fontFace=x.get("face", "Bold"), fontColor=x["color"],
                         alignment="center")
            if x.get("stroke"):
                attrs["strokeColor"] = x["stroke"]
                attrs["strokeWidth"] = str(x["sw"])
            ET.SubElement(sd, "text-style", **attrs)
            # position 은 픽셀이 아니다 — 값 × (높이÷100) = 픽셀
            pos_y = round(x["y"] / (self.h / 100), 4)
            ET.SubElement(ti, "adjust-transform", position=f"0 {pos_y}")

        # ⑤ 오디오 (lane < 0)
        for a in self.audios:
            host = next((p for p in placed if p[0] <= a["off"] < p[1]), placed[0] if placed else None)
            if host is None:
                continue
            c_off, _, c_start, c_el = host
            au = ET.SubElement(c_el, "audio", ref=a["asset"], name=a["name"],
                               lane=str(a["lane"]), role=a["role"],
                               offset=self.t(c_start + (a["off"] - c_off)),
                               start="0s", duration=self.t(a["dur"]))
            if a["vol"] is not None:
                ET.SubElement(au, "adjust-volume", amount=f"{a['vol']}dB")

        # ⑥ 전환 — 클립 사이. filter-video 를 생략하면 기본 크로스 디졸브.
        for idx, c in enumerate(self.clips):
            if not c.get("trans") or idx >= len(placed) - 1:
                continue
            # 전환은 양쪽 클립에서 여분 미디어(핸들)를 끌어온다.
            # 속도가 바뀐 클립은 시간 매핑 때문에 핸들 계산이 안 되고
            # "각각의 미디어가 없는 유효하지 않은 편집입니다" 로 거부된다.
            if c.get("speed", 1.0) != 1.0 or self.clips[idx + 1].get("speed", 1.0) != 1.0:
                print(f"  ⚠️ 전환 건너뜀: '{c['name']}' 주변에 속도 변경 클립이 있음")
                continue
            d = self.snap(c["trans"], min_one=True)
            edit = placed[idx][1]
            tr = ET.Element("transition", name="Cross Dissolve",
                            offset=self.t(edit - d / 2), duration=self.t(d))
            # filter-video 를 생략하면 회색 빈 껍데기만 생긴다
            ET.SubElement(tr, "filter-video", ref=trans_eff, name="Cross Dissolve")
            spine.insert(list(spine).index(placed[idx][3]) + 1, tr)

        ET.indent(root, space="    ")
        xml = ET.tostring(root, encoding="unicode")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + xml)
        return out_path
