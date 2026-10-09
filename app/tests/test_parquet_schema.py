from datetime import date

import pyarrow as pa
import pyarrow.parquet as pq

from src.data_generator.data_factory import gerar_registros
from src.data_generator.parquet_writer import SCHEMA, criar_parquet


def test_parquet_preserva_quantidade_e_schema():
    registros = gerar_registros(
        quantidade=10,
        data_processamento=date(2025, 3, 8),
        id_lote="lote-teste",
    )

    conteudo = criar_parquet(registros)
    tabela = pq.read_table(pa.BufferReader(conteudo))

    assert tabela.num_rows == 10

    for campo_esperado, campo_lido in zip(SCHEMA, tabela.schema):
        assert campo_lido.name == campo_esperado.name
        assert campo_lido.type == campo_esperado.type


def test_nao_cria_parquet_sem_registros():
    try:
        criar_parquet([])
        assert False, "Era esperado um ValueError"
    except ValueError:
        pass
