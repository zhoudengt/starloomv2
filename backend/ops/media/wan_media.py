"""
阿里云 DashScope 万相：文生图（默认）与可选文生视频。
wan2.6-t2i 必须使用 multimodal-generation/generation HTTP（见阿里云文生图 V2 文档），
勿用旧版 ImageSynthesis 的 text2image 路径，否则会 400 url error。
"""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from PIL import Image, ImageDraw, ImageFont

from ops.config import OpsSettings, get_ops_settings
from ops.visual.bundle import BRAND


def _download(url: str, dest: Path, timeout: float = 120.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)


def _load_wan_overlay_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size, index=0)
        except OSError:
            continue
    return ImageFont.load_default()


def _compress_and_overlay(dest: Path, overlay_text: str = "", max_kb: int = 500) -> Path:
    """Read downloaded image, optional bottom-third overlay, save JPEG ≤ max_kb (try q=80 then 60)."""
    img = Image.open(dest).convert("RGBA")
    w, h = img.size
    text = (overlay_text or "").strip()
    if text:
        draw = ImageDraw.Draw(img)
        font_size = max(22, min(int(w / 10), 120))
        font = _load_wan_overlay_font(font_size)
        bar_y0 = int(h * 2 / 3)
        draw.rectangle([0, bar_y0, w, h], fill=(0, 0, 0, 200))
        cx = w // 2
        cy = bar_y0 + (h - bar_y0) // 2
        draw.text((cx, cy), text, fill=(255, 255, 255, 255), font=font, anchor="mm")

    rgb = Image.new("RGB", img.size, (0, 0, 0))
    rgb.paste(img, mask=img.split()[3])

    jpg_path = dest.with_suffix(".jpg")
    max_bytes = max_kb * 1024

    def _save_jpeg(quality: int) -> None:
        rgb.save(jpg_path, "JPEG", quality=quality, optimize=True)

    _save_jpeg(80)
    if jpg_path.stat().st_size > max_bytes:
        _save_jpeg(60)

    if dest.resolve() != jpg_path.resolve() and dest.exists():
        dest.unlink()

    return jpg_path


def _api_key(settings: Any, ops: OpsSettings) -> str:
    raw = (getattr(ops, "dashscope_api_key", None) or "").strip()
    if raw:
        return raw
    return (getattr(settings, "bailian_api_key", None) or "").strip()


def _is_wan26_t2i_multimodal(model: str) -> bool:
    m = (model or "").strip().lower()
    return m == "wan2.6-t2i" or (m.startswith("wan2.6") and "t2i" in m)


def _extract_image_url_multimodal(data: Dict[str, Any]) -> Optional[str]:
    out = data.get("output") or {}
    choices = out.get("choices") or []
    if not choices:
        return None
    msg = (choices[0].get("message") or {})
    for item in msg.get("content") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "image" and item.get("image"):
            return str(item["image"])
        if item.get("image"):
            return str(item["image"])
    return None


