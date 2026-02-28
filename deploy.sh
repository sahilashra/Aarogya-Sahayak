#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Aarogya Sahayak — One-Command Hackathon Deploy to AWS
# Prerequisites: AWS CLI configured, Python 3.11, pip
# Usage: bash deploy.sh [hackathon|dev]
# ─────────────────────────────────────────────────────────
set -euo pipefail

ENV="${1:-hackathon}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
DEPLOY_BUCKET="aarogya-deploy-${ACCOUNT}"

echo "═══════════════════════════════════════════════════"
echo " Aarogya Sahayak Deploy — env=${ENV} region=${REGION}"
echo "═══════════════════════════════════════════════════"

# 1. Create deployment bucket if it doesn't exist
echo "[1/6] Ensuring deployment S3 bucket..."
aws s3 mb "s3://${DEPLOY_BUCKET}" --region "${REGION}" 2>/dev/null || true

# 2. Build FAISS corpus index
echo "[2/6] Building FAISS corpus index..."
pip install -r requirements.txt -q
python demo/build_corpus.py

# 3. Package Lambda function
echo "[3/6] Packaging Lambda function..."
rm -f function.zip
zip -r function.zip src/ demo/pmc_corpus/ requirements.txt -x "**/__pycache__/*" "**/*.pyc"
aws s3 cp function.zip "s3://${DEPLOY_BUCKET}/function.zip"

# 4. Deploy CloudFormation
echo "[4/6] Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file infrastructure/cloudformation-minimal.yaml \
  --stack-name "aarogya-sahayak-${ENV}" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides Environment="${ENV}" \
  --region "${REGION}"

# 5. Upload FAISS corpus to corpus bucket
echo "[5/6] Uploading FAISS corpus to S3..."
CORPUS_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "aarogya-sahayak-${ENV}" \
  --query "Stacks[0].Outputs[?OutputKey=='CorpusBucketName'].OutputValue" \
  --output text --region "${REGION}")
aws s3 cp demo/pmc_corpus/ "s3://${CORPUS_BUCKET}/corpus/" --recursive

# 6. Print endpoint
echo "[6/6] Deployment complete!"
API=$(aws cloudformation describe-stacks \
  --stack-name "aarogya-sahayak-${ENV}" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text --region "${REGION}")
echo ""
echo "✅ API Endpoint: ${API}/summaries"
echo ""
echo "Test with:"
echo "  curl -X POST ${API}/summaries \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d @demo/synthetic_notes/diabetes_case.txt"
