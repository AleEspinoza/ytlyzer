# YTlyzer — Master Context

## Project Overview
YouTube transcription and analysis system that transcribes videos via Whisper and analyzes them with Claude API to identify specific fragments through a REST API.

## Stack
- **Backend**: FastAPI (Python 3.11)
- **Transcription**: OpenAI Whisper
- **AI Analysis**: Claude API (Anthropic)
- **Deployment**: GCP Cloud Run
- **Container Registry**: GCP Artifact Registry

## GCP Configuration
- **Project ID**: ytlyzer
- **Region**: us-central1
- **Services in use**:
  - Cloud Run — API hosting
  - Cloud Storage — audio/video file storage
  - Firestore — job metadata and results
  - Cloud Tasks — async transcription job queue
  - Artifact Registry — Docker image registry

## Repository
- **GitHub**: AleEspinoza/ytlyzer

## Project Structure
```
ytlyzer/
├── backend/
│   ├── api/main.py          # FastAPI app entry point
│   ├── services/
│   │   ├── transcriber.py   # Whisper transcription logic
│   │   └── analyzer.py      # Claude API analysis logic
│   └── models/job.py        # Firestore job data models
├── agents/
│   ├── infra/agent.py       # Infrastructure agent
│   ├── dev/agent.py         # Development agent
│   ├── review/agent.py      # Code review agent
│   ├── cicd/agent.py        # CI/CD agent
│   └── cloud_eng/agent.py   # Cloud engineering agent
├── .github/workflows/       # GitHub Actions CI/CD pipelines
├── Dockerfile
├── requirements.txt
├── .env.example
└── CLAUDE.md
```

## Claude Agents
Each agent lives in its own folder under `/agents` and has a focused responsibility:

| Agent | Path | Responsibility |
|-------|------|----------------|
| Infra | `agents/infra/` | GCP infrastructure provisioning and Terraform |
| Dev | `agents/dev/` | Feature development, FastAPI routes, services |
| Review | `agents/review/` | Code review, security checks, best practices |
| CI/CD | `agents/cicd/` | GitHub Actions workflows, deployment pipelines |
| Cloud Eng | `agents/cloud_eng/` | Cloud Run config, scaling, observability |

## Conventions
- **Python version**: 3.11
- **Naming**: `snake_case` for all variables, functions, and file names
- **Environment variables**: loaded from `.env` (never hardcoded); see `.env.example` for required vars
- **API style**: RESTful, JSON responses, HTTP status codes
- **Error handling**: raise HTTP exceptions at the API layer; services return typed results

## Key Environment Variables
```
ANTHROPIC_API_KEY=
GCP_PROJECT_ID=ytlyzer
GCP_REGION=us-central1
GCS_BUCKET_NAME=
FIRESTORE_COLLECTION=jobs
CLOUD_TASKS_QUEUE=transcription-queue
```

## Goal
Accept a YouTube URL via REST API → download audio → transcribe with Whisper → analyze transcript with Claude → return timestamped fragments matching the user's query.
