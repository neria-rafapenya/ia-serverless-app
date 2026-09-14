# ============================================================
# COGNITO
# Autenticación de usuarios para la API
# ============================================================

resource "aws_cognito_user_pool" "users" {
  name = "${var.project_name}-${var.environment}-users"

  username_attributes = [
    "email"
  ]

  auto_verified_attributes = [
    "email"
  ]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }
}

resource "aws_cognito_user_pool_client" "web" {
  name = "${var.project_name}-${var.environment}-web"

  user_pool_id = aws_cognito_user_pool.users.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
}