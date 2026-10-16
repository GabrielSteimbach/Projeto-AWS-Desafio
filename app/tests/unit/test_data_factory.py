import re
from datetime import date, datetime, timedelta
from uuid import UUID

import pytest

from src.data_generator import data_factory


def contrato_teste(id_conta="0000", cnpj="000000001"):
    return {
        "id_conta": id_conta,
        "cnpj": cnpj,
        "id_contrato": f"CC-{id_conta}-1",
        "cod_agencia": "0000",
        "tipo_contrato": "CC",
        "cod_cosif": data_factory.COSIF_MOCK["CC"],
    }


def test_carregar_identidades_le_csv_fixo():
    primeira = data_factory.carregar_identidades()
    segunda = data_factory.carregar_identidades()

    tuplas = {
        (linha["id_conta"], linha["agencia"], linha["cnpj"])
        for linha in primeira
    }

    assert primeira == segunda
    assert len(primeira) == 1000
    assert len(tuplas) == 1000
    assert len({linha["id_conta"] for linha in primeira}) == 1000
    assert len({linha["agencia"] for linha in primeira}) == 101
    assert len({linha["cnpj"] for linha in primeira}) == 100
    assert all(len(linha["id_conta"]) == 4 for linha in primeira)
    assert all(len(linha["agencia"]) == 4 for linha in primeira)
    assert all(
        re.fullmatch(r"0[A-Z0-9]{8}", linha["cnpj"])
        for linha in primeira
    )


def test_criar_contas_e_contratos_preserva_as_tuplas():
    primeira = data_factory.criar_contas_e_contratos(8)
    segunda = data_factory.criar_contas_e_contratos(8)

    mapa_primeiro = {
        item["id_conta"]: (item["cod_agencia"], item["cnpj"])
        for item in primeira
    }
    mapa_segundo = {
        item["id_conta"]: (item["cod_agencia"], item["cnpj"])
        for item in segunda
    }

    assert mapa_primeiro == mapa_segundo
    assert len(mapa_primeiro) == 8

    for conta in mapa_primeiro:
        contratos = [item for item in primeira if item["id_conta"] == conta]
        assert 3 <= len(contratos) <= 5

        for contrato in contratos:
            assert contrato["tipo_contrato"] in data_factory.TIPOS_CONTRATO
            assert contrato["cod_cosif"] == data_factory.COSIF_MOCK[
                contrato["tipo_contrato"]
            ]


@pytest.mark.parametrize("quantidade", [0, 1001])
def test_criar_contas_rejeita_quantidade_fora_do_limite(quantidade):
    with pytest.raises(ValueError):
        data_factory.criar_contas_e_contratos(quantidade)


def test_gerar_registros_usa_as_mil_identidades():
    registros = data_factory.gerar_registros(1000, date(2026, 10, 10))
    identidades = data_factory.carregar_identidades()

    assert len(registros) == 1000
    assert len({r["id_conta"] for r in registros}) == 1000
    assert len({r["agencia"] for r in identidades}) == 101
    assert len({r["cnpj"] for r in identidades}) == 100
    assert all(
        re.fullmatch(r"0[A-Z0-9]{8}", r["cnpj"])
        for r in registros
    )


def test_gerar_registros_com_lote_informado(monkeypatch):
    monkeypatch.setattr(
        data_factory,
        "criar_contas_e_contratos",
        lambda: [contrato_teste()],
    )

    data_referencia = date(2026, 10, 7)
    registros = data_factory.gerar_registros(
        5,
        data_referencia,
        id_lote="lote-teste",
    )

    assert len(registros) == 5

    for registro in registros:
        assert registro["id_lote"] == "lote-teste"
        assert registro["id_conta"] == "0000"
        assert registro["cnpj"] == "000000001"
        assert registro["tipo_lancamento"] in data_factory.TIPOS_LANCAMENTO
        assert registro["dt_processamento"] == data_referencia
        assert registro["dt_lancamento"].date() <= data_referencia
        assert registro["dt_lancamento"].date() >= (
            data_referencia - timedelta(days=30)
        )
        assert registro["valor_lancamento"] > 0


def test_gerar_registros_gera_id_lote_se_ausente(monkeypatch):
    monkeypatch.setattr(
        data_factory,
        "criar_contas_e_contratos",
        lambda: [contrato_teste()],
    )

    uuid_teste = UUID("12345678-1234-5678-1234-567812345678")
    monkeypatch.setattr(data_factory.uuid, "uuid4", lambda: uuid_teste)

    registros = data_factory.gerar_registros(1, date(2026, 10, 7))

    assert registros[0]["id_lote"] == str(uuid_teste)


def test_gerar_registros_rejeita_quantidade_zero():
    with pytest.raises(ValueError, match="maior que zero"):
        data_factory.gerar_registros(0, date(2026, 10, 7))


@pytest.mark.parametrize(
    "data_invalida",
    [
        datetime(2026, 10, 7),
        "2026-10-07",
    ],
)
def test_gerar_registros_rejeita_data_invalida(data_invalida):
    with pytest.raises(TypeError, match="datetime.date"):
        data_factory.gerar_registros(1, data_invalida)


def test_gerar_registros_rejeita_menos_lancamentos_que_contas(monkeypatch):
    contratos = [
        contrato_teste("0000", "000000001"),
        contrato_teste("0001", "000000002"),
    ]
    monkeypatch.setattr(
        data_factory,
        "criar_contas_e_contratos",
        lambda: contratos,
    )

    with pytest.raises(ValueError, match="pelo menos"):
        data_factory.gerar_registros(1, date(2026, 10, 7))
