from enum import Enum
from pydantic import BaseModel


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Fragment(BaseModel):
    start: float
    end: float
    text: str
    reason: str


class Job(BaseModel):
    job_id: str
    url: str
    query: str
    status: JobStatus
    transcript: str | None = None
    fragments: list[Fragment] | None = None
    error: str | None = None
