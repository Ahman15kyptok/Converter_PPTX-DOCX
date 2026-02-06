import fitz  # PyMuPDF

def pdf_to_pages_text(pdf_path: str) -> list[str]:

    doc = fitz.open(pdf_path)
    pages = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text")

        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        pages.append(text)
    doc.close()
    return pages


if __name__ == "__main__":
    pdf_path = r"E:\check_slide\out.pdf"
    pages = pdf_to_pages_text(pdf_path)
    print("Pages:", len(pages))
    for idx, t in enumerate(pages[:3], start=1):
        print("\n" + "=" * 20, "PAGE", idx, "=" * 20)
        print(t[:1200] if t else "[EMPTY PAGE]")
