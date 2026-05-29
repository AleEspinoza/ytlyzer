#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────
# YTlyzer — GCP Setup Script
# Configures Workload Identity Federation, service account,
# IAM roles, Artifact Registry, and Secret Manager secrets.
# ─────────────────────────────────────────────

PROJECT_ID="ytlyzer"
REGION="us-central1"
GITHUB_REPO="AleEspinoza/ytlyzer"
SA_NAME="ytlyzer-deployer"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
WIF_POOL="ytlyzer-github-pool"
WIF_PROVIDER="ytlyzer-github-provider"
AR_REPOSITORY="ytlyzer"

echo "▶ Setting active project to ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}"

# ─────────────────────────────────────────────
# 1. Enable required APIs
# ─────────────────────────────────────────────
echo "▶ Enabling APIs..."
gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  run.googleapis.com

# ─────────────────────────────────────────────
# 2. Create service account
# ─────────────────────────────────────────────
echo "▶ Creating service account ${SA_EMAIL}..."
gcloud iam service-accounts create "${SA_NAME}" \
  --display-name="YTlyzer GitHub Deployer" \
  --project="${PROJECT_ID}" 2>/dev/null || echo "  (already exists, skipping)"

# ─────────────────────────────────────────────
# 3. Grant IAM roles to service account
# ─────────────────────────────────────────────
echo "▶ Granting IAM roles..."
ROLES=(
  "roles/run.admin"
  "roles/artifactregistry.writer"
  "roles/secretmanager.secretAccessor"
  "roles/iam.serviceAccountUser"
  "roles/datastore.user"
  "roles/storage.objectAdmin"
  "roles/cloudtasks.enqueuer"
)
for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --quiet
  echo "  ✓ ${ROLE}"
done

# ─────────────────────────────────────────────
# 4. Create Artifact Registry repository
# ─────────────────────────────────────────────
echo "▶ Creating Artifact Registry repository '${AR_REPOSITORY}'..."
gcloud artifacts repositories create "${AR_REPOSITORY}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="YTlyzer Docker images" 2>/dev/null || echo "  (already exists, skipping)"

# ─────────────────────────────────────────────
# 5. Workload Identity Federation
# ─────────────────────────────────────────────
echo "▶ Creating Workload Identity Pool '${WIF_POOL}'..."
gcloud iam workload-identity-pools create "${WIF_POOL}" \
  --location="global" \
  --display-name="YTlyzer GitHub Actions Pool" 2>/dev/null || echo "  (already exists, skipping)"

WIF_POOL_ID=$(gcloud iam workload-identity-pools describe "${WIF_POOL}" \
  --location="global" \
  --format="value(name)")

echo "▶ Creating Workload Identity Provider '${WIF_PROVIDER}'..."
gcloud iam workload-identity-pools providers create-oidc "${WIF_PROVIDER}" \
  --location="global" \
  --workload-identity-pool="${WIF_POOL}" \
  --display-name="GitHub OIDC Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'" 2>/dev/null || echo "  (already exists, skipping)"

echo "▶ Binding service account to Workload Identity Pool..."
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WIF_POOL_ID}/attribute.repository/${GITHUB_REPO}" \
  --quiet

# ─────────────────────────────────────────────
# 6. Create secrets in Secret Manager
# ─────────────────────────────────────────────
echo "▶ Creating secrets in Secret Manager..."

create_secret() {
  local SECRET_NAME="$1"
  local SECRET_VALUE="$2"

  if gcloud secrets describe "${SECRET_NAME}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "  (${SECRET_NAME} already exists, adding new version)"
    echo -n "${SECRET_VALUE}" | gcloud secrets versions add "${SECRET_NAME}" --data-file=-
  else
    echo -n "${SECRET_VALUE}" | gcloud secrets create "${SECRET_NAME}" \
      --data-file=- \
      --replication-policy="automatic" \
      --project="${PROJECT_ID}"
    echo "  ✓ ${SECRET_NAME}"
  fi
}

# Prompt for secret values
echo ""
echo "Enter secret values (leave blank to set a placeholder and update later):"
echo ""

read -rp "  ANTHROPIC_API_KEY: " ANTHROPIC_API_KEY
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-PLACEHOLDER}"

read -rp "  GCS_BUCKET_NAME [ytlyzer-audio]: " GCS_BUCKET_NAME
GCS_BUCKET_NAME="${GCS_BUCKET_NAME:-ytlyzer-audio}"

read -rp "  FIRESTORE_COLLECTION [jobs]: " FIRESTORE_COLLECTION
FIRESTORE_COLLECTION="${FIRESTORE_COLLECTION:-jobs}"

read -rp "  CLOUD_TASKS_QUEUE [transcription-queue]: " CLOUD_TASKS_QUEUE
CLOUD_TASKS_QUEUE="${CLOUD_TASKS_QUEUE:-transcription-queue}"

read -rp "  CLOUD_RUN_URL (leave blank for now): " CLOUD_RUN_URL
CLOUD_RUN_URL="${CLOUD_RUN_URL:-PLACEHOLDER}"

create_secret "ANTHROPIC_API_KEY"      "${ANTHROPIC_API_KEY}"
create_secret "GCS_BUCKET_NAME"        "${GCS_BUCKET_NAME}"
create_secret "FIRESTORE_COLLECTION"   "${FIRESTORE_COLLECTION}"
create_secret "CLOUD_TASKS_QUEUE"      "${CLOUD_TASKS_QUEUE}"
create_secret "CLOUD_RUN_URL"          "${CLOUD_RUN_URL}"

# ─────────────────────────────────────────────
# 7. Print GitHub Secrets values
# ─────────────────────────────────────────────
WIF_PROVIDER_FULL=$(gcloud iam workload-identity-pools providers describe "${WIF_PROVIDER}" \
  --location="global" \
  --workload-identity-pool="${WIF_POOL}" \
  --format="value(name)")

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Add these as GitHub Actions Secrets in:"
echo "  https://github.com/${GITHUB_REPO}/settings/secrets/actions"
echo "══════════════════════════════════════════════════════"
echo ""
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER:"
echo "  ${WIF_PROVIDER_FULL}"
echo ""
echo "  GCP_SERVICE_ACCOUNT:"
echo "  ${SA_EMAIL}"
echo ""
echo "══════════════════════════════════════════════════════"
echo "✅ GCP setup complete."
