from src.data_generator.handler import executar


class S3Falso:
    def __init__(self):
        self.argumentos = None

    def put_object(self, **argumentos):
        self.argumentos = argumentos


def test_handler_gera_parquet_e_envia_para_s3(monkeypatch):
    monkeypatch.setenv("RAW_BUCKET", "bucket-de-teste")

    s3_falso = S3Falso()

    resultado = executar(
        {
            "processing_date": "2025-03-08",
            "record_count": 5,
        },
        s3_client=s3_falso,
    )

    assert resultado["status"] == "success"
    assert resultado["record_count"] == 5
    assert resultado["s3_uri"].startswith(
        "s3://bucket-de-teste/raw/fin_contabilidade_saldo_contrato/"
    )

    assert s3_falso.argumentos is not None
    assert s3_falso.argumentos["Key"].endswith(".parquet")
    assert len(s3_falso.argumentos["Body"]) > 0
