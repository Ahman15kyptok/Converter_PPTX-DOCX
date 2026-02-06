import os
from dotenv import load_dotenv
import aiohttp
import asyncio
import boto3
from botocore.config import Config
import presentationconverter


load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()

OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1").rstrip("/")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")

OPENROUTER_REFERER = os.getenv("OPENROUTER_REFERER", "http://localhost")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "check_slide")



# Прокси не использую
USE_TRUST_ENV = True


def _ds_headers() -> dict:
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
def _wrap_like_openai_responses(text: str) -> dict:
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": text}
                ],
            }
        ]
    }

def _openrouter_headers() -> dict:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY missing in .env")

    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_REFERER,
        "X-Title": OPENROUTER_APP_NAME,
    }

async def ask_openai_async(
    prompt,
    temperature,
    model=None,
    url=None,
    key=None,
    local_proxy_key=None,
    input_files=None,
    attempt=0,
):
    if input_files:
        raise NotImplementedError(
            "OpenRouter/DeepSeek: input_files не поддерживается. "
            "Передавай текст, извлечённый из PDF."
        )

    system_msg = (
        "Ты должен отвечать только в формате HTML. "
        
        "Не используй Markdown."
    )

    payload = {
        "model": model or OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }

    endpoint = f"{OPENROUTER_URL}/chat/completions"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                headers=_openrouter_headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as response:

                raw_text = await response.text()
                content_type = response.headers.get("Content-Type", "")

                if "application/json" not in content_type.lower():
                    raise RuntimeError(
                        f"OpenRouter вернул НЕ JSON "
                        f"(status={response.status}, type={content_type}). "
                        f"Preview: {raw_text[:400]}"
                    )

                data = await response.json()
                answer_text = data["choices"][0]["message"]["content"]
                return _wrap_like_openai_responses(answer_text)

    except Exception:
        if attempt >= 1:
            raise
        await asyncio.sleep(1)
        return await ask_openai_async(
            prompt,
            temperature,
            model,
            url,
            key,
            local_proxy_key,
            input_files,
            attempt + 1,
        )


async def upload_files_from_s3(bucket_info, s3_keys):

    s3_yandex_key = bucket_info[0]
    s3_yandex_secret = bucket_info[1]
    bucket_name = bucket_info[2]

    s3 = boto3.client(
        "s3",
        aws_access_key_id=s3_yandex_key,
        aws_secret_access_key=s3_yandex_secret,
        region_name="us-east-1",
        endpoint_url="https://storage.yandexcloud.net",
        config=Config(signature_version="s3v4"),
    )

    files = []
    for s3_key in s3_keys:
        s3_response = s3.get_object(Bucket=bucket_name, Key=s3_key)
        file_content = s3_response["Body"].read()
        filename = s3_key.split("/")[-1]
        files.append({"filename": filename, "bytes": file_content})

    return files


async def upload_files_from_s3_with_conversion(bucket_info, s3_keys, url, local_key, local_proxy_key):


    s3_yandex_key = bucket_info[0]
    s3_yandex_secret = bucket_info[1]
    bucket_name = bucket_info[2]

    s3 = boto3.client(
        "s3",
        aws_access_key_id=s3_yandex_key,
        aws_secret_access_key=s3_yandex_secret,
        region_name="us-east-1",
        endpoint_url="https://storage.yandexcloud.net",
        config=Config(signature_version="s3v4"),
    )

    results = []

    async with aiohttp.ClientSession(trust_env=USE_TRUST_ENV) as session:
        for s3_key_item in s3_keys:
            s3_key = s3_key_item.replace("cdn/", "", 1)
            s3_response = s3.get_object(Bucket=bucket_name, Key=s3_key)
            original_file_content = s3_response["Body"].read()
            original_filename = s3_key.split("/")[-1]

            file_extension = original_filename.lower().split(".")[-1]

            if file_extension == "pdf":
                results.append({"filename": original_filename, "bytes": original_file_content})
                continue

            converter = presentationconverter.PresentationConverter()
            if not converter.is_presentation_memory(file_extension):
                raise Exception(f"Неверный формат: {original_filename}")

            pdf_bytes = await converter.convert_to_pdf_in_memory(
                original_file_content,
                original_filename,
                session,
            )

            pdf_name = original_filename.rsplit(".", 1)[0] + ".pdf"
            results.append({"filename": pdf_name, "bytes": pdf_bytes})

    return results


async def delete_file_from_openai(file_id: str) -> bool:


    print(f"[DeepSeek] delete_file_from_openai called for {file_id} -> NO-OP")
    return True
