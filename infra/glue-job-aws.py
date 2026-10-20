import sys
import logging

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

args = getResolvedOptions(sys.argv, ["JOB_NAME"])

sc = SparkContext.getOrCreate()
glue_context = GlueContext(sc)
spark = glue_context.spark_session

job = Job(glue_context)
job.init(args["JOB_NAME"], args)

caminho_entrada = "s3://mockdesafio-aws/contratos/"
tabela_bronze = (
    "glue_catalog.desafio_glue."
    "fin_contabilidade_saldo_contrato_bronze"
)

logger.info("Lendo arquivos Parquet de %s", caminho_entrada)
dados = spark.read.parquet(caminho_entrada)

colunas_esperadas = [
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
]

colunas_ausentes = sorted(set(colunas_esperadas) - set(dados.columns))
if colunas_ausentes:
    raise ValueError(
        f"Colunas obrigatórias ausentes na origem: {colunas_ausentes}"
    )

dados = (
    dados
    .withColumn("_source_file", F.input_file_name())
    .withColumn("_ingested_at", F.current_timestamp())
)

logger.info("Gravando tabela Iceberg Bronze: %s", tabela_bronze)

(
    dados.writeTo(tabela_bronze)
    .using("iceberg")
    .tableProperty("format-version", "3")
    .createOrReplace()
)

job.commit()
logger.info("Job concluído.")
