# ============================================================
# LAMBDA
# Backend serverless inicial
# ============================================================

# ============================================================
# Empaquetado local del código Python para Lambda
# ============================================================

data "archive_file" "lambda_zip" {
  type = "zip"

  # El directorio build/lambda contiene:
  # - nuestro código Python
  # - FastAPI
  # - Mangum
  # - dependencias compatibles con AWS Lambda
  source_dir = "${path.module}/../../build/lambda"

  output_path = "${path.module}/lambda.zip"
}

resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-${var.environment}-api"

  runtime = "python3.12"
  handler = "lambda_function.lambda_handler"

  role = aws_iam_role.lambda_execution_role.arn

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  # Configuración mínima para desarrollo.
  memory_size = 128
  timeout     = 10
  # Variables de entorno disponibles para el backend
  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }
}