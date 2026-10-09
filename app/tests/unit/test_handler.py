import json
import logging
from datetime import datetime as DataHoraNativa
from types import SimpleNamespace

import pytest

from src.data_generator import handler


def eventos_json(caplog):
    resultado = []
    for registro in caplog.records:
        mensagem = registro.getMessage()
        if mensagem.startswith("{"):
            resultado.append(json.loads(mensagem))
    return resultado


def preparar_pipeline(monkeypatch):
    monkeypatch.setenv("RAW_BUCKET", "bucket-teste")

    chamadas = {}

    def gerar(**kwargs):
        chamadas["gerar"] = kwargs
        return [{"indice": i} for i in range(kwargs["quantidade"])]

    def criar(registros):
        chamadas["registros_parquet"] = registros
        return b"parquet-teste"

    def enviar(**kwargs):
        chamadas["upload"] = kwargs
        return "s3://bucket-teste/contratos/arquivo.parquet"

    monkeypatch.setattr(handler, "gerar_registros", gerar)
    monkeypatch.setattr(handler, "criar_parquet", criar)
    monkeypatch.setattr(handler, "enviar_parquet_para_s3", enviar)

    return chamadas


def test_obter_data_processamento_do_evento():
    resultado = handler.obter_data_processamento(
        {"processing_date": "2026-10-07"}
    )

    assert resultado.isoformat() == "2026-10-07"


def test_obter_data_processamento_do_detail():
    resultado = handler.obter_data_processamento(
        {"detail": {"processing_date": "2026-10-07"}}
    )

    assert resultado.isoformat() == "2026-10-07"


def test_obter_data_processamento_usa_data_atual(monkeypatch):
    class RelogioFixo:
        @staticmethod
        def now(fuso):
            return DataHoraNativa(2026, 10, 8, 12, tzinfo=fuso)

    monkeypatch.setattr(handler, "datetime", RelogioFixo)

    assert handler.obter_data_processamento({}).isoformat() == "2026-10-08"


@pytest.mark.parametrize("data_invalida", ["07/10/2026", 20261007])
def test_obter_data_processamento_rejeita_data_invalida(data_invalida):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        handler.obter_data_processamento(
            {"processing_date": data_invalida}
        )


def test_executar_com_sucesso_e_registra_logs(monkeypatch, caplog):
    chamadas = preparar_pipeline(monkeypatch)
    cliente_s3_falso = object()

    with caplog.at_level(logging.INFO):
        resultado = handler.executar(
            {
                "processing_date": "2026-10-07",
                "record_count": 5,
                "run_id": "lote-teste",
            },
            s3_client=cliente_s3_falso,
            request_id="request-teste",
        )

    assert resultado == {
        "status": "success",
        "record_count": 5,
        "processing_date": "2026-10-07",
        "run_id": "lote-teste",
        "s3_uri": "s3://bucket-teste/contratos/arquivo.parquet",
    }
    assert chamadas["gerar"]["quantidade"] == 5
    assert chamadas["upload"]["s3_client"] is cliente_s3_falso

    nomes = {evento["evento"] for evento in eventos_json(caplog)}
    assert {
        "execucao_iniciada",
        "parametros_validados",
        "geracao_registros_iniciada",
        "geracao_registros_concluida",
        "conversao_parquet_iniciada",
        "conversao_parquet_concluida",
        "upload_s3_iniciado",
        "upload_s3_concluido",
        "execucao_concluida",
    }.issubset(nomes)


def test_executar_usa_valores_padrao(monkeypatch):
    preparar_pipeline(monkeypatch)
    monkeypatch.setenv("RECORD_COUNT", "2")

    class RelogioFixo:
        @staticmethod
        def now(fuso):
            return DataHoraNativa(2026, 10, 8, 12, tzinfo=fuso)

    monkeypatch.setattr(handler, "datetime", RelogioFixo)
    monkeypatch.setattr(
        handler.uuid,
        "uuid4",
        lambda: "uuid-teste",
    )

    resultado = handler.executar(None)

    assert resultado["record_count"] == 2
    assert resultado["processing_date"] == "2026-10-08"
    assert resultado["run_id"] == "uuid-teste"


def test_executar_rejeita_evento_que_nao_seja_dicionario():
    with pytest.raises(TypeError, match="objeto JSON"):
        handler.executar([{"record_count": 1}])


def test_executar_falha_sem_bucket(monkeypatch):
    monkeypatch.delenv("RAW_BUCKET", raising=False)

    with pytest.raises(ValueError, match="RAW_BUCKET"):
        handler.executar({"record_count": 1})


@pytest.mark.parametrize("quantidade", ["invalida", 0])
def test_executar_rejeita_record_count_invalido(monkeypatch, quantidade):
    monkeypatch.setenv("RAW_BUCKET", "bucket-teste")

    with pytest.raises(ValueError):
        handler.executar({"record_count": quantidade})


def test_executar_registra_falha_da_geracao(monkeypatch, caplog):
    monkeypatch.setenv("RAW_BUCKET", "bucket-teste")

    def falhar(**kwargs):
        raise RuntimeError("falha de teste")

    monkeypatch.setattr(handler, "gerar_registros", falhar)

    with caplog.at_level(logging.INFO):
        with pytest.raises(RuntimeError, match="falha de teste"):
            handler.executar({"record_count": 1})

    assert any(
        evento["evento"] == "execucao_falhou"
        for evento in eventos_json(caplog)
    )


def test_lambda_handler_encaminha_request_id(monkeypatch):
    chamadas = {}

    def executar_falso(event, request_id=None):
        chamadas["event"] = event
        chamadas["request_id"] = request_id
        return {"status": "success"}

    monkeypatch.setattr(handler, "executar", executar_falso)

    resultado = handler.lambda_handler(
        {"teste": True},
        SimpleNamespace(aws_request_id="request-123"),
    )

    assert resultado == {"status": "success"}
    assert chamadas == {
        "event": {"teste": True},
        "request_id": "request-123",
    }

