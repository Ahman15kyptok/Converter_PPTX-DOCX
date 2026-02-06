import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
JOB_TTL = int(os.getenv("JOB_TTL", "86400"))

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def job_key(job_id: str) -> str:
    return f"job:{job_id}"

def set_job(job_id: str, data: dict):
    key = job_key(job_id)
    r.set(key, json.dumps(data, ensure_ascii=False))
    r.expire(key, JOB_TTL)

def get_job(job_id: str) -> dict | None:
    raw = r.get(job_key(job_id))
    return json.loads(raw) if raw else None
