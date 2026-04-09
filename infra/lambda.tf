# lambda.tf — ECR repository, Lambda container function, IAM, and (optionally)
# a Function URL. Toggle expose_via=apigw to route through API Gateway instead
# (see api_gateway.tf).

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  image_uri   = "${aws_ecr_repository.meapy.repository_url}:${var.docker_image_tag}"
}

# ──────────────────────────────────────────────────────────────────────────
# ECR
# ──────────────────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "meapy" {
  name                 = local.name_prefix
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "meapy" {
  repository = aws_ecr_repository.meapy.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# ──────────────────────────────────────────────────────────────────────────
# IAM — least privilege execution role
# ──────────────────────────────────────────────────────────────────────────
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${local.name_prefix}-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda_logs" {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_role_policy" "lambda_logs" {
  name   = "${local.name_prefix}-logs"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_logs.json
}

# ──────────────────────────────────────────────────────────────────────────
# CloudWatch log group
# ──────────────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "meapy" {
  name              = "/aws/lambda/${local.name_prefix}"
  retention_in_days = 14
}

# ──────────────────────────────────────────────────────────────────────────
# Lambda (container image, ARM64 / Graviton)
# ──────────────────────────────────────────────────────────────────────────
resource "aws_lambda_function" "meapy" {
  function_name = local.name_prefix
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = local.image_uri
  architectures = ["arm64"]
  memory_size   = var.lambda_memory
  timeout       = var.lambda_timeout

  environment {
    variables = {
      LOG_LEVEL   = "INFO"
      ENVIRONMENT = var.environment
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.meapy,
    aws_iam_role_policy.lambda_logs,
  ]
}

# ──────────────────────────────────────────────────────────────────────────
# Function URL (only if expose_via = "function_url")
# ──────────────────────────────────────────────────────────────────────────
resource "aws_lambda_function_url" "meapy" {
  count              = var.expose_via == "function_url" ? 1 : 0
  function_name      = aws_lambda_function.meapy.function_name
  authorization_type = var.function_url_auth

  cors {
    allow_origins = var.cors_allow_origins
    allow_methods = ["GET", "POST"]
    allow_headers = ["content-type"]
    max_age       = 3600
  }
}
