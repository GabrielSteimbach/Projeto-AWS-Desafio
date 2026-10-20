variable "aws_region" {
  description = "Região AWS onde a infraestrutura será criada"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefixo para identificar os recursos do projeto"
  type        = string
  default     = "fin-contabilidade-saldo"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Use somente letras minúsculas, números e hífens."
  }
}

variable "environment" {
  description = "Ambiente da implantação"
  type        = string
  default     = "dev"
}

variable "glue_database_name" {
  description = "Nome do banco de dados no Glue Data Catalog"
  type        = string
  default     = "desafio_glue"
}

variable "lake_bucket_name" {
  description = "Bucket existente que contém as tabelas Iceberg"
  type        = string
  default     = "mockdesafio-iceberg"
}