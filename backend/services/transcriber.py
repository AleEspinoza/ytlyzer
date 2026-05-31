import os
import uuid
import tempfile
import yt_dlp
from faster_whisper import WhisperModel
from google.cloud import firestore, tasks_v2

_db = None
_whisper_model = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=os.environ["GCP_PROJECT_ID"])
    return _db


def _get_whisper_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


def _download_audio(youtube_url: str, output_path: str) -> str:
    """Download audio from YouTube URL, return path to .mp3 file."""
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    return output_path + ".mp3"


def _transcribe_audio(audio_path: str) -> list[dict]:
    """Run Whisper on audio file, return list of segments with timestamps."""
    model = _get_whisper_model()
    segments, _ = model.transcribe(audio_path, beam_size=5)
    return [
        {
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        }
        for seg in segments
    ]


async def enqueue_transcription_job(youtube_url: str, query: str) -> str:
    """
    Create a Firestore job record and enqueue a Cloud Tasks task.
    Returns the job_id.
    """
    job_id = str(uuid.uuid4())
    db = _get_db()

    db.collection(os.environ["FIRESTORE_COLLECTION"]).document(job_id).set({
        "job_id": job_id,
        "url": youtube_url,
        "query": query,
        "status": "queued",
        "transcript": None,
        "fragments": None,
    })

    project = os.environ["GCP_PROJECT_ID"]
    location = os.environ["CLOUD_TASKS_LOCATION"]
    queue = os.environ["CLOUD_TASKS_QUEUE"]
    service_url = os.environ.get("CLOUD_RUN_URL", "http://localhost:8080")

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(project, location, queue)

    import json
    payload = json.dumps({"job_id": job_id, "url": youtube_url, "query": query}).encode()

    client.create_task(request={
        "parent": parent,
        "task": {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{service_url}/internal/process",
                "headers": {"Content-Type": "application/json"},
                "body": payload,
            }
        },
    })

    return job_id


async def get_job_result(job_id: str) -> dict | None:
    """Fetch job status and results from Firestore."""
    db = _get_db()
    doc = db.collection(os.environ["FIRESTORE_COLLECTION"]).document(job_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()


async def process_job(job_id: str, youtube_url: str, query: str) -> None:
    """
    Execute the full transcription pipeline for a job.
    Called by the internal Cloud Tasks handler.
    """
    db = _get_db()
    collection = os.environ["FIRESTORE_COLLECTION"]
    ref = db.collection(collection).document(job_id)

    ref.update({"status": "processing"})

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = os.path.join(tmp_dir, "audio")
            audio_file = _download_audio(youtube_url, audio_path)
            segments = _transcribe_audio(audio_file)

        transcript = " ".join(seg["text"] for seg in segments)

        from backend.services.analyzer import analyze_transcript
        fragments = await analyze_transcript(transcript, segments, query)

        ref.update({
            "status": "completed",
            "transcript": transcript,
            "fragments": fragments,
        })

    except Exception as e:
        ref.update({"status": "failed", "error": str(e)})
        raise
