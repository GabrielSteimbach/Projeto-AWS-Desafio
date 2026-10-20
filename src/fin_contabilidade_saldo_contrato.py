import logging
import sys
from datetime import date
from functools import reduce
from operator import or_
 
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark import SparkContext
from pyspark.sql import functions as F
 
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fin_contabilidade_saldo_contrato_silver")
 
args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "PROCESSING_DATE",
        "SOURCE_DATABASE",
        "SOURCE_TABLE",
        "TARGET_DATABASE",
        "TARGET_TABLE",
    ],
)
 
processing_date = date.fromisoformat(args["PROCESSING_DATE"])
 
spark_context = SparkContext.getOrCreate()
glue_context = GlueContext(spark_context)
spark = glue_context.spark_session
 
job = Job(glue_context)
job.init(args["JOB_NAME"], args)
 
source_table = (
    f"glue_catalog.{args['SOURCE_DATABASE']}.{args['SOURCE_TABLE']}"
)
target_table = (
    f"glue_catalog.{args['TARGET_DATABASE']}.{args['TARGET_TABLE']}"
)
 
bronze = spark.table(source_table)
 
contract_columns = [
    "id_transacao",
    "id_contrato",
    "id_conta",
    "cod_agencia",
    "tipo_contrato",
    "tipo_lancamento",
    "valor_lancamento",
    "dt_lancamento",
    "dt_processamento",
    "cod_cosif",
    "flag_estorno",
    "id_lote",
    "ano",
    "mes",
    "dia",
]
 
missing_columns = sorted(set(contract_columns) - set(bronze.columns))
if missing_columns:
    raise ValueError(f"Colunas ausentes na tabela Bronze: {missing_columns}")
 
# Filtra o lote diário usando a data e as colunas de partição da Bronze.
daily_batch = bronze.filter(
    (F.col("ano") == processing_date.year)
& (F.col("mes") == processing_date.month)
& (F.col("dia") == processing_date.day)
& (
        F.col("dt_processamento")
        == F.lit(processing_date).cast("date")
    )
)
 
if daily_batch.limit(1).count() == 0:
    raise ValueError(
        f"Não há registros na Bronze para {processing_date.isoformat()}."
    )
 
required_non_null = [
    "id_transacao",
    "id_contrato",
    "id_conta",
    "cod_agencia",
    "tipo_contrato",
    "tipo_lancamento",
    "valor_lancamento",
    "dt_lancamento",
    "dt_processamento",
    "flag_estorno",
    "id_lote",
]
 
required_strings = [
    "id_transacao",
    "id_contrato",
    "id_conta",
    "cod_agencia",
    "tipo_contrato",
    "tipo_lancamento",
    "id_lote",
]
 
required_checks = [F.col(name).isNull() for name in required_non_null]
empty_checks = [
    F.coalesce(F.trim(F.col(name)), F.lit("")) == ""
    for name in required_strings
]
invalid_required = reduce(or_, required_checks + empty_checks)
 
valid_contract_types = [
    "CC",
    "POUP",
    "CDB",
    "LCI",
    "CONSORCIO",
    "SEGURO",
]
valid_transaction_types = [
    "DEBITO",
    "CREDITO",
    "TARIFA",
    "JUROS",
    "IOF",
]
 
quality_counts = (
    daily_batch.agg(
        F.coalesce(
            F.sum(F.when(invalid_required, 1).otherwise(0)),
            F.lit(0),
        ).alias("invalid_required"),
        F.coalesce(
            F.sum(
                F.when(F.col("valor_lancamento") <= 0, 1).otherwise(0)
            ),
            F.lit(0),
        ).alias("non_positive_amount"),
        F.coalesce(
            F.sum(
                F.when(
                    F.to_date("dt_lancamento")
> F.col("dt_processamento"),
                    1,
                ).otherwise(0)
            ),
            F.lit(0),
        ).alias("invalid_dates"),
        F.coalesce(
            F.sum(
                F.when(
                    ~F.col("tipo_contrato").isin(valid_contract_types),
                    1,
                ).otherwise(0)
            ),
            F.lit(0),
        ).alias("invalid_contract_types"),
        F.coalesce(
            F.sum(
                F.when(
                    ~F.col("tipo_lancamento").isin(
                        valid_transaction_types
                    ),
                    1,
                ).otherwise(0)
            ),
            F.lit(0),
        ).alias("invalid_transaction_types"),
    )
    .first()
    .asDict()
)
 
# Verifica duplicidades dentro do lote diário.
has_duplicate_ids = (
    daily_batch.groupBy("id_transacao")
    .count()
    .where(F.col("count") > 1)
    .limit(1)
    .count()
> 0
)
 
errors = [
    name
    for name, count in quality_counts.items()
    if count > 0
]
 
if has_duplicate_ids:
    errors.append("id_transacao duplicado no lote diário")
 
if errors:
    logger.error("Falha nas validações da Silver: %s", errors)
    raise ValueError("O lote foi rejeitado pelas regras de qualidade.")
 
# Não propaga cnpj: ele não faz parte do contrato informado.
# Mantém os metadados de origem para rastreabilidade, se estiverem presentes.
lineage_columns = [
    name
    for name in ["_source_file", "_ingested_at"]
    if name in daily_batch.columns
]
 
silver = daily_batch.select(*(contract_columns + lineage_columns))
 
# A tabela é particionada por ano, mês e dia.
if spark.catalog.tableExists(target_table):
    silver.writeTo(target_table).overwritePartitions()
else:
    (
        silver.writeTo(target_table)
        .using("iceberg")
        .tableProperty("format-version", "3")
        .partitionedBy("ano", "mes", "dia")
        .create()
    )
 
logger.info(
    "Silver gravada para a data de processamento %s.",
    processing_date.isoformat(),
)
 
job.commit()