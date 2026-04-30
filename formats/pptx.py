"""PPTX exporter.
"""
from __future__ import annotations

from app.core.models import FileRef
from app.core.templates import TemplateRegistry

template = TemplateRegistry.get("pptx")  # str | None


def export_pptx(
    slides: list[dict] | str,
    filename: str | None,
) -> FileRef:
    """Export *slides* as a PowerPoint presentation."""
    raise NotImplementedError(
        "TODO: copy _create_presentation from tools/presentations.py.\n"
        "Use TemplateRegistry.get('pptx') instead of module-level globals."
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

    Args:
        slides_data: List of slide definitions. Each dict may contain:
            - `title` (str): Slide title
            - `content` (Union[str, List[str]]): Bullet points or paragraphs
            - `image_query` (Optional[str]): Query to search for an image
            - `image_position` (str): One of 'left', 'right', 'top', 'bottom' (default: 'right')
            - `image_size` (str): One of 'small', 'medium', 'large' (default: 'medium')
        filename: Output filename (e.g., "report.pptx")
        folder_path: Optional output folder. If None, auto-generated.
        title: Title for the cover slide (default: empty)

    Returns:
        dict with keys:
            - 'url': Publicly accessible link (via `_public_url`)
            - 'path': Local filesystem path to saved .pptx

    Raises:
        OSError: If saving fails.
    """
    log = logging.getLogger(__name__)

    if folder_path is None:
        folder_path = _generate_unique_folder()

    if filename:
        # Sanitize filename to prevent path traversal
        filename = os.path.basename(filename)
        filepath = os.path.join(folder_path, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        fname = filename
    else:
        filepath, fname = _generate_filename(folder_path, "pptx")

    prs = None
    use_template = False
    title_layout = None
    content_layout = None

    # Determine which template to use: explicit parameter > module-level > none
    active_template = template_path or PPTX_TEMPLATE_PATH

    # === 1. Try loading template and extracting layouts ===
    if active_template and os.path.exists(active_template):
        try:
            log.info(f"Loading template: {active_template}")
            prs = Presentation(active_template)
            use_template = True

            # === SELECT LAYOUTS BY NAME ===
            layouts_by_name = {layout.name: layout for layout in prs.slide_layouts}

            TITLE_LAYOUT_NAME = 'Title Slide'
            CONTENT_LAYOUT_NAME = 'Slide 01'

            title_layout = layouts_by_name.get(TITLE_LAYOUT_NAME)
            content_layout = layouts_by_name.get(CONTENT_LAYOUT_NAME)

            # Fallback if not found by name
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

            # Ultimate fallback
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

            # Clean template slides (keep none — we'll rebuild all)
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

    # === 2. Fallback: create new presentation ===
    if not prs:
        log.info("Creating new presentation (no template)")
        prs = Presentation()
        title_layout = prs.slide_layouts[0]
        content_layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else title_layout

    # === 3. Add title slide ===
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

    # === 4. Add content slides with optional images ===
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

    # === 5. Save and return ===
    try:
        prs.save(filepath)
        log.info(f"Saved presentation to: {filepath}")
        if use_template:
            log.info(f"Template applied: {active_template}")
        else:
            log.warning("No template used — default style applied")
    except Exception as e:
        log.error(f"Failed to save presentation: {e}", exc_info=True)
        raise

    return {
        "url": _public_url(folder_path, fname),
        "path": filepath
    }
    