# ============================================================
# API GATEWAY
# HTTP API de entrada al backend serverless
# ============================================================

resource "aws_apigatewayv2_api" "api" {
  name          = "${var.project_name}-${var.environment}-api"
  protocol_type = "HTTP"
}

# ============================================================
# Integración API Gateway -> Lambda
# ============================================================

resource "aws_apigatewayv2_integration" "lambda" {
  api_id = aws_apigatewayv2_api.api.id

  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api.invoke_arn

  payload_format_version = "2.0"
}

# ============================================================
# Ruta HTTP pública
# GET /health -> Lambda
# ============================================================

resource "aws_apigatewayv2_route" "health" {
  api_id = aws_apigatewayv2_api.api.id

  route_key = "GET /health"

  target = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# ============================================================
# Permiso para que API Gateway pueda invocar la Lambda
# ============================================================

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

# ============================================================
# Stage por defecto
# Publica automáticamente los cambios de la HTTP API
# ============================================================

resource "aws_apigatewayv2_stage" "default" {
  api_id = aws_apigatewayv2_api.api.id

  name        = "$default"
  auto_deploy = true

  # Limita específicamente las llamadas al endpoint de chat.
  # Protege Lambda y, cuando lo activemos, el consumo de Bedrock.
  route_settings {
    route_key = aws_apigatewayv2_route.chat.route_key

    throttling_rate_limit  = 2
    throttling_burst_limit = 5
  }
}

# ============================================================
# Ruta HTTP
# POST /api/chat -> Lambda
# ============================================================

resource "aws_apigatewayv2_route" "chat" {
  api_id = aws_apigatewayv2_api.api.id

  route_key = "POST /api/chat"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}