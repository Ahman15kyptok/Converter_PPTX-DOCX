import json
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from bs4 import BeautifulSoup


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


def add_html_block(doc, html: str):

    soup = BeautifulSoup(html, "html.parser")


    for b in soup.find_all("b"):
        b.name = "strong"

    for elem in soup.children:
        if elem.name == "p":
            p = doc.add_paragraph()
            for child in elem.children:
                if child.name == "strong":
                    run = p.add_run(child.get_text())
                    run.bold = True
                else:
                    run = p.add_run(str(child))

                run.font.size = Pt(12)
                run.font.color.rgb = RGBColor(0, 0, 0)

        elif elem.name == "ul":
            for li in elem.find_all("li"):
                p = doc.add_paragraph(li.get_text(), style="List Bullet")
                for run in p.runs:
                    run.font.size = Pt(12)
                    run.font.color.rgb = RGBColor(0, 0, 0)



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
