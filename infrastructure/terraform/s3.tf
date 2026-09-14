# ============================================================
# S3
# Almacenamiento privado de documentos para el futuro RAG
# ============================================================

resource "aws_s3_bucket" "documents" {
  # El account ID hace el nombre globalmente único sin
  # acoplar el código Terraform a una cuenta concreta.
  bucket = "${var.project_name}-${var.environment}-documents-${data.aws_caller_identity.current.account_id}"

  # Evitamos que terraform destroy borre accidentalmente
  # documentos existentes.
  force_destroy = false
}

# Bloqueamos cualquier acceso público al bucket.
resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Cifrado en reposo administrado por S3.
# SSE-S3 evita introducir por ahora el coste y gestión adicional de KMS.
resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}