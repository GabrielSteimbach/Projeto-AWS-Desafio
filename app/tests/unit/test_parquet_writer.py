from datetime import date, datetime
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.data_generator import parquet_writer


def registro_valido():
    return {
        "id_transacao": "transacao-1",
        "id_contrato": "CC-123-1",
        "id_conta": "123",
        "cod_agencia": "456",
        "tipo_contrato": "CC",
        "tipo_lancamento": "DEBITO",
        "valor_lancamento": Decimal("12.34"),
        "dt_lancamento": datetime(2026, 10, 7, 12, 30),
        "dt_processamento": date(2026, 10, 7),
        "cod_cosif": "COSIF-MOCK-001",
        "flag_estorno": False,
        "id_lote": "lote-1",
    }


def test_criar_parquet_produz_arquivo_legivel():
    conteudo = parquet_writer.criar_parquet([registro_valido()])
    tabela = pq.read_table(pa.BufferReader(conteudo))

    assert tabela.schema.names == parquet_writer.SCHEMA.names
    assert tabela.num_rows == 1
    assert tabela.to_pylist()[0]["id_transacao"] == "transacao-1"


def test_criar_parquet_rejeita_lista_vazia():
    with pytest.raises(ValueError, match="sem registros"):
        parquet_writer.criar_parquet([])
