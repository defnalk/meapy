# oidc.tf — GitHub Actions OIDC trust for keyless AWS deploys.
#
# Creates the GitHub OIDC provider (idempotent — only one allowed per account)
# and a deploy role that the release workflow assumes via
# `aws-actions/configure-aws-credentials`. Trust is scoped to a specific
# repo + ref pattern so other repos in the org can't assume it.
#
# After apply, set the `AWS_DEPLOY_ROLE_ARN` secret/var in the GitHub repo
# settings to the value of `output.github_actions_role_arn`.

variable "github_owner" {
  type        = string
  default     = "defnalk"
  description = "GitHub org/user that owns the repo."
}

variable "github_repo" {
  type        = string
  default     = "meapy"
  description = "Repo name (without owner)."
}

variable "github_ref_pattern" {
  type        = string
  default     = "ref:refs/tags/v*"
  description = "Which refs may assume the deploy role. Default: tags only."
}

# The OIDC provider is account-global. If it already exists from another
# stack, import it instead of creating a duplicate:
#   terraform import aws_iam_openid_connect_provider.github \
#     arn:aws:iam::ACCOUNT:oidc-provider/token.actions.githubusercontent.com
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_policy_document" "github_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_owner}/${var.github_repo}:${var.github_ref_pattern}"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = "${local.name_prefix}-gh-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json
}

# Least-privilege deploy permissions: ECR push + Lambda update only.
data "aws_iam_policy_document" "github_deploy" {
  statement {
    sid     = "EcrAuth"
    actions = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    sid = "EcrPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [aws_ecr_repository.meapy.arn]
  }
  statement {
    sid = "LambdaUpdate"
    actions = [
      "lambda:UpdateFunctionCode",
      "lambda:GetFunction",
      "lambda:PublishVersion",
    ]
    resources = [aws_lambda_function.meapy.arn]
  }
}

resource "aws_iam_role_policy" "github_deploy" {
  name   = "${local.name_prefix}-gh-deploy"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy.json
}

output "github_actions_role_arn" {
  value       = aws_iam_role.github_deploy.arn
  description = "Set as AWS_DEPLOY_ROLE_ARN in GitHub repo settings."
}
