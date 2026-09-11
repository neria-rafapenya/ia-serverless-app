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