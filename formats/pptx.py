"""PPTX exporter.
"""
from __future__ import annotations

import logging
import os
from io import BytesIO
from typing import Any, Dict, List, Optional

import httpx
from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Inches, Pt as PptPt

from app.core.models import FileRef
from app.core.templates import TemplateRegistry
from formats.content import ContentValidationError, validate_slides
from formats.coerce import coerce
from storage.paths import new_export_folder, public_url, resolve_output_path

log = logging.getLogger(__name__)


# ── DOCX → PPTX slide conversion ──────────────────────────────────────────────


def _is_docx_blocks(items: list) -> bool:
    """Return True if *items* looks like a list of DOCX content blocks
    (dicts with a 'type' key) rather than PPTX slide dicts."""
    if not items:
        return False
    first = items[0]
    if not isinstance(first, dict):
        return False
    return "type" in first


def _docx_blocks_to_slides(blocks: list) -> list[dict]:
    """Convert DOCX content blocks into PPTX slide dicts.

    Rules:
    - heading level 1 / title / subtitle (first) → new slide
    - heading level 2+ → content line in current slide (bold marker)
    - paragraph → content line
    - list → one content line per item
    - table → one content line per row (cells joined by " | ")
    - plain string → content line

    If no current slide exists, a new one is created with an empty title.
    """
    slides: list[dict] = []
    current: dict | None = None

    def _ensure_slide() -> dict:
        nonlocal current
        if current is None:
            current = {"title": "", "content": []}
            slides.append(current)
        return current

    for block in blocks:
        if isinstance(block, str):
            s = _ensure_slide()
            s["content"].append(block)
            continue

        if not isinstance(block, dict):
            continue

        btype = block.get("type", "")

        if btype in ("title", "subtitle"):
            # Start a new slide
            current = {"title": str(block.get("text", "")), "content": []}
            slides.append(current)

        elif btype == "heading":
            level = block.get("level", 1)
            text = str(block.get("text", ""))
            if level <= 1:
                # New slide
                current = {"title": text, "content": []}
                slides.append(current)
            else:
                # Sub-heading in current slide
                s = _ensure_slide()
                s["content"].append(text)

        elif btype == "paragraph":
            s = _ensure_slide()
            s["content"].append(str(block.get("text", "")))

        elif btype == "list":
            s = _ensure_slide()
            for item in block.get("items", []):
                s["content"].append(f"• {item}")

        elif btype == "table":
            s = _ensure_slide()
            for row in block.get("data", []):
                s["content"].append(" | ".join(str(cell) for cell in row))

        else:
            # Unknown type — skip (already validated upstream)
            pass

    # Remove slides with empty title AND empty content
    slides = [s for s in slides if s["title"] or s["content"]]
    return slides


# ── Public API ────────────────────────────────────────────────────────────────


def export_pptx(slides: list[dict] | str, filename: str | None) -> FileRef:
    template_path = TemplateRegistry.get("pptx")

    # Defensive second line of guard (the MCP tool already validates):
    # recover JSON-serialized input, then fail loud on malformed slides
    # instead of rendering raw markup into the presentation.
    slides = coerce(slides)

    if isinstance(slides, str):
        slides = [{"title": "", "content": slides}]
    elif isinstance(slides, list) and _is_docx_blocks(slides):
        # Caller passed DOCX content blocks — convert to slides
        log.info("Converting %d DOCX blocks to PPTX slides", len(slides))
        slides = _docx_blocks_to_slides(slides)
    else:
        slides = validate_slides(slides)

    result = _create_presentation(
        slides_data=slides,
        filename=filename or "presentation.pptx",
        template_path=template_path,
    )

    return FileRef(
        path=result["path"],
        name=result["name"],
        url=result["url"],
    )


