# Configuración general de Terraform
terraform {
  # Versión mínima de Terraform
  required_version = ">= 1.6.0"

  # Proveedores que necesita nuestro proyecto
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}

# Configuración del proveedor AWS
provider "aws" {
  region = var.aws_region

  # Estas etiquetas se añadirán automáticamente a todos
  # los recursos AWS que permitan etiquetas.
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}