def _generate_wan26_t2i_http(
    *,
    api_key: str,
    model: str,
    prompt: str,
    size: str,
    base_url: str,
    workspace: Optional[str],
    negative_prompt: str = "",
) -> Dict[str, Any]:
    """文生图 V2：POST .../services/aigc/multimodal-generation/generation"""
    url = base_url.rstrip("/") + "/services/aigc/multimodal-generation/generation"
    text = (prompt or "")[:2100]
    payload: Dict[str, Any] = {
        "model": model,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": text}],
                }
            ]
        },
        "parameters": {
            "prompt_extend": True,
            "watermark": False,
            "n": 1,
            "negative_prompt": negative_prompt or "",
            "size": size,
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if workspace:
        headers["X-DashScope-WorkSpace"] = workspace

    try:
        with httpx.Client(timeout=180.0) as client:
            r = client.post(url, headers=headers, json=payload)
            data = r.json() if r.content else {}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    if r.status_code != 200:
        msg = data.get("message") or data.get("code") or r.text
        return {"ok": False, "error": f"HTTP {r.status_code}: {msg}"}

    # 成功响应含 output.choices；错误响应常为顶层 code/message
    if data.get("code") and not data.get("output"):
        return {"ok": False, "error": f"{data.get('code')}: {data.get('message', data)}"}

    img_url = _extract_image_url_multimodal(data)
    if not img_url:
        return {"ok": False, "error": f"no image url in response: {json.dumps(data, ensure_ascii=False)[:500]}"}
    return {"ok": True, "url": img_url}


def _generate_one_image_legacy(
    *,
    api_key: str,
    model: str,
    prompt: str,
    size: str,
    workspace: Optional[str],
) -> Dict[str, Any]:
    """旧版 ImageSynthesis：wanx-v1、wan2.2-t2i-flash / wan2.2-t2i-plus（sync_call）等。"""
    from dashscope import ImageSynthesis

    m = (model or "").lower()
    try:
        if m in ("wan2.2-t2i-flash", "wan2.2-t2i-plus"):
            done = ImageSynthesis.sync_call(
                model=model,
                prompt=prompt,
                api_key=api_key,
                workspace=workspace or None,
                size=size,
                n=1,
            )
        else:
            rsp = ImageSynthesis.async_call(
                model=model,
                prompt=prompt,
                api_key=api_key,
                workspace=workspace or None,
                size=size,
                n=1,
            )
            done = ImageSynthesis.wait(rsp, api_key=api_key, workspace=workspace or None)
    except Exception as e:
        return {"ok": False, "error": str(e)}

    if done.status_code != 200 or not done.output or not done.output.results:
        msg = getattr(done, "message", None) or getattr(done, "code", None) or "unknown"
        return {"ok": False, "error": str(msg)}

    url = done.output.results[0].url
    return {"ok": True, "url": url}


def _generate_one_image(
    *,
    api_key: str,
    model: str,
    prompt: str,
    size: str,
    base_http: str,
    workspace: Optional[str],
) -> Dict[str, Any]:
    if _is_wan26_t2i_multimodal(model):
        return _generate_wan26_t2i_http(
            api_key=api_key,
            model=model,
            prompt=prompt,
            size=size,
            base_url=base_http,
            workspace=workspace,
        )
    return _generate_one_image_legacy(
        api_key=api_key,
        model=model,
        prompt=prompt,
        size=size,
        workspace=workspace,
    )


def _generate_one_image_with_retries(
    *,
    api_key: str,
    model: str,
    prompt: str,
    size: str,
    base_http: str,
    workspace: Optional[str],
    retries: int,
) -> Dict[str, Any]:
    last: Dict[str, Any] = {"ok": False, "error": "unknown"}
    for attempt in range(retries):
        last = _generate_one_image(
            api_key=api_key,
            model=model,
            prompt=prompt,
            size=size,
            base_http=base_http,
            workspace=workspace,
        )
        if last.get("ok"):
            return last
        err = str(last.get("error", ""))
        if "429" in err or "Throttling" in err or "RateQuota" in err:
            time.sleep(5.0 * (attempt + 1))
            continue
        break
    return last


def _safe_filename_slug(slug: str, max_len: int = 120) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff\-]+", "-", (slug or "").strip("-"))
    return (s or "article")[:max_len]


def generate_h5_article_cover(
    settings: Any,
    *,
    slug: str,
    title: str,
    category: str,
    publish_date: date,
) -> Dict[str, Any]:
    """万相文生图保存到 `frontend/public/generated/articles/{date}/`，返回可给前端的 web 路径。"""
    ops = get_ops_settings()
    out: Dict[str, Any] = {"ok": False, "web_path": None, "error": None}
    if not ops.wan_image_enabled:
        out["error"] = "wan_image_disabled"
        return out
    key = _api_key(settings, ops)
    if not key:
        out["error"] = "no_dashscope_api_key"
        return out
    ws = (ops.dashscope_workspace or "").strip() or None
    base_http = (ops.dashscope_http_base or "https://dashscope.aliyuncs.com/api/v1").rstrip("/")
    cat_mood = {
        "career": "职场与成长",
        "wealth": "财富与消费",
        "relationship": "人际与亲密关系",
        "energy": "情绪与身心休息",
        "general": "星座与自我探索",
    }.get((category or "").strip(), "星座主题")
    safe_title = (title or "")[:80]
    prompt = (
        f"竖版移动端封面插画，占星生活方式 App，主题：{safe_title}。"
        f"氛围：{cat_mood}。视觉：深紫夜空、细碎星光、少量金色点缀，高级简洁，画面中无文字、无水印、无 logo。"
    )
    meta = _generate_one_image_with_retries(
        api_key=key,
        model=ops.wan_image_model,
        prompt=prompt,
        size=ops.wan_image_size,
        base_http=base_http,
        workspace=ws,
        retries=ops.wan_image_retries,
    )
    if not meta.get("ok") or not meta.get("url"):
        out["error"] = str(meta.get("error") or "generation_failed")
        return out
    url = str(meta["url"])
    lu = url.lower()
    ext = ".png"
    if ".webp" in lu:
        ext = ".webp"
    elif ".jpg" in lu or "jpeg" in lu:
        ext = ".jpg"
    repo_root = Path(__file__).resolve().parents[3]
    rel_dir = Path("generated") / "articles" / publish_date.isoformat()
    dest_dir = repo_root / "frontend" / "public" / rel_dir
    fname = f"{_safe_filename_slug(slug)}{ext}"
    dest = dest_dir / fname
    try:
        _download(url, dest)
    except Exception as e:
        out["error"] = f"download_failed: {e}"
        return out
    web_path = f"/{rel_dir.as_posix()}/{fname}"
    out["ok"] = True
    out["web_path"] = web_path
    return out


def _generate_one_video(
    *,
    api_key: str,
    model: str,
    prompt: str,
    size: str,
    duration: int,
    workspace: Optional[str],
) -> Dict[str, Any]:
    from dashscope import VideoSynthesis

    try:
        rsp = VideoSynthesis.async_call(
            model=model,
            prompt=prompt,
            api_key=api_key,
            workspace=workspace or None,
            duration=duration,
            size=size,
        )
        done = VideoSynthesis.wait(rsp, api_key=api_key, workspace=workspace or None)
    except Exception as e:
        return {"ok": False, "error": str(e)}

    if done.status_code != 200 or not done.output:
        msg = getattr(done, "message", None) or getattr(done, "code", None) or "unknown"
        return {"ok": False, "error": str(msg)}

    vurl = getattr(done.output, "video_url", None) or ""
    return {
        "ok": bool(vurl),
        "url": vurl,
        "task_id": getattr(done.output, "task_id", None),
        "error": None if vurl else "empty video_url",
    }


def _video_prompt_from_bundle(video_spec: Dict[str, Any], title_hint: str) -> str:
    beats = (video_spec.get("15s") or {}).get("beats") or []
    parts = [f"Theme: StarLoom zodiac content. {title_hint}."]
    parts.append(f"Visual style: {BRAND['bg']}, colors {BRAND['primary']} and {BRAND['accent']}.")
    for b in beats[:3]:
        parts.append(
            f"Shot: {b.get('visual', '')}. Voiceover mood: {b.get('voice', '')}. B-roll: {b.get('b_roll_prompt', '')}."
        )
    parts.append("Vertical 9:16 mobile short video, smooth motion, no readable text in frame, cinematic.")
    return " ".join(parts)


