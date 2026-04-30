"""PDF exporter.
"""
from __future__ import annotations

from app.core.models import FileRef


async def export_pdf(
    content: str | list,
    filename: str | None,
) -> FileRef:
    """Export markdown/structured *content* as a PDF."""
    raise NotImplementedError(
        "TODO: copy _create_pdf from file_export_mcp.py and render_html_elements\n"
        "from pdf_renderer.py. Move reportlab imports to module level."
    )


def _get_styles():
    """Lazy initialization of paragraph styles."""
    global _styles
    if _styles is None:
        _styles = getSampleStyleSheet()
        _styles.add(ParagraphStyle(
            name="CustomHeading1",
            parent=_styles["Heading1"],
            textColor=colors.HexColor("#0A1F44"),
            fontSize=18,
            spaceAfter=16,
            spaceBefore=12,
            alignment=TA_LEFT
        ))
        _styles.add(ParagraphStyle(
            name="CustomHeading2",
            parent=_styles["Heading2"],
            textColor=colors.HexColor("#1C3F77"),
            fontSize=14,
            spaceAfter=12,
            spaceBefore=10,
            alignment=TA_LEFT
        ))
        _styles.add(ParagraphStyle(
            name="CustomHeading3",
            parent=_styles["Heading3"],
            textColor=colors.HexColor("#3A6FB0"),
            fontSize=12,
            spaceAfter=10,
            spaceBefore=8,
            alignment=TA_LEFT
        ))
        _styles.add(ParagraphStyle(
            name="CustomNormal",
            parent=_styles["Normal"],
            fontSize=11,
            leading=14,
            alignment=TA_LEFT
        ))
        _styles.add(ParagraphStyle(
            name="CustomListItem",
            parent=_styles["Normal"],
            fontSize=11,
            leading=14,
            alignment=TA_LEFT
        ))
        _styles.add(ParagraphStyle(
            name="CustomCode",
            parent=_styles["Code"],
            fontSize=10,
            leading=12,
            fontName="Courier",
            backColor=colors.HexColor("#F5F5F5"),
            borderColor=colors.HexColor("#CCCCCC"),
            borderWidth=1,
            leftIndent=10,
            rightIndent=10,
            topPadding=5,
            bottomPadding=5
        ))
    return _styles


# Module-level styles dict (lazy-loaded for external access)
class _StylesDict:
    """Lazy-loaded styles dictionary that proxies to _get_styles()."""
    def __getitem__(self, key):
        return _get_styles()[key]
    
    def __contains__(self, key):
        return key in _get_styles()
    
    def get(self, key, default=None):
        return _get_styles().get(key, default)
    
    def keys(self):
        return _get_styles().keys()
    
    def __iter__(self):
        return iter(_get_styles())


async def _create_pdf(text: str | list[str], filename: str, folder_path: str | None = None) -> dict:
    """Create a PDF file from markdown/text content.
    
    Args:
        text: Markdown string or list of content objects
        filename: Output filename
        folder_path: Optional output folder path
        
    Returns:
        dict with keys 'url' and 'path'
    """
    log.debug("Creating PDF file")
    if folder_path is None:
        folder_path = _generate_unique_folder()
        
    if filename:
        filename = os.path.basename(filename)
        filepath = os.path.join(folder_path, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        fname = filename
    else:
        filepath, fname = _generate_filename(folder_path, "pdf")

    md_parts = []
    if isinstance(text, list):
        for item in text:
            if isinstance(item, str):
                md_parts.append(item)
            elif isinstance(item, dict):
                t = item.get("type")
                if t == "title":
                    md_parts.append(f"# {item.get('text','')}")
                elif t == "subtitle":
                    md_parts.append(f"## {item.get('text','')}")
                elif t == "paragraph":
                    md_parts.append(item.get("text",""))
                elif t == "list":
                    md_parts.append("\n".join([f"- {x}" for x in item.get("items",[])]))
                elif t in ("image","image_query"):
                    query = item.get("query","")
                    if query:
                        md_parts.append(f"![Image](image_query: {query})")
    else:
        md_parts = [str(text or "")]

    md_text = "\n\n".join(md_parts)

    def replace_image_query(match):
        query = match.group(1).strip()
        image_url = search_image(log, query)
        return f'\n\n<img src="{image_url}" alt="Image: {query}" />\n\n' if image_url else ""

    md_text = re.sub(r'!\[[^\]]*\]\(\s*image_query:\s*([^)]+)\)', replace_image_query, md_text)
    html = markdown2.markdown(md_text, extras=['fenced-code-blocks','tables','break-on-newline','cuddled-lists'])
    soup = BeautifulSoup(html, "html.parser")
    
    from reportlab.platypus import Paragraph
    story = await render_html_elements(soup) or [Paragraph("Empty Content", styles["CustomNormal"])]

    from reportlab.platypus import SimpleDocTemplate
    doc = SimpleDocTemplate(filepath, topMargin=72, bottomMargin=72, leftMargin=72, rightMargin=72)
    try:
        doc.build(story)
    except Exception as e:
        log.error(f"Error building PDF {fname}: {e}", exc_info=True)
        from reportlab.platypus import Paragraph
        doc2 = SimpleDocTemplate(filepath)
        doc2.build([Paragraph("Error in PDF generation", styles["CustomNormal"])])

    return {"url": _public_url(folder_path, fname), "path": filepath}
    