def _create_presentation(
    slides_data: List[Dict],
    filename: str,
    folder_path: Optional[str] = None,
    title: Optional[str] = None,
    template_path: str | None = None
) -> Dict[str, str]:
    """Create a PowerPoint presentation from structured slide data, optionally using a template.

    Supports:
    - Loading and reusing layouts from a template file (while clearing its slides)
    - Inserting images by query (via `image_query`) with positioning (`image_position`)
      and sizing (`image_size`)
    - Preserving template styling (font, bold, sizes) via run-level formatting
    - Fallback to default layouts if template fails

    :param slides_data: List of slide definitions. Each dict may contain:
            - `title` (str): Slide title
            - `content` (Union[str, List[str]]): Bullet points or paragraphs
            - `image_query` (Optional[str]): Query to search for an image
            - `image_position` (str): One of 'left', 'right', 'top', 'bottom' (default: 'right')
            - `image_size` (str): One of 'small', 'medium', 'large' (default: 'medium')
    :param filename: Output filename (e.g., "report.pptx")
    :param folder_path: Optional output folder. If None, auto-generated.
    :param title: Title for the cover slide (default: empty)
    :param template_path: Optional explicit path to a PPTX template file.

    :returns: dict with keys:
            - 'url': Publicly accessible link
            - 'path': Local filesystem path to saved .pptx
            - 'name': Safe filename (with extension)
    :raises OSError: If saving fails.
    """
    if folder_path is None:
        folder_path = new_export_folder()

    filepath, fname = resolve_output_path(folder_path, filename or "", "pptx")

    prs = None
    use_template = False
    title_layout = None
    content_layout = None

    active_template = template_path

    prs, use_template, title_layout, content_layout = _load_presentation_template(
        active_template, log
    )
    _add_title_slide(prs, title_layout, title, log)
    _add_content_slides(prs, slides_data, content_layout, use_template, log)

    # === Save and return ===
    try:
        prs.save(filepath)
        log.info("Saved presentation to: %s", filepath)
        if use_template:
            log.info("Template applied: %s", active_template)
        else:
            log.warning("No template used — default style applied")
    except Exception as e:
        log.error("Failed to save presentation: %s", e, exc_info=True)
        raise

    return {
        "url": public_url(folder_path, fname),
        "path": filepath,
        "name": fname,
    }


def _load_presentation_template(active_template, log):
    prs = None
    use_template = False
    title_layout = None
    content_layout = None
    if active_template and os.path.exists(active_template):
        try:
            log.info(f"Loading template: {active_template}")
            prs = Presentation(active_template)
            use_template = True
            layouts_by_name = {layout.name: layout for layout in prs.slide_layouts}
            TITLE_LAYOUT_NAME = 'Title Slide'
            CONTENT_LAYOUT_NAME = 'Slide 01'
            title_layout = layouts_by_name.get(TITLE_LAYOUT_NAME)
            content_layout = layouts_by_name.get(CONTENT_LAYOUT_NAME)
            if not title_layout:
                log.warning(f"Layout '{TITLE_LAYOUT_NAME}' not found, searching alternatives")
                for layout in prs.slide_layouts:
                    for ph in layout.placeholders:
                        try:
                            if ph.placeholder_format.type == PP_PLACEHOLDER.TITLE:
                                title_layout = layout
                                log.debug(f"Found title layout: {layout.name}")
                                break
                        except Exception:
                            pass
                    if title_layout:
                        break
            if not content_layout:
                alternative_names = ['Slide 02', 'Slide 03', 'Content']
                for alt_name in alternative_names:
                    if alt_name in layouts_by_name:
                        content_layout = layouts_by_name[alt_name]
                        log.info(f"Using alternative layout: '{alt_name}'")
                        break
            if not title_layout and prs.slide_layouts:
                title_layout = prs.slide_layouts[0]
                log.warning(f"Using first layout: '{title_layout.name}'")
            if not content_layout:
                if len(prs.slide_layouts) > 1:
                    content_layout = prs.slide_layouts[1]
                else:
                    content_layout = title_layout
                log.warning(f"Using default layout: '{content_layout.name}'")
            log.info(f"Using layouts: Title='{title_layout.name}', Content='{content_layout.name}'")
            slide_ids = [slide.slide_id for slide in prs.slides]
            for slide_id in reversed(slide_ids):
                for i, sldId in enumerate(prs.slides._sldIdLst):
                    slide_id_match = (
                        (hasattr(sldId, 'id') and int(sldId.id) == int(slide_id)) or
                        (hasattr(sldId, 'slideId') and int(sldId.slideId) == int(slide_id))
                    )
                    if slide_id_match:
                        if hasattr(sldId, 'rId') and sldId.rId:
                            prs.part.drop_rel(sldId.rId)
                        del prs.slides._sldIdLst[i]
                        break
            log.info(f"Cleared {len(slide_ids)} slides from template. "
                     f"Using layouts: Title='{title_layout.name}', Content='{content_layout.name}'")
        except Exception as e:
            log.error(f"Failed to process template '{active_template}': {e}", exc_info=True)
            use_template = False
            prs = None
    if not prs:
        log.info("Creating new presentation (no template)")
        prs = Presentation()
        title_layout = prs.slide_layouts[0]
        content_layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else title_layout
    return prs, use_template, title_layout, content_layout


