import json
import logging
import os
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.data_generator.data_factory import gerar_registros
from src.data_generator.parquet_writer import criar_parquet
from src.data_generator.s3_writer import enviar_parquet_para_s3


logger = logging.getLogger()
logger.setLevel(logging.INFO)

FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")


def obter_data_processamento(event: dict) -> date:
    """Obtém a data do evento ou usa a data atual de São Paulo."""
    detalhe = event.get("detail") or {}
    valor = event.get("processing_date") or detalhe.get("processing_date")

    if not valor:
        return datetime.now(FUSO_HORARIO).date()

    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError(
            "processing_date deve usar o formato YYYY-MM-DD"
        ) from erro


def executar(event: dict, s3_client=None) -> dict:
    """Gera os dados, converte para Parquet e envia ao S3."""
    event = event or {}

    bucket = os.environ.get("RAW_BUCKET")
    if not bucket:
        raise ValueError("Configure a variável de ambiente RAW_BUCKET")

    data_processamento = obter_data_processamento(event)

    quantidade = int(
        event.get("record_count", os.environ.get("RECORD_COUNT", "1000"))
    )
    if quantidade < 1:
        raise ValueError("record_count precisa ser maior que zero")

    # Cada execução gera um identificador usado no lote e no nome do arquivo.
    run_id = str(event.get("run_id") or uuid.uuid4())

    registros = gerar_registros(
        quantidade=quantidade,
        data_processamento=data_processamento,
        id_lote=run_id,
    )

    conteudo_parquet = criar_parquet(registros)

    uri = enviar_parquet_para_s3(
        conteudo_parquet=conteudo_parquet,
        bucket=bucket,
        data_processamento=data_processamento,
        run_id=run_id,
        prefixo_raw=os.environ.get("RAW_PREFIX", "contratos"),
        s3_client=s3_client,
    )

    resultado = {
        "status": "success",
        "record_count": len(registros),
        "processing_date": data_processamento.isoformat(),
        "run_id": run_id,
        "s3_uri": uri,
    }

    logger.info(json.dumps(resultado))
    return resultado


def lambda_handler(event, context):
    """Ponto de entrada configurado na AWS Lambda."""
    return executar(event)
