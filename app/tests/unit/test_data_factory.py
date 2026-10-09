from datetime import date, datetime, timedelta
from uuid import UUID

import pytest

from src.data_generator import data_factory


def test_criar_contas_e_contratos():
    contratos = data_factory.criar_contas_e_contratos(8)

    contas = {item["id_conta"] for item in contratos}
    assert len(contas) == 8

    for conta in contas:
        da_conta = [
            item for item in contratos if item["id_conta"] == conta
        ]
        assert 3 <= len(da_conta) <= 5

        for contrato in da_conta:
            assert contrato["tipo_contrato"] in data_factory.TIPOS_CONTRATO
            assert contrato["cod_cosif"] == data_factory.COSIF_MOCK[
                contrato["tipo_contrato"]
            ]


def test_conta_duplicada_e_ignorada(monkeypatch):
    valores = iter([
        "11111111", "0001",  # conta e agência
        "11111111",          # conta duplicada
        "22222222", "0002",  # segunda conta e agência
    ])
    monkeypatch.setattr(
        data_factory.fake,
        "numerify",
        lambda text: next(valores),
    )

    contratos = data_factory.criar_contas_e_contratos(2)

    assert len({item["id_conta"] for item in contratos}) == 2


def test_gerar_registros_com_lote_informado(monkeypatch):
    contrato = {
        "id_conta": "12345678",
        "id_contrato": "CC-12345678-1",
        "cod_agencia": "1234",
        "tipo_contrato": "CC",
        "cod_cosif": data_factory.COSIF_MOCK["CC"],
    }
    monkeypatch.setattr(
        data_factory,
        "criar_contas_e_contratos",
        lambda: [contrato],
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
        assert registro["id_conta"] == "12345678"
        assert registro["tipo_lancamento"] in data_factory.TIPOS_LANCAMENTO
        assert registro["dt_processamento"] == data_referencia
        assert registro["dt_lancamento"].date() <= data_referencia
        assert registro["dt_lancamento"].date() >= (
            data_referencia - timedelta(days=30)
        )
        assert registro["valor_lancamento"] > 0


def test_gerar_registros_gera_id_lote_se_ausente(monkeypatch):
    contrato = {
        "id_conta": "12345678",
        "id_contrato": "CC-12345678-1",
        "cod_agencia": "1234",
        "tipo_contrato": "CC",
        "cod_cosif": data_factory.COSIF_MOCK["CC"],
    }
    monkeypatch.setattr(
        data_factory,
        "criar_contas_e_contratos",
        lambda: [contrato],
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
