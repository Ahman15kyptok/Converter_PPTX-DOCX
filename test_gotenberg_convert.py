import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()


from presentationconverter import PresentationConverter

async def main():
    input_pptx = r"E:\check_slide\test.pptx"
    if not os.path.exists(input_pptx):
        raise FileNotFoundError(f"Не найден файл: {input_pptx}")

    with open(input_pptx, "rb") as f:
        pptx_bytes = f.read()

    converter = PresentationConverter()

    async with aiohttp.ClientSession() as session:
        pdf_bytes = await converter.convert_to_pdf_in_memory(
            pptx_bytes,
            os.path.basename(input_pptx),
            session
        )

    out_pdf = r"E:\check_slide\out.pdf"
    with open(out_pdf, "wb") as f:
        f.write(pdf_bytes)

    print("OK: PDF saved ->", out_pdf, "size =", len(pdf_bytes), "bytes")

asyncio.run(main())
