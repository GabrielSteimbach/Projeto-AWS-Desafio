import pyarrow as pa
import pyarrow.parquet as pq


SCHEMA = pa.schema([
    pa.field("id_transacao", pa.string(), nullable=False),
    pa.field("id_contrato", pa.string(), nullable=False),
    pa.field("id_conta", pa.string(), nullable=False),
    pa.field("cod_agencia", pa.string(), nullable=False),
    pa.field("tipo_contrato", pa.string(), nullable=False),
    pa.field("tipo_lancamento", pa.string(), nullable=False),
    pa.field("valor_lancamento", pa.decimal128(18, 2), nullable=False),
    pa.field("dt_lancamento", pa.timestamp("us"), nullable=False),
    pa.field("dt_processamento", pa.date32(), nullable=False),
    pa.field("cod_cosif", pa.string(), nullable=True),
    pa.field("flag_estorno", pa.bool_(), nullable=False),
    pa.field("id_lote", pa.string(), nullable=False),
])


def criar_parquet(registros: list[dict]) -> bytes:
    """Converte registros para bytes no formato Parquet."""
    if not registros:
        raise ValueError("Não é possível criar Parquet sem registros")

    tabela = pa.Table.from_pylist(registros, schema=SCHEMA)

    buffer = pa.BufferOutputStream()
    pq.write_table(tabela, buffer, compression="snappy")

    return buffer.getvalue().to_pybytes()
