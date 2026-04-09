# outputs.tf — Useful endpoints and identifiers exposed by the stack.

output "ecr_repo_url" {
  value       = aws_ecr_repository.meapy.repository_url
  description = "ECR repository URL — push the Lambda container image here."
}

output "lambda_function_name" {
  value       = aws_lambda_function.meapy.function_name
  description = "Lambda function name (handy for `aws lambda invoke`)."
}

output "cloudwatch_log_group" {
  value       = aws_cloudwatch_log_group.meapy.name
  description = "CloudWatch log group with Lambda logs."
}

output "api_endpoint" {
  description = "Public HTTPS endpoint for the meapy API."
  value = (
    var.expose_via == "function_url"
    ? try(aws_lambda_function_url.meapy[0].function_url, null)
    : try(aws_apigatewayv2_stage.default[0].invoke_url, null)
  )
}
