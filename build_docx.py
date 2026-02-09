import json
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from bs4 import BeautifulSoup
from bs4 import BeautifulSoup, NavigableString, Tag

def add_black_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0, 0, 0)
        run.font.bold = True


def add_paragraph(doc, text, bold=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(12)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)




def _append_inline_runs(paragraph, node):
    """
    Рекурсивно добавляет текст в paragraph, соблюдая <strong>/<b> и <i>/<em>.
    Никакие HTML-теги в docx не попадают.
    """
    if isinstance(node, NavigableString):
        text = str(node)
        if text:
            run = paragraph.add_run(text)
            run.font.size = Pt(12)
            run.font.color.rgb = RGBColor(0, 0, 0)
        return

    if not isinstance(node, Tag):
        return

    name = node.name.lower()

    if name == "br":
        paragraph.add_run("\n")
        return

    
    bold = name in ("strong", "b")
    italic = name in ("i", "em")

 
    if bold or italic:
        text = node.get_text()
        run = paragraph.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return

    for child in node.children:
        _append_inline_runs(paragraph, child)


def add_html_block(doc, html: str):
    """
    HTML → DOCX (p, ul, li, strong/b, i/em, br).
    Теги не пишутся в docx как текст.
    """
    soup = BeautifulSoup(html, "html.parser")

    
    for b in soup.find_all("b"):
        b.name = "strong"
    for i in soup.find_all("i"):
        i.name = "em"

    
    elements = []
    for el in soup.contents:
        if isinstance(el, Tag):
            elements.append(el)

    for elem in elements:
        name = elem.name.lower()

        if name == "p":
            p = doc.add_paragraph()
            for child in elem.children:
                _append_inline_runs(p, child)

        elif name == "ul":
            for li in elem.find_all("li", recursive=False):
                p = doc.add_paragraph(style="List Bullet")
                for child in li.children:
                    _append_inline_runs(p, child)



def build_docx_from_slides(json_path: str, output_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        slides = json.load(f)

    doc = Document()

    # обложка
    title = doc.add_heading("Доклад по презентации", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.color.rgb = RGBColor(0, 0, 0)

    p = doc.add_paragraph("\nАвтор: Студент\n")
    p.add_run("Дата: ").bold = True
    p.add_run(datetime.now().strftime("%d.%m.%Y"))

    doc.add_page_break()

    # слайды
    for slide in slides:
        slide_num = slide["slide"]
        html_text = slide["generated_html"]

        add_black_heading(doc, f"Слайд {slide_num}", level=1)
        add_html_block(doc, html_text)

        doc.add_page_break()

    doc.save(output_path)
    print("DOCX saved:", output_path)


if __name__ == "__main__":
    build_docx_from_slides(
        json_path=r"E:\check_slide\slides_report.json",
        output_path=r"E:\check_slide\result.docx",
    )


