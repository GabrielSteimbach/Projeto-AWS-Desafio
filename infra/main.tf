terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

data "aws_s3_bucket" "data_lake" {
  bucket = var.lake_bucket_name
}

locals {
  common_tags = {
    Project            = var.project_name
    Environment        = var.environment
    DataClassification = "Confidential"
    ManagedBy          = "Terraform"
  }
}

output "data_lake_bucket_name" {
  description = "Bucket existente das tabelas Iceberg"
  value       = data.aws_s3_bucket.data_lake.bucket
}

output "glue_database_name" {
  description = "Nome do banco existente no Glue Data Catalog"
  value       = var.glue_database_name
}

resource "aws_iam_role" "glue_job" {
  name = "${var.project_name}-${var.environment}-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "glue_job" {
  name = "${var.project_name}-${var.environment}-glue-policy"
  role = aws_iam_role.glue_job.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListDataLakeBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucketLocation"]
        Resource = data.aws_s3_bucket.data_lake.arn
      },
      {
        Sid    = "ReadBronzeAndSilverObjects"
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = [
          "${data.aws_s3_bucket.data_lake.arn}/warehouse/desafio_glue.db/fin_contabilidade_saldo_contrato_bronze/*",
          "${data.aws_s3_bucket.data_lake.arn}/warehouse/desafio_glue.db/fin_contabilidade_saldo_contrato_silver/*",
          "${data.aws_s3_bucket.data_lake.arn}/scripts/*",
          "${data.aws_s3_bucket.data_lake.arn}/tmp/*"
        ]
      },
      {
        Sid    = "WriteSilverAndTemporaryObjects"
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:AbortMultipartUpload"]
        Resource = [
          "${data.aws_s3_bucket.data_lake.arn}/warehouse/desafio_glue.db/fin_contabilidade_saldo_contrato_silver/*",
          "${data.aws_s3_bucket.data_lake.arn}/tmp/*"
        ]
      },
      {
        Sid    = "UpdateSilverAndTemporaryObjects"
        Effect = "Allow"
        Action = ["s3:DeleteObject"]
        Resource = [
          "${data.aws_s3_bucket.data_lake.arn}/warehouse/desafio_glue.db/fin_contabilidade_saldo_contrato_silver/*",
          "${data.aws_s3_bucket.data_lake.arn}/tmp/*"
        ]
      },
      {
        Sid    = "UseGlueCatalog"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:GetPartitions",
          "glue:BatchGetPartition",
          "glue:BatchCreatePartition",
          "glue:CreatePartition",
          "glue:UpdatePartition"
        ]
        Resource = [
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:database/${var.glue_database_name}",
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.glue_database_name}/*"
        ]
      },
      {
        Sid      = "CreateGlueLogGroups"
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup"]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws-glue/*"
      },
      {
        Sid      = "WriteGlueLogs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws-glue/*:log-stream:*"
      },
      {
        Sid    = "UseS3Encryption"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService"    = "s3.${var.aws_region}.amazonaws.com"
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

resource "aws_s3_object" "silver_script" {
  bucket      = data.aws_s3_bucket.data_lake.bucket
  key         = "scripts/fin_contabilidade_saldo_contrato_silver.py"
  source      = "${path.module}/../src/fin_contabilidade_saldo_contrato.py"
  source_hash = filemd5("${path.module}/../src/fin_contabilidade_saldo_contrato.py")
}

resource "aws_glue_job" "silver" {
  name              = "${var.project_name}-${var.environment}-silver"
  role_arn          = aws_iam_role.glue_job.arn
  glue_version      = "6.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60
  max_retries       = 1

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_object.silver_script.bucket}/${aws_s3_object.silver_script.key}"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--datalake-formats"                 = "iceberg"
    "--enable-glue-datacatalog"          = "true"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-job-insights"              = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://${data.aws_s3_bucket.data_lake.bucket}/tmp/"
    "--SOURCE_DATABASE"                  = var.glue_database_name
    "--SOURCE_TABLE"                     = "fin_contabilidade_saldo_contrato_bronze"
    "--TARGET_DATABASE"                  = var.glue_database_name
    "--TARGET_TABLE"                     = "fin_contabilidade_saldo_contrato_silver"
    "--conf"                             = "spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions --conf spark.sql.catalog.glue_catalog=org.apache.iceberg.spark.SparkCatalog --conf spark.sql.catalog.glue_catalog.warehouse=s3://${data.aws_s3_bucket.data_lake.bucket}/warehouse/ --conf spark.sql.catalog.glue_catalog.catalog-impl=org.apache.iceberg.aws.glue.GlueCatalog --conf spark.sql.catalog.glue_catalog.io-impl=org.apache.iceberg.aws.s3.S3FileIO"
  }

  tags = local.common_tags

  depends_on = [
    aws_iam_role_policy.glue_job
  ]
}