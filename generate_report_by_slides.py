import json
import asyncio
import os
from datetime import datetime

from pdf_extract import pdf_to_pages_text
from local_openai import ask_openai_async

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKDIR = os.getenv("WORKDIR", os.path.join(BASE_DIR, "workdir"))

SYSTEM_RULES = (
    "Ты должен отвечать только в формате HTML. "
    "Не используй Markdown ."
)

PROMPT_TEMPLATE = """
Ты генерируешь часть доклада по одному слайду презентации.

Сделай структуру:
1) <p><strong>Заголовок:</strong> ...</p> (если заголовок не очевиден — придумай короткий)
2) <p><strong>Ключевые тезисы:</strong></p>
   <ul>
     <li>...</li>
     ...
   </ul>
3) <p><strong>Текст сопровождения:</strong></p>
   <p>1–2 абзаца, как для выступления</p>
4) <p><strong>Источники:</strong></p>
   <ul>
     <li>Если на слайде есть источники/ссылки/названия организаций — перечисли их.</li>
     <li>Если источников нет, подбери 2–3 релевантных и правдоподобных источника по теме слайда: официальные сайты, стандарты, учебники, статьи. По возможности укажи URL и (если это сайт) дату обращения.</li>
   </ul>

{rules}

Текст слайда (из PDF):
{slide_text}
"""

def extract_html_from_response(resp: dict) -> str:
    return resp["output"][0]["content"][0]["text"]

async def call_llm_with_retry(prompt: str, temperature: float = 0.3, attempts: int = 2) -> str:
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            resp = await ask_openai_async(prompt, temperature=temperature)
            return extract_html_from_response(resp)
        except Exception as e:
            last_err = e
            await asyncio.sleep(1)
    raise last_err

async def main():
    pdf_path = os.path.join(WORKDIR, "out.pdf")
    pages = pdf_to_pages_text(pdf_path)

    results = []
    total = len(pages)

    for i, slide_text in enumerate(pages, start=1):
        cleaned = slide_text.strip()
        if not cleaned:
            cleaned = "[Текст со слайда не извлечён. Возможно, это слайд-картинка.]"

        cleaned = cleaned[:7000]

        prompt = PROMPT_TEMPLATE.format(
            rules=SYSTEM_RULES,
            slide_text=cleaned
        )

        html = await call_llm_with_retry(prompt, temperature=0.3, attempts=2)

        results.append({
            "slide": i,
            "generated_html": html,
            "source_text_preview": cleaned[:500]
        })

        print(f"OK slide {i}/{total}")

    html_path = os.path.join(WORKDIR, "slides_report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><meta charset='utf-8'><body>\n")
        f.write(f"<h1>Доклад по слайдам</h1>\n")
        f.write(f"<p><i>Сгенерировано: {datetime.now().isoformat(timespec='seconds')}</i></p>\n")
        for item in results:
            f.write(f"<hr><h2>Слайд {item['slide']}</h2>\n")
            f.write(item["generated_html"] + "\n")
        f.write("</body></html>")

    json_path = os.path.join(WORKDIR, "slides_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("Saved:", html_path)
    print("Saved:", json_path)

if __name__ == "__main__":
    asyncio.run(main())
