from datetime import date, datetime

import pytest
from botocore.exceptions import ClientError

from src.data_generator import s3_writer


class S3Falso:
    def __init__(self, erro=None):
        self.erro = erro
        self.argumentos = None

    def put_object(self, **kwargs):
        self.argumentos = kwargs
        if self.erro:
            raise self.erro


def parametros_validos():
    return {
        "conteudo_parquet": b"parquet-teste",
        "bucket": "bucket-teste",
        "data_processamento": date(2026, 10, 7),
        "run_id": "lote-1",
    }


@pytest.mark.parametrize(
    ("alteracao", "erro"),
    [
        ({"conteudo_parquet": b""}, ValueError),
        ({"bucket": ""}, ValueError),
        ({"data_processamento": datetime(2026, 10, 7)}, TypeError),
        ({"run_id": None}, ValueError),
        ({"run_id": "lote/invalido"}, ValueError),
        ({"run_id": "lote\\invalido"}, ValueError),
        ({"prefixo_raw": "/"}, ValueError),
    ],
)
def test_rejeita_parametros_invalidos(alteracao, erro):
    argumentos = parametros_validos()
    argumentos.update(alteracao)

    with pytest.raises(erro):
        s3_writer.enviar_parquet_para_s3(
            **argumentos,
            s3_client=S3Falso(),
        )


def test_envia_parquet_e_monta_uri():
    cliente = S3Falso()

    uri = s3_writer.enviar_parquet_para_s3(
        **parametros_validos(),
        prefixo_raw="/raw/",
        s3_client=cliente,
    )

    assert uri == (
        "s3://bucket-teste/raw/ano=2026/mes=10/dia=7/"
        "part-lote-1.parquet"
    )
    assert cliente.argumentos["Body"] == b"parquet-teste"
    assert cliente.argumentos["Metadata"] == {
        "dt-processamento": "2026-10-07",
        "run-id": "lote-1",
    }


def test_cria_cliente_s3_padrao_sob_demanda(monkeypatch):
    cliente = S3Falso()
    monkeypatch.setattr(s3_writer, "_s3_client", None)
    monkeypatch.setattr(
        s3_writer.boto3,
        "client",
        lambda servico: cliente,
    )

    uri = s3_writer.enviar_parquet_para_s3(**parametros_validos())

    assert uri.startswith("s3://bucket-teste/")
    assert cliente.argumentos is not None
    assert s3_writer.obter_cliente_s3() is cliente


def test_repassa_erro_do_s3():
    erro = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Acesso negado"}},
        "PutObject",
    )

    with pytest.raises(ClientError):
        s3_writer.enviar_parquet_para_s3(
            **parametros_validos(),
            s3_client=S3Falso(erro=erro),
        )
