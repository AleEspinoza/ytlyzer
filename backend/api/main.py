import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="YTlyzer", version="0.1.0")


class AnalyzeRequest(BaseModel):
    url: HttpUrl
    query: str


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class AnalysisResult(BaseModel):
    job_id: str
    status: str
    transcript: str | None = None
    fragments: list[dict] | None = None


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/analyze", response_model=JobResponse)
async def analyze_video(request: AnalyzeRequest):
    """
    Submit a YouTube URL for transcription and analysis.
    Returns a job_id to poll for results.
    """
    from backend.services.transcriber import enqueue_transcription_job

    job_id = await enqueue_transcription_job(str(request.url), request.query)
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Transcription job enqueued.",
    )


@app.get("/jobs/{job_id}", response_model=AnalysisResult)
async def get_job(job_id: str):
    """
    Poll the status and results of a transcription/analysis job.
    """
    from backend.services.transcriber import get_job_result

    result = await get_job_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return result


class ProcessRequest(BaseModel):
    job_id: str
    url: str
    query: str


@app.post("/internal/process", include_in_schema=False)
async def internal_process(request: ProcessRequest):
    """
    Called by Cloud Tasks to execute the transcription + analysis pipeline.
    Not exposed in the public API docs.
    """
    from backend.services.transcriber import process_job

    await process_job(request.job_id, request.url, request.query)
    return {"status": "ok"}
