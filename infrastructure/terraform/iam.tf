# ============================================================
# IAM
# Rol mínimo de ejecución para la Lambda
# ============================================================

resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "lambda.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Permite a la Lambda escribir logs básicos en CloudWatch Logs
resource "aws_iam_role_policy_attachment" "lambda_basic_logging" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


# ============================================================
# BEDROCK
# Obtiene dinámicamente la cuenta AWS actual.
# Evitamos hardcodear el account ID para mantener portabilidad.
# ============================================================

data "aws_caller_identity" "current" {}


# ============================================================
# BEDROCK
# Permite a la Lambda invocar únicamente Amazon Nova Micro
# mediante el perfil de inferencia geográfico de la UE.
# ============================================================

resource "aws_iam_role_policy" "lambda_bedrock" {
  name = "${var.project_name}-${var.environment}-bedrock"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "InvokeNovaMicroEUInferenceProfile"
        Effect = "Allow"

        Action = [
          "bedrock:InvokeModel"
        ]

        Resource = [
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-micro-v1:0"
        ]
      },
      {
        Sid    = "InvokeNovaMicroEUModels"
        Effect = "Allow"

        Action = [
          "bedrock:InvokeModel"
        ]

        Resource = [
          "arn:aws:bedrock:eu-central-1::foundation-model/amazon.nova-micro-v1:0",
          "arn:aws:bedrock:eu-north-1::foundation-model/amazon.nova-micro-v1:0",
          "arn:aws:bedrock:eu-west-1::foundation-model/amazon.nova-micro-v1:0",
          "arn:aws:bedrock:eu-west-3::foundation-model/amazon.nova-micro-v1:0"
        ]

        Condition = {
          StringEquals = {
            "bedrock:InferenceProfileArn" = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-micro-v1:0"
          }
        }
      }
    ]
  })
}