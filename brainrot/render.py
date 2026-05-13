from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .captions import captions_to_srt
from .files import slugify
from .models import Caption


class RenderError(RuntimeError):
    pass


LOGO_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]

HIGHLIGHT_WORDS = {
    "AI",
    "BEHIND",
    "DARK",
    "DEAD",
    "DON'T",
    "FAKE",
    "HIDDEN",
    "MILLION",
    "MILLIONS",
    "MONEY",
    "NEVER",
    "NOT",
    "SCAM",
    "SECRET",
    "STOP",
    "WARNING",
}


@dataclass
class RenderStyle:
    name: str
    accent_color: str
    overlay_color: str
    overlay_alpha: float = 0.62
    font_size: int = 76
    logo_width: int = 150


RENDER_STYLES = {
    "default": RenderStyle("default", accent_color="#f6c945", overlay_color="#070707"),
    "scams": RenderStyle("scams", accent_color="#ff4747", overlay_color="#100606"),
    "business": RenderStyle("business", accent_color="#f4bd42", overlay_color="#0d0b07"),
    "ai": RenderStyle("ai", accent_color="#34d3ff", overlay_color="#061016"),
    "internet": RenderStyle("internet", accent_color="#ff5fd2", overlay_color="#110712"),
    "law": RenderStyle("law", accent_color="#7ab7ff", overlay_color="#070b12"),
    "money": RenderStyle("money", accent_color="#5ee28a", overlay_color="#061006"),
    "micro-horror": RenderStyle("micro-horror", accent_color="#ff3b58", overlay_color="#050507"),
    "sci-fi-ai": RenderStyle("sci-fi-ai", accent_color="#31e7ff", overlay_color="#051017"),
    "moral-dilemma": RenderStyle("moral-dilemma", accent_color="#ffd166", overlay_color="#0d0b08"),
    "workplace-drama": RenderStyle("workplace-drama", accent_color="#7ee787", overlay_color="#071008"),
    "relationship-drama": RenderStyle("relationship-drama", accent_color="#ff77b7", overlay_color="#120710"),
}


