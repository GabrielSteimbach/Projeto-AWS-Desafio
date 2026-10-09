from datetime import date
from decimal import Decimal

import pytest

from src.data_generator.data_factory import gerar_registros


def test_gera_a_quantidade_solicitada():
    registros = gerar_registros(
        quantidade=1000,
        data_processamento=date(2025, 3, 8),
        id_lote="lote-teste",
    )

    assert len(registros) == 1000


def test_id_transacao_e_unico_no_lote():
    registros = gerar_registros(
        quantidade=1000,
        data_processamento=date(2025, 3, 8),
        id_lote="lote-teste",
    )

    ids = [registro["id_transacao"] for registro in registros]

    assert len(ids) == len(set(ids))


def test_campos_e_regras_basicas():
    data_processamento = date(2025, 3, 8)
    registros = gerar_registros(
        quantidade=100,
        data_processamento=data_processamento,
        id_lote="lote-teste",
    )

    campos_esperados = {
        "id_transacao",
        "id_contrato",
        "id_conta",
        "cod_agencia",
        "tipo_contrato",
        "tipo_lancamento",
        "valor_lancamento",
        "dt_lancamento",
        "dt_processamento",
        "cod_cosif",
        "flag_estorno",
        "id_lote",
    }

    for registro in registros:
        assert set(registro.keys()) == campos_esperados
        assert isinstance(registro["valor_lancamento"], Decimal)
        assert registro["valor_lancamento"] > 0
        assert registro["dt_lancamento"].date() <= data_processamento
        assert registro["dt_processamento"] == data_processamento
        assert registro["id_lote"] == "lote-teste"


def test_rejeita_quantidade_zero():
    with pytest.raises(ValueError):
        gerar_registros(
            quantidade=0,
            data_processamento=date(2025, 3, 8),
        )
