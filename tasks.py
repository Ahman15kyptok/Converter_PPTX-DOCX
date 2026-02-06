import os
import shutil
import json
import aiohttp
from celery import Celery
from dotenv import load_dotenv

from storage import set_job, get_job

from presentationconverter import PresentationConverter
from pdf_extract import pdf_to_pages_text
from generate_report_by_slides import PROMPT_TEMPLATE, SYSTEM_RULES  # можно вынести
from local_openai import ask_openai_async
from build_docx import build_docx_from_slides

load_dotenv()

REDIS_URL = (os.getenv("REDIS_URL") or "redis://localhost:6379/0").strip()
WORKDIR = os.getenv("WORKDIR", "./workdir")

celery = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# важно для windows иногда:
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)


async def convert_to_pdf_if_needed(input_path: str, session: aiohttp.ClientSession) -> str:
    ext = os.path.splitext(input_path)[1].lower().strip(".")
    if ext == "pdf":
        return input_path

    converter = PresentationConverter()
    if not converter.is_presentation_memory(ext):
        raise RuntimeError(f"Unsupported input format: .{ext}")

    with open(input_path, "rb") as f:
        content = f.read()

    pdf_bytes = await converter.convert_to_pdf_in_memory(content, os.path.basename(input_path), session)

    pdf_path = os.path.splitext(input_path)[0] + ".pdf"
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    return pdf_path


async def generate_slides_json(pdf_path: str, out_json_path: str):
    pages = pdf_to_pages_text(pdf_path)
    results = []

    for i, slide_text in enumerate(pages, start=1):
        cleaned = slide_text.strip() or "[Текст со слайда не извлечён. Возможно, слайд-картинка.]"
        cleaned = cleaned[:7000]

        prompt = PROMPT_TEMPLATE.format(rules=SYSTEM_RULES, slide_text=cleaned)

        # 2 попытки
        resp = await ask_openai_async(prompt, temperature=0.3)
        html = resp["output"][0]["content"][0]["text"]

        results.append({"slide": i, "generated_html": html})

    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


@celery.task(bind=True, max_retries=1)
def process_job(self, job_id: str):
    job = get_job(job_id)
    if not job:
        return

    job_dir = job["job_dir"]
    input_path = job["input_path"]
    out_docx = os.path.join(job_dir, "result.docx")
    out_json = os.path.join(job_dir, "slides_report.json")

    try:
        set_job(job_id, {**job, "status": "processing"})

        async def run():
            async with aiohttp.ClientSession() as session:
                pdf_path = await convert_to_pdf_if_needed(input_path, session)
            await generate_slides_json(pdf_path, out_json)
            build_docx_from_slides(out_json, out_docx)

        import asyncio
        asyncio.run(run())

        set_job(job_id, {**job, "status": "done", "result_docx": out_docx})

        # cleanup: можно оставить docx, удалить остальное
        for name in os.listdir(job_dir):
            p = os.path.join(job_dir, name)
            if p != out_docx:
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    try:
                        os.remove(p)
                    except:
                        pass

    except Exception as e:
        # 2 попытки
        if self.request.retries < 1:
            raise self.retry(exc=e, countdown=2)
        set_job(job_id, {**job, "status": "error", "error": str(e)})
@celery.task
def ping():
    return "ping"