def run_wan_media_bundle(
    settings: Any,
    out_dir: Path,
    carousel: Dict[str, Any],
    video_spec: Dict[str, Any],
    *,
    title_hint: str,
    video_enabled_override: Optional[bool] = None,
    carousel_covers: list[dict] | None = None,
) -> Dict[str, Any]:
    ops = get_ops_settings()
    key = _api_key(settings, ops)
    ws = (ops.dashscope_workspace or "").strip() or None
    base_http = (ops.dashscope_http_base or "https://dashscope.aliyuncs.com/api/v1").rstrip("/")

    ve = bool(ops.wan_video_enabled) if video_enabled_override is None else bool(video_enabled_override)

    out: Dict[str, Any] = {
        "image_enabled": bool(ops.wan_image_enabled),
        "video_enabled": ve,
        "image_model": ops.wan_image_model,
        "video_model": ops.wan_video_model,
        "images": [],
        "carousel_cover_images": [],
        "video": None,
        "wan26_multimodal_http": _is_wan26_t2i_multimodal(ops.wan_image_model),
    }

    if not key:
        out["error"] = "BAILIAN_API_KEY（或 OPS_DASHSCOPE_API_KEY）未配置"
        return out

    if ops.wan_image_enabled:
        pages = carousel.get("pages") or []
        for i, p in enumerate(pages):
            if i > 0 and ops.wan_image_sleep_sec > 0:
                time.sleep(ops.wan_image_sleep_sec)
            prompt = p.get("image_prompt") or ""
            if not prompt.strip():
                continue
            dl_rel = f"media/images/douyin_{i+1:02d}.png"
            dest = out_dir / dl_rel
            overlay = (p.get("overlay_text") or "").strip()
            meta = _generate_one_image_with_retries(
                api_key=key,
                model=ops.wan_image_model,
                prompt=prompt,
                size=ops.wan_image_size,
                base_http=base_http,
                workspace=ws,
                retries=ops.wan_image_retries,
            )
            entry: Dict[str, Any] = {
                "page": p.get("page", i + 1),
                "prompt_excerpt": prompt[:200],
                "model": ops.wan_image_model,
            }
            if meta.get("ok") and meta.get("url"):
                try:
                    _download(str(meta["url"]), dest)
                    jpg_path = _compress_and_overlay(
                        dest,
                        overlay_text=overlay,
                        max_kb=int(ops.wan_image_max_kb),
                    )
                    rel_jpg = jpg_path.relative_to(out_dir).as_posix()
                    entry["remote_url"] = meta["url"]
                    entry["local_file"] = rel_jpg
                    entry["ok"] = True
                except Exception as e:
                    entry["ok"] = False
                    entry["error"] = f"download failed: {e}"
                    entry["remote_url"] = meta.get("url")
            else:
                entry["ok"] = False
                entry["error"] = meta.get("error", "generation failed")
            out["images"].append(entry)

        covers_list = carousel_covers or []
        for i, c in enumerate(covers_list):
            if i > 0 and ops.wan_image_sleep_sec > 0:
                time.sleep(ops.wan_image_sleep_sec)
            prompt = c.get("image_prompt") or ""
            if not prompt.strip():
                continue
            dl_rel = f"media/images/carousel_cover_{i+1:02d}.png"
            dest = out_dir / dl_rel
            meta = _generate_one_image_with_retries(
                api_key=key,
                model=ops.wan_image_model,
                prompt=prompt,
                size=ops.wan_image_size,
                base_http=base_http,
                workspace=ws,
                retries=ops.wan_image_retries,
            )
            cent: Dict[str, Any] = {
                "index": c.get("index", i),
                "prompt_excerpt": prompt[:200],
                "model": ops.wan_image_model,
            }
            if meta.get("ok") and meta.get("url"):
                try:
                    _download(str(meta["url"]), dest)
                    jpg_path = _compress_and_overlay(
                        dest,
                        overlay_text="",
                        max_kb=int(ops.wan_image_max_kb),
                    )
                    rel_jpg = jpg_path.relative_to(out_dir).as_posix()
                    cent["remote_url"] = meta["url"]
                    cent["local_file"] = rel_jpg
                    cent["ok"] = True
                except Exception as e:
                    cent["ok"] = False
                    cent["error"] = f"download failed: {e}"
                    cent["remote_url"] = meta.get("url")
            else:
                cent["ok"] = False
                cent["error"] = meta.get("error", "generation failed")
            out["carousel_cover_images"].append(cent)

    if ve:
        vprompt = _video_prompt_from_bundle(video_spec, title_hint)
        rel_v = "media/videos/clip.mp4"
        dest_v = out_dir / rel_v
        vm = _generate_one_video(
            api_key=key,
            model=ops.wan_video_model,
            prompt=vprompt,
            size=ops.wan_video_size,
            duration=ops.wan_video_duration_sec,
            workspace=ws,
        )
        vent: Dict[str, Any] = {
            "model": ops.wan_video_model,
            "prompt_excerpt": vprompt[:300],
            "ok": False,
        }
        if vm.get("ok") and vm.get("url"):
            try:
                _download(str(vm["url"]), dest_v)
                vent["ok"] = True
                vent["remote_url"] = vm["url"]
                vent["local_file"] = rel_v.replace("\\", "/")
            except Exception as e:
                vent["error"] = f"download failed: {e}"
                vent["remote_url"] = vm.get("url")
        else:
            vent["error"] = vm.get("error", "video generation failed")
        out["video"] = vent

    return out


def merge_wan_media_into_manifest(out_dir: Path, wan_media: Dict[str, Any]) -> None:
    mpath = out_dir / "manifest.json"
    if not mpath.exists():
        return
    data = json.loads(mpath.read_text(encoding="utf-8"))
    data["wan_media"] = wan_media
    mpath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
