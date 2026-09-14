variable "aws_region" {
  description = "Región AWS donde desplegaremos la infraestructura"
  type        = string
  default     = "eu-west-1"
}

variable "environment" {
  description = "Entorno de despliegue"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
  default     = "ia-serverless-app"
}

# Email donde recibiremos las alertas de costes
variable "budget_alert_email" {
  description = "Email para recibir alertas de AWS Budgets"
  type        = string
}

variable "ai_provider" {
  description = "Proveedor de IA utilizado por el backend"
  type        = string
  default     = "mock"
}

variable "bedrock_model_id" {
  description = "Identificador del modelo o perfil de inferencia utilizado por Amazon Bedrock"
  type        = string
  default     = "eu.amazon.nova-micro-v1:0"
}

# ============================================================
# INGESTA DOCUMENTAL
# Límites de seguridad y control de costes para el futuro RAG
# ============================================================

variable "ingestion_max_file_size_mb" {
  description = "Tamaño máximo permitido por archivo, en MB"
  type        = number
  default     = 20
}

variable "ingestion_max_pdf_pages" {
  description = "Número máximo de páginas permitido por documento PDF"
  type        = number
  default     = 100
}

variable "ingestion_max_files_per_batch" {
  description = "Número máximo de archivos que un usuario puede enviar en un mismo lote"
  type        = number
  default     = 10
}

variable "ingestion_allowed_extensions" {
  description = "Extensiones de archivo permitidas para la ingesta documental"
  type        = list(string)

  default = [
    "pdf",
    "txt"
  ]
}

variable "ingestion_max_chunks_per_document" {
  description = "Número máximo de chunks que podrá generar un único documento antes de abortar la generación de embeddings"
  type        = number
  default     = 500
}