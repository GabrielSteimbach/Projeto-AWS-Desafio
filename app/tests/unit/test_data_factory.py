from datetime import date, datetime, timedelta
from uuid import UUID

import pytest

from src.data_generator import data_factory


def contrato_teste(id_conta="000123"):
    return {
        "id_conta": id_conta,
        "cnpj": data_factory.gerar_cnpjs_unicos(1)[0],
        "id_contrato": f"CC-{id_conta}-1",
        "cod_agencia": "1234",
        "tipo_contrato": "CC",
        "cod_cosif": data_factory.COSIF_MOCK["CC"],
    }


def test_criar_contas_e_contratos():
    contratos = data_factory.criar_contas_e_contratos(8)

    assert len({item["id_conta"] for item in contratos}) == 8
    assert len({item["cod_agencia"] for item in contratos}) == 8
    assert len({item["cnpj"] for item in contratos}) == 8

    for cnpj in {item["cnpj"] for item in contratos}:
        assert len(cnpj) == 14
        assert data_factory.validar_cnpj(cnpj)

    contas = {item["id_conta"] for item in contratos}
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


def test_quantidade_padrao_gera_mil_contas_agencias_e_cnpjs():
    contratos = data_factory.criar_contas_e_contratos()

    assert len({item["id_conta"] for item in contratos}) == 1000
    assert len({item["cod_agencia"] for item in contratos}) == 1000
    assert len({item["cnpj"] for item in contratos}) == 1000


def test_cnpjs_gerados_sao_unicos_e_validos():
    cnpjs = data_factory.gerar_cnpjs_unicos(10)

    assert len(cnpjs) == 10
    assert len(set(cnpjs)) == 10
    assert all(data_factory.validar_cnpj(cnpj) for cnpj in cnpjs)


def test_validar_cnpj_rejeita_valores_invalidos():
    assert not data_factory.validar_cnpj(None)
    assert not data_factory.validar_cnpj("cnpj-invalido")


def test_gerador_tenta_novamente_se_a_base_do_cnpj_for_repetida(monkeypatch):
    bases = iter(["AAAAAAAAAAAA", "ABC123DEF456"])
    monkeypatch.setattr(
        data_factory.random,
        "choices",
        lambda population, k: list(next(bases)),
    )

    cnpj = data_factory.gerar_cnpjs_unicos(1)[0]

    assert data_factory.validar_cnpj(cnpj)


def test_calculo_cnpj_rejeita_base_com_tamanho_invalido():
    with pytest.raises(ValueError):
        data_factory._calcular_digito_verificador_cnpj("X")


@pytest.mark.parametrize("quantidade", [0, 10000])
def test_criar_contas_rejeita_quantidade_fora_do_limite(quantidade):
    with pytest.raises(ValueError):
        data_factory.criar_contas_e_contratos(quantidade)


def test_gerar_registros_com_lote_informado(monkeypatch):
    contrato = contrato_teste()
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
        assert registro["id_conta"] == "000123"
        assert registro["cnpj"] == contrato["cnpj"]
        assert data_factory.validar_cnpj(registro["cnpj"])
        assert registro["tipo_lancamento"] in data_factory.TIPOS_LANCAMENTO
        assert registro["dt_processamento"] == data_referencia
        assert registro["dt_lancamento"].date() <= data_referencia
        assert registro["dt_lancamento"].date() >= (
            data_referencia - timedelta(days=30)
        )
        assert registro["valor_lancamento"] > 0


def test_gerar_registros_gera_id_lote_se_ausente(monkeypatch):
    contrato = contrato_teste()
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


def test_gerar_registros_rejeita_menos_lancamentos_que_contas(monkeypatch):
    contratos = [
        contrato_teste("000123"),
        contrato_teste("000456"),
    ]
    monkeypatch.setattr(
        data_factory,
        "criar_contas_e_contratos",
        lambda: contratos,
    )

    with pytest.raises(ValueError, match="pelo menos"):
        data_factory.gerar_registros(1, date(2026, 10, 7))
