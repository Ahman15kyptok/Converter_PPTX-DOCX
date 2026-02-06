import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com").strip().rstrip("/")
API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()

async def main():
    if not API_URL.startswith("http"):
        raise RuntimeError(f"DEEPSEEK_API_URL должен быть URL: {API_URL!r}")
    if not API_KEY.startswith("sk-"):
        raise RuntimeError("DEEPSEEK_API_KEY не ключ ")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Скажи строго: OK"}],
        "temperature": 0.2,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            print("Status:", resp.status)
            print(await resp.text())

asyncio.run(main())
