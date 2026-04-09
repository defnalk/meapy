# api_gateway.tf — HTTP API (API Gateway v2) in front of the meapy Lambda.
# Only created when var.expose_via = "apigw". Cheaper and faster than REST API.

resource "aws_apigatewayv2_api" "meapy" {
  count         = var.expose_via == "apigw" ? 1 : 0
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = var.cors_allow_origins
    allow_methods = ["GET", "POST"]
    allow_headers = ["content-type"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "meapy" {
  count                  = var.expose_via == "apigw" ? 1 : 0
  api_id                 = aws_apigatewayv2_api.meapy[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.meapy.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  count     = var.expose_via == "apigw" ? 1 : 0
  api_id    = aws_apigatewayv2_api.meapy[0].id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.meapy[0].id}"
}

resource "aws_cloudwatch_log_group" "apigw" {
  count             = var.expose_via == "apigw" ? 1 : 0
  name              = "/aws/apigw/${local.name_prefix}"
  retention_in_days = 14
}

resource "aws_apigatewayv2_stage" "default" {
  count       = var.expose_via == "apigw" ? 1 : 0
  api_id      = aws_apigatewayv2_api.meapy[0].id
  name        = var.environment
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.apigw[0].arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }
}

resource "aws_lambda_permission" "apigw" {
  count         = var.expose_via == "apigw" ? 1 : 0
  statement_id  = "AllowExecutionFromAPIGW"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.meapy.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.meapy[0].execution_arn}/*/*"
}
