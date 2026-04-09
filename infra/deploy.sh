#!/usr/bin/env bash
# deploy.sh — Build the Lambda container, push to ECR, and apply Terraform.
#
# Usage:
#   ./infra/deploy.sh                # plan + apply
#   ./infra/deploy.sh --dry-run      # plan only
#
# Requires: aws CLI, docker, terraform on PATH and AWS credentials configured.

set -euo pipefail

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

INFRA_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$INFRA_DIR/.." && pwd)"

cd "$INFRA_DIR"
terraform init -input=false

PROJECT="$(terraform output -raw lambda_function_name 2>/dev/null || echo meapy-dev)"
REGION="$(terraform output -raw aws_region 2>/dev/null || aws configure get region || echo eu-west-1)"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PROJECT}"
TAG="${IMAGE_TAG:-latest}"

echo ">> Logging in to ECR ($REGION)"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo ">> Building Lambda image"
docker build --platform linux/arm64 \
  -f "$ROOT_DIR/Dockerfile.lambda" \
  -t "${ECR_REPO}:${TAG}" \
  "$ROOT_DIR"

if [[ $DRY_RUN -eq 1 ]]; then
  echo ">> Dry run: terraform plan only (image not pushed)"
  terraform plan -var "docker_image_tag=${TAG}"
  exit 0
fi

echo ">> Pushing image"
docker push "${ECR_REPO}:${TAG}"

echo ">> Applying terraform"
terraform apply -auto-approve -var "docker_image_tag=${TAG}"