def _add_title_slide(prs, title_layout, title, log):
    try:
        title_slide = prs.slides.add_slide(title_layout)
        if title_slide.shapes.title:
            title_slide.shapes.title.text = title or ""
            for p in title_slide.shapes.title.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = PptPt(32)
                    run.font.bold = True
        log.info(f"Created title slide: '{title or '(no title)'}'")
    except Exception as e:
        log.warning(f"Title slide fallback: {e}")
        title_slide = prs.slides.add_slide(prs.slide_layouts[0])
        if title_slide.shapes.title:
            title_slide.shapes.title.text = title or ""


def _add_content_slides(prs, slides_data, content_layout, use_template, log):
    EMU_PER_INCH = 914400
    slide_w_in = prs.slide_width / EMU_PER_INCH
    slide_h_in = prs.slide_height / EMU_PER_INCH
    PAGE_MARGIN = 0.5
    GUTTER = 0.3
    for i, slide_data in enumerate(slides_data):
        slide_title = slide_data.get("title", f"Slide {i + 1}")
        content_list = slide_data.get("content", [])
        if not isinstance(content_list, list):
            content_list = [content_list]
        log.info(f"Creating slide {i + 1}: '{slide_title}'")
        try:
            slide = prs.slides.add_slide(content_layout)
            if slide.shapes.title:
                slide.shapes.title.text = slide_title
                for p in slide.shapes.title.text_frame.paragraphs:
                    for run in p.runs:
                        run.font.size = PptPt(28 if use_template else 24)
                        run.font.bold = True
            picture_placeholder = None
            content_ph = None
            for shape in slide.placeholders:
                try:
                    ph_type = shape.placeholder_format.type
                    if ph_type == PP_PLACEHOLDER.PICTURE:
                        picture_placeholder = shape
                    elif ph_type == PP_PLACEHOLDER.BODY:
                        content_ph = shape
                except Exception:
                    pass
            title_bottom_in = 1.2
            if slide.shapes.title:
                try:
                    title_bottom_emu = slide.shapes.title.top + slide.shapes.title.height
                    title_bottom_in = max(title_bottom_emu / EMU_PER_INCH + 0.2, 1.2)
                except Exception:
                    pass
            content_left_in, content_top_in = PAGE_MARGIN, title_bottom_in
            content_width_in = slide_w_in - 2 * PAGE_MARGIN
            content_height_in = slide_h_in - title_bottom_in - PAGE_MARGIN
            image_query = slide_data.get("image_query")
            if image_query:
                image_url = search_image(log, image_query)
                if image_url:
                    log.debug(f"Found image for '{image_query}': {image_url}")
                    try:
                        img_data = download_bytes_sync(image_url, timeout=30)
                        img_stream = BytesIO(img_data)
                        if picture_placeholder:
                            try:
                                picture_placeholder.insert_picture(img_stream)
                                log.debug("Inserted image into PICTURE placeholder")
                            except Exception as e:
                                log.warning(f"Could not insert into placeholder: {e}")
                                picture_placeholder = None
                        if not picture_placeholder:
                            pos = slide_data.get("image_position", "right")
                            size = slide_data.get("image_size", "medium")
                            img_w_in, img_h_in = {
                                "small": (2.0, 1.5),
                                "large": (4.0, 3.0)
                            }.get(size, (3.0, 2.0))
                            if pos == "left":
                                img_left_in = PAGE_MARGIN
                                img_top_in = title_bottom_in
                                content_left_in = img_left_in + img_w_in + GUTTER
                                content_width_in = max(slide_w_in - PAGE_MARGIN - content_left_in, 2.5)
                            elif pos == "right":
                                img_left_in = slide_w_in - PAGE_MARGIN - img_w_in
                                img_top_in = title_bottom_in
                                content_width_in = max(img_left_in - GUTTER - PAGE_MARGIN, 2.5)
                            elif pos == "top":
                                img_left_in = (slide_w_in - img_w_in) / 2
                                img_top_in = title_bottom_in
                                content_top_in = img_top_in + img_h_in + GUTTER
                                content_height_in = max(slide_h_in - PAGE_MARGIN - content_top_in, 2.0)
                            elif pos == "bottom":
                                img_left_in = (slide_w_in - img_w_in) / 2
                                img_top_in = slide_h_in - PAGE_MARGIN - img_h_in
                                content_height_in = max(img_top_in - GUTTER - title_bottom_in, 2.0)
                            else:
                                img_left_in = slide_w_in - PAGE_MARGIN - img_w_in
                                img_top_in = title_bottom_in
                                content_width_in = max(img_left_in - GUTTER - PAGE_MARGIN, 2.5)
                            slide.shapes.add_picture(
                                img_stream,
                                Inches(img_left_in),
                                Inches(img_top_in),
                                width=Inches(img_w_in),
                                height=Inches(img_h_in)
                            )
                            log.debug(f"Inserted image at {pos}, {size}")
                    except Exception as e:
                        log.warning(f"Image insertion failed: {e}")
            if content_ph is None:
                content_ph = slide.shapes.add_textbox(
                    Inches(content_left_in),
                    Inches(content_top_in),
                    Inches(content_width_in),
                    Inches(content_height_in)
                )
            tf = content_ph.text_frame
            tf.clear()
            tf.word_wrap = True
            tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            chars_per_inch = 9.5
            lines_per_inch = 1.6
            est_capacity = int(
                max(content_width_in, 0.1) * chars_per_inch *
                max(content_height_in, 0.1) * lines_per_inch
            )
            font_size = dynamic_font_size(
                content_list,
                max_chars=max(est_capacity, 120),
                base_size=16,
                min_size=10
            )
            for idx, line in enumerate(content_list):
                p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
                run = p.add_run()
                run.text = str(line) if line is not None else ""
                run.font.size = font_size
                p.space_after = PptPt(6)
        except Exception as e:
            log.error(f"Failed to create slide {i + 1} ('{slide_title}'): {e}", exc_info=True)
            continue


