import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME"])

sc = SparkContext.getOrCreate()
glue_context = GlueContext(sc)
spark = glue_context.spark_session

job = Job(glue_context)
job.init(args["JOB_NAME"], args)

source = (
    "glue_catalog.desafio_glue."
    "fin_contabilidade_saldo_contrato_bronze"
)
target = (
    "glue_catalog.desafio_glue."
    "fin_contabilidade_saldo_contrato_bronze_alt"
)
location = (
    "s3://mockdesafio-iceberg/athena-alt/"
    "fin_contabilidade_saldo_contrato_bronze_alt/"
)

spark.sql(f"""
    CREATE TABLE {target}
    USING iceberg
    LOCATION '{location}'
    TBLPROPERTIES ('format-version' = '2')
    AS SELECT * FROM {source}
""")

job.commit()
