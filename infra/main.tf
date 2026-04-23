# main.tf — Root Terraform module for meapy AWS deployment.
#
# Wires the AWS provider and pins versions. The actual resources live in
# sibling files (lambda.tf, api_gateway.tf). Backend config is in backend.tf
# so that it can be filled in per-environment without touching this file.

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.42"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