def dynamic_font_size(content_list, max_chars=400, base_size=28, min_size=12):
    """Pick a font size that scales down when a slide has a lot of text.

    :param content_list: list of text lines for a slide.
    :param max_chars: total character budget before shrinking starts.
    :param base_size: font size (pt) when content is short.
    :param min_size: floor font size (pt).
    :return: a ``pptx.util.Pt`` value.
    """
    total_chars = sum(len(str(line)) for line in content_list)
    ratio = total_chars / max_chars if max_chars > 0 else 1
    if ratio <= 1:
        return PptPt(base_size)
    new_size = int(base_size / ratio)
    return PptPt(max(min_size, new_size))


def search_image(log, query: str) -> Optional[str]:
    """Search for an image by a textual query.

    Only Unsplash is supported (requires ``UNSPLASH_ACCESS_KEY``). When no
    source is configured the query is skipped and ``None`` is returned —
    image insertion is best-effort and must never break the export.

    :param log: Logger instance.
    :param query: Search query.
    :return: Public image URL, or ``None`` when unavailable.
    """
    api_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not api_key:
        log.debug("UNSPLASH_ACCESS_KEY not set — image query '%s' skipped", query)
        return None
    url = "https://api.unsplash.com/search/photos"
    params = {"query": query, "per_page": 1, "orientation": "landscape"}
    headers = {"Authorization": f"Client-ID {api_key}"}
    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        if results:
            return results[0]["urls"]["regular"]
    except Exception as e:
        log.warning("Image search for '%s' failed: %s", query, e)
    return None


def download_bytes_sync(url: str, timeout: float = 30.0) -> bytes:
    """Download *url* and return the response body as bytes (synchronous)."""
    resp = httpx.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content
