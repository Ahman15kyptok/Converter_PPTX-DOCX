import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse

from storage import set_job, get_job
from tasks import process_job

load_dotenv()

WORKDIR = os.getenv("WORKDIR", "./workdir")
os.makedirs(WORKDIR, exist_ok=True)

app = FastAPI(title="Slide→Report Platform")


@app.post("/jobs")
async def create_job(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(WORKDIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    input_path = os.path.join(job_dir, file.filename)
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job = {
        "job_id": job_id,
        "status": "queued",
        "filename": file.filename,
        "input_path": input_path,
        "job_dir": job_dir,
    }
    set_job(job_id, job)

    process_job.delay(job_id)

    return {"job_id": job_id, "status": "queued"}

@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job

@app.get("/jobs/{job_id}/result")
def job_result(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"job status is {job.get('status')}")
    path = job.get("result_docx")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="result file not found")
    return FileResponse(path, filename="result.docx")
