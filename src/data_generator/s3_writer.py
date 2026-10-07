import json
import logging
from datetime import date, datetime

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)

_s3_client = boto3.client("s3")


def enviar_parquet_para_s3(
    conteudo_parquet: bytes,
    bucket: str,
    data_processamento: date,
    run_id: str,
    prefixo_raw: str = "contratos",
    s3_client=None,
) -> str:
    """Envia um arquivo Parquet ao S3 e retorna sua URI."""
    if not conteudo_parquet:
        raise ValueError("O conteúdo Parquet não pode estar vazio")

    if not bucket:
        raise ValueError("O nome do bucket é obrigatório")

    if not isinstance(data_processamento, date) or isinstance(
        data_processamento, datetime
    ):
        raise TypeError("data_processamento precisa ser datetime.date")

    if not run_id or "/" in run_id or "\\" in run_id:
        raise ValueError("run_id deve ser informado e não pode conter barras")

    prefixo = prefixo_raw.strip("/")
    if not prefixo:
        raise ValueError("prefixo_raw não pode estar vazio")

    ano = f"{data_processamento.year:04d}"
    mes = f"{data_processamento.month:02d}"
    dia = str(data_processamento.day)
    data_formatada = data_processamento.isoformat()

    chave = (
        f"{prefixo}/"
        f"ano={ano}/"
        f"mes={mes}/"
        f"dia={dia}/"
        f"part-{run_id}.parquet"
    )

    cliente = s3_client or _s3_client

    try:
        cliente.put_object(
            Bucket=bucket,
            Key=chave,
            Body=conteudo_parquet,
            ContentType="application/vnd.apache.parquet",
            Metadata={
                "dt-processamento": data_formatada,
                "run-id": run_id,
            },
        )
    except ClientError:
        logger.exception(
            "Falha ao enviar Parquet para o S3",
            extra={"bucket": bucket, "key": chave, "run_id": run_id},
        )
        raise

    uri = f"s3://{bucket}/{chave}"

    logger.info(json.dumps({
        "event": "parquet_uploaded",
        "bucket": bucket,
        "key": chave,
        "uri": uri,
        "run_id": run_id,
        "dt_processamento": data_formatada,
    }))

    return uri
