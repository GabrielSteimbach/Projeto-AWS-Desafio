import json
import logging
import os
import time
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.data_generator.data_factory import gerar_registros
from src.data_generator.parquet_writer import criar_parquet
from src.data_generator.s3_writer import enviar_parquet_para_s3


logger = logging.getLogger()
logger.setLevel(logging.INFO)

FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")


def registrar_log(evento: str, **campos) -> None:
    """Registra uma mensagem JSON estruturada no CloudWatch Logs."""
    logger.info(
        json.dumps(
            {"evento": evento, **campos},
            ensure_ascii=False,
        )
    )


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


def executar(event: dict, s3_client=None, request_id=None) -> dict:
    """Gera os dados, converte para Parquet e envia ao S3."""
    inicio = time.perf_counter()
    event = event or {}

    try:
        registrar_log(
            "execucao_iniciada",
            request_id=request_id,
            tipo_evento=type(event).__name__,
        )

        if not isinstance(event, dict):
            raise TypeError("O evento precisa ser um objeto JSON")

        bucket = os.environ.get("RAW_BUCKET")
        if not bucket:
            raise ValueError("Configure a variável de ambiente RAW_BUCKET")

        data_processamento = obter_data_processamento(event)

        quantidade = int(
            event.get("record_count", os.environ.get("RECORD_COUNT", "1000"))
        )
        if quantidade < 1:
            raise ValueError("record_count precisa ser maior que zero")

        run_id = str(event.get("run_id") or uuid.uuid4())

        registrar_log(
            "parametros_validados",
            request_id=request_id,
            bucket=bucket,
            record_count=quantidade,
            processing_date=data_processamento.isoformat(),
            run_id=run_id,
        )

        registrar_log(
            "geracao_registros_iniciada",
            record_count=quantidade,
        )
        registros = gerar_registros(
            quantidade=quantidade,
            data_processamento=data_processamento,
            id_lote=run_id,
        )
        registrar_log(
            "geracao_registros_concluida",
            record_count=len(registros),
        )

        registrar_log("conversao_parquet_iniciada")
        conteudo_parquet = criar_parquet(registros)
        registrar_log("conversao_parquet_concluida")

        prefixo_raw = os.environ.get("RAW_PREFIX", "contratos")
        registrar_log(
            "upload_s3_iniciado",
            bucket=bucket,
            prefixo=prefixo_raw,
        )
        uri = enviar_parquet_para_s3(
            conteudo_parquet=conteudo_parquet,
            bucket=bucket,
            data_processamento=data_processamento,
            run_id=run_id,
            prefixo_raw=prefixo_raw,
            s3_client=s3_client,
        )
        registrar_log("upload_s3_concluido", s3_uri=uri)

        resultado = {
            "status": "success",
            "record_count": len(registros),
            "processing_date": data_processamento.isoformat(),
            "run_id": run_id,
            "s3_uri": uri,
        }

        registrar_log(
            "execucao_concluida",
            request_id=request_id,
            duracao_ms=round((time.perf_counter() - inicio) * 1000, 2),
            **resultado,
        )
        return resultado

    except Exception as erro:
        logger.exception(
            json.dumps(
                {
                    "evento": "execucao_falhou",
                    "request_id": request_id,
                    "tipo_erro": type(erro).__name__,
                    "duracao_ms": round((time.perf_counter() - inicio) * 1000, 2),
                },
                ensure_ascii=False,
            )
        )
        raise


def lambda_handler(event, context):
    """Ponto de entrada configurado na AWS Lambda."""
    request_id = getattr(context, "aws_request_id", None)
    return executar(event, request_id=request_id)
