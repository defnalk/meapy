# variables.tf — Input variables for the meapy AWS stack.

variable "project_name" {
  type        = string
  default     = "meapy"
  description = "Logical project name; used as a prefix for AWS resources."
}

variable "aws_region" {
  type        = string
  default     = "eu-west-1"
  description = "AWS region to deploy into."
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment name (dev/staging/prod)."
}

variable "lambda_memory" {
  type        = number
  default     = 256
  description = "Lambda memory size in MB."
}

variable "lambda_timeout" {
  type        = number
  default     = 30
  description = "Lambda timeout in seconds."
}

variable "docker_image_tag" {
  type        = string
  default     = "latest"
  description = "Docker image tag to deploy from ECR."
}

variable "expose_via" {
  type        = string
  default     = "function_url"
  description = "How to expose the Lambda: 'function_url' or 'apigw'."

  validation {
    condition     = contains(["function_url", "apigw"], var.expose_via)
    error_message = "expose_via must be 'function_url' or 'apigw'."
  }
}

variable "function_url_auth" {
  type        = string
  default     = "NONE"
  description = "Auth type for the Lambda Function URL: NONE or AWS_IAM."
}

variable "cors_allow_origins" {
  type        = list(string)
  default     = ["*"]
  description = "Allowed CORS origins. Override per environment."
}
