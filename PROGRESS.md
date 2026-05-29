# YTlyzer — Progress Log

## Session 1 — 2026-05-29

### What was built

#### Infrastructure & GCP
- Created GCP project `ytlyzer` (project ID: `321570785793`)
- Enabled APIs: Cloud Run, Cloud Storage, Firestore, Cloud Tasks, Artifact Registry, IAM, Secret Manager
- Created service account `ytlyzer-deployer@ytlyzer.iam.gserviceaccount.com` with 7 IAM roles
- Created Artifact Registry repository `ytlyzer` in `us-central1`
- Configured Workload Identity Federation (pool: `ytlyzer-github-pool`, provider: `ytlyzer-github-provider`) for keyless GitHub Actions auth
- Created secrets in Secret Manager: `GCS_BUCKET_NAME`, `FIRESTORE_COLLECTION`, `CLOUD_TASKS_QUEUE`, `CLOUD_RUN_URL`

#### GitHub
- Created public repo `AleEspinoza/ytlyzer`
- Configured `gh` CLI authentication

#### Backend (FastAPI)
- `backend/api/main.py` — 3 public endpoints + 1 internal:
  - `GET /health`
  - `POST /analyze` — receives YouTube URL + query, enqueues job
  - `GET /jobs/{job_id}` — polls job status
  - `POST /internal/process` — called by Cloud Tasks to run pipeline
- `backend/services/transcriber.py` — full pipeline: yt-dlp download → Whisper transcription → Firestore persistence → Cloud Tasks enqueue
- `backend/services/analyzer.py` — Claude Sonnet 4.6 via Vertex AI to identify relevant transcript fragments
- `backend/models/job.py` — Pydantic models: `Job`, `Fragment`, `JobStatus`

#### CI/CD
- `.github/workflows/deploy.yml` — builds Docker image, pushes to Artifact Registry, deploys to Cloud Run on push to `main`
- `setup/gcp_setup.sh` — one-shot script to reproduce full GCP setup

#### Config files
- `Dockerfile` — python:3.11-slim + ffmpeg, targets Cloud Run port 8080
- `requirements.txt` — FastAPI, Whisper, yt-dlp, anthropic[vertex], GCP SDKs
- `.env.example`, `.gitignore`, `CLAUDE.md`

---

## Pending — Next Steps

### Required before first deploy works
- [ ] **GitHub Secrets** — add to `AleEspinoza/ytlyzer/settings/secrets/actions`:
  - `GCP_WORKLOAD_IDENTITY_PROVIDER`: `projects/321570785793/locations/global/workloadIdentityPools/ytlyzer-github-pool/providers/ytlyzer-github-provider`
  - `GCP_SERVICE_ACCOUNT`: `ytlyzer-deployer@ytlyzer.iam.gserviceaccount.com`
- [ ] **Vertex AI Model Garden** — enable `claude-sonnet-4-6` in GCP console and accept Anthropic terms
- [ ] **Cloud Tasks queue** — create the queue `transcription-queue` in `us-central1`
- [ ] **GCS bucket** — create bucket `ytlyzer-audio`
- [ ] **Firestore** — initialize database in native mode

### Code — not yet implemented
- [ ] `backend/api/main.py` — add `__init__.py` files to make packages importable
- [ ] Cloud Run service account for runtime (separate from deployer) with Vertex AI permissions
- [ ] `CLOUD_RUN_URL` secret — update after first deploy with the real URL
- [ ] Error handling and retries for Cloud Tasks callbacks
- [ ] Local development setup (docker-compose or instructions to run without GCP)

### Agents — scaffolded but empty
- [ ] `agents/infra/agent.py`
- [ ] `agents/dev/agent.py`
- [ ] `agents/review/agent.py`
- [ ] `agents/cicd/agent.py`
- [ ] `agents/cloud_eng/agent.py`

### Nice to have
- [ ] `git config --global user.name / user.email` — commits show hostname instead of real name
- [ ] Rename local branch `master` → `main` to match remote