def write_srt_from_json(script: Dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    captions = [
        Caption(
            index=int(item["index"]),
            start=float(item["start"]),
            end=float(item["end"]),
            text=str(item["text"]),
        )
        for item in script.get("captions", [])
    ]
    path = out_dir / f"{slugify(script['title'])}.srt"
    path.write_text(captions_to_srt(captions), encoding="utf-8")
    return path


def write_ass_from_json(
    script: Dict[str, Any],
    out_dir: Path,
    style: RenderStyle,
    font_name: str = "Arial Black",
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    captions = [
        Caption(
            index=int(item["index"]),
            start=float(item["start"]),
            end=float(item["end"]),
            text=str(item["text"]),
        )
        for item in script.get("captions", [])
    ]
    path = out_dir / f"{slugify(script['title'])}.ass"
    path.write_text(captions_to_ass(captions, style=style, font_name=font_name), encoding="utf-8")
    return path


def write_caption_images_from_json(
    script: Dict[str, Any],
    out_dir: Path,
    style: RenderStyle,
    font_name: str = "Arial Black",
) -> List[Caption]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RenderError("Pillow is required for rendering captions. Install it with: pip install -e .") from exc

    captions = [
        Caption(
            index=int(item["index"]),
            start=float(item["start"]),
            end=float(item["end"]),
            text=str(item["text"]),
        )
        for item in script.get("captions", [])
    ]
    image_dir = out_dir / f"{slugify(script['title'])}-caption-images"
    image_dir.mkdir(parents=True, exist_ok=True)
    font = load_caption_font(ImageFont, font_name=font_name, size=style.font_size)

    for caption in captions:
        image = Image.new("RGBA", (1080, 960), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw_caption_text(draw, caption.text, font=font, style=style)
        caption.image_path = image_dir / f"{caption.index:03}.png"  # type: ignore[attr-defined]
        image.save(caption.image_path)  # type: ignore[attr-defined]

    return captions


def captions_to_ass(captions: List[Caption], style: RenderStyle, font_name: str) -> str:
    primary = ass_color("#ffffff")
    outline = ass_color("#000000")
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 960",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
        ),
        (
            f"Style: Default,{font_name},{style.font_size},{primary},{primary},{outline},&H7F000000,"
            "1,0,0,0,100,100,0,0,1,5,2,5,48,48,40,1"
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for caption in captions:
        text = highlight_caption(escape_ass_text(caption.text), accent_color=style.accent_color)
        lines.append(
            "Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\fad(90,90)\\an5\\pos(540,480)}}{text}".format(
                start=ass_timestamp(caption.start),
                end=ass_timestamp(caption.end),
                text=text,
            )
        )
    return "\n".join(lines) + "\n"


def render_short(
    script: Dict[str, Any],
    gameplay_path: Path,
    output_path: Path,
    audio_path: Optional[Path] = None,
    font_name: str = "Arial Black",
    render_template: str = "auto",
    logo_path: Optional[Path] = None,
    channel: Optional[str] = None,
    logo_dir: Path = Path("assets/logos"),
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError("ffmpeg is not installed. Install it with: brew install ffmpeg")

    if not gameplay_path.exists():
        raise RenderError(f"Gameplay file does not exist: {gameplay_path}")
    if audio_path and not audio_path.exists():
        raise RenderError(f"Audio file does not exist: {audio_path}")
    resolved_logo = resolve_logo_path(channel=channel, logo_path=logo_path, logo_dir=logo_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    style = style_for_script(script, render_template)
    captions = write_caption_images_from_json(script, output_path.parent, style=style, font_name=font_name)
    duration = float(script.get("estimated_seconds", 55.0))

    command = [
        ffmpeg,
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(gameplay_path),
    ]
    if audio_path:
        command.extend(["-i", str(audio_path)])
    logo_input_index = None
    if resolved_logo:
        logo_input_index = 2 if audio_path else 1
        command.extend(["-loop", "1", "-i", str(resolved_logo)])
    caption_input_start = 1 + (1 if audio_path else 0) + (1 if resolved_logo else 0)
    for caption in captions:
        command.extend(["-loop", "1", "-i", str(caption.image_path)])  # type: ignore[attr-defined]

    filter_complex = build_filter_complex(
        duration=duration,
        style=style,
        logo_input_index=logo_input_index,
        captions=captions,
        caption_input_start=caption_input_start,
    )

    command.extend(
        [
            "-t",
            str(duration),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
        ]
    )
    if audio_path:
        command.extend(["-map", "1:a", "-shortest"])
    else:
        command.append("-an")

    command.extend(
        [
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(result.stderr.strip() or "ffmpeg render failed")

    return output_path


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_filter_complex(
    duration: float,
    style: RenderStyle,
    logo_input_index: Optional[int],
    captions: List[Caption],
    caption_input_start: int,
) -> str:
    filters = [
        "[0:v]split=2[bgsrc][gamesrc]",
        (
            "[bgsrc]scale=1080:960:force_original_aspect_ratio=increase,"
            "crop=1080:960,boxblur=24:2,eq=brightness=-0.12:saturation=0.65[topbg]"
        ),
        f"color=c={style.overlay_color}@{style.overlay_alpha}:s=1080x960:d={duration},format=rgba[shade]",
        "[topbg][shade]overlay=0:0[topshade]",
    ]
    top_label = "topshade"
    if logo_input_index is not None:
        filters.extend(
            [
                (
                    f"[{logo_input_index}:v]scale={style.logo_width}:{style.logo_width}:"
                    "force_original_aspect_ratio=decrease[logo]"
                ),
                f"[{top_label}][logo]overlay=40:36:format=auto[toplogo]",
            ]
        )
        top_label = "toplogo"

    for index, caption in enumerate(captions):
        caption_input = caption_input_start + index
        image_label = f"capimg{index}"
        output_label = f"capout{index}"
        filters.append(f"[{caption_input}:v]format=rgba[{image_label}]")
        filters.append(
            f"[{top_label}][{image_label}]overlay=0:0:enable='gte(t\\,{caption.start:.2f})*lt(t\\,{caption.end:.2f})'[{output_label}]"
        )
        top_label = output_label

    filters.extend(
        [
            (
                "[gamesrc]scale=1160:1032:force_original_aspect_ratio=increase,"
                "crop=1080:960[game]"
            ),
            f"[{top_label}][game]vstack=inputs=2[v]",
        ]
    )
    return ";".join(filters)


def style_for_script(script: Dict[str, Any], render_template: str = "auto") -> RenderStyle:
    if render_template != "auto":
        return RENDER_STYLES.get(render_template, RENDER_STYLES["default"])

    fiction_genre = str(script.get("fiction_genre", "")).strip()
    if fiction_genre in RENDER_STYLES:
        return RENDER_STYLES[fiction_genre]

    niche = str(script.get("niche", "")).strip()
    return RENDER_STYLES.get(niche, RENDER_STYLES["default"])


def resolve_logo_path(
    channel: Optional[str] = None,
    logo_path: Optional[Path] = None,
    logo_dir: Path = Path("assets/logos"),
) -> Optional[Path]:
    if logo_path:
        if not logo_path.exists():
            raise RenderError(f"Logo file does not exist: {logo_path}")
        return logo_path

    if not channel:
        return None

    channel_dir = logo_dir / channel
    if not channel_dir.exists():
        return None

    for extension in LOGO_EXTENSIONS:
        preferred = channel_dir / f"logo{extension}"
        if preferred.exists():
            return preferred

    candidates = [
        path for path in channel_dir.iterdir() if path.is_file() and path.suffix.lower() in LOGO_EXTENSIONS
    ]
    candidates.sort()
    return candidates[0] if candidates else None


def ass_timestamp(seconds: float) -> str:
    centiseconds = int(round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, centiseconds = divmod(remainder, 100)
    return f"{hours:d}:{minutes:02}:{secs:02}.{centiseconds:02}"


def ass_color(hex_color: str) -> str:
    clean = hex_color.strip().lstrip("#")
    if len(clean) != 6:
        clean = "ffffff"
    red = clean[0:2]
    green = clean[2:4]
    blue = clean[4:6]
    return f"&H00{blue}{green}{red}".upper()


def escape_ass_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def highlight_caption(text: str, accent_color: str) -> str:
    accent = ass_override_color(accent_color)
    white = ass_override_color("#ffffff")
    words = text.split()
    highlighted = 0
    result = []
    for word in words:
        clean = "".join(character for character in word if character.isalnum() or character == "'").upper()
        if clean in HIGHLIGHT_WORDS and highlighted < 2:
            result.append(f"{{\\1c{accent}}}{word}{{\\1c{white}}}")
            highlighted += 1
        else:
            result.append(word)
    return " ".join(result)


def ass_override_color(hex_color: str) -> str:
    clean = hex_color.strip().lstrip("#")
    if len(clean) != 6:
        clean = "ffffff"
    red = clean[0:2]
    green = clean[2:4]
    blue = clean[4:6]
    return f"&H{blue}{green}{red}&".upper()


def load_caption_font(ImageFont, font_name: str, size: int):
    candidates = [
        font_name,
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_caption_text(draw, text: str, font, style: RenderStyle) -> None:
    lines = wrap_caption_words(text.split(), max_chars=12)
    line_height = int(style.font_size * 1.18)
    start_y = 480 - (len(lines) * line_height) // 2
    space_width = int(style.font_size * 0.72)
    for line_index, line_words in enumerate(lines):
        runs = caption_runs(line_words, style.accent_color)
        total_width = sum(text_width(draw, word, font=font) for word, _ in runs)
        total_width += max(0, len(runs) - 1) * space_width
        x = (1080 - total_width) / 2
        y = start_y + line_index * line_height
        for word, color in runs:
            draw.text(
                (x, y),
                word,
                font=font,
                fill=color,
                stroke_width=5,
                stroke_fill=(0, 0, 0, 235),
            )
            x += text_width(draw, word, font=font) + space_width


def wrap_caption_words(words: List[str], max_chars: int) -> List[List[str]]:
    lines: List[List[str]] = []
    current: List[str] = []
    current_length = 0
    for word in words:
        next_length = current_length + len(word) + (1 if current else 0)
        if current and next_length > max_chars:
            lines.append(current)
            current = [word]
            current_length = len(word)
        else:
            current.append(word)
            current_length = next_length
    if current:
        lines.append(current)
    return lines[:3]


def caption_runs(words: List[str], accent_color: str):
    accent = rgb_tuple(accent_color)
    white = (255, 255, 255, 255)
    highlighted = 0
    runs = []
    for word in words:
        clean = "".join(character for character in word if character.isalnum() or character == "'").upper()
        if clean in HIGHLIGHT_WORDS and highlighted < 2:
            runs.append((word, accent))
            highlighted += 1
        else:
            runs.append((word, white))
    return runs


def rgb_tuple(hex_color: str):
    clean = hex_color.strip().lstrip("#")
    if len(clean) != 6:
        clean = "ffffff"
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16), 255)


def text_width(draw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=5)
    return bbox[2] - bbox[0]
