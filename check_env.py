from dotenv import load_dotenv
import os

load_dotenv()
print("OPENAI_URL =", os.getenv("OPENAI_URL"))
print("CHAT_GPT_KEY starts with =", (os.getenv("CHAT_GPT_KEY") or "")[:3])
