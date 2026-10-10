from datetime import date, datetime, time, timedelta
from decimal import Decimal
import random
import re
import string
import uuid


TIPOS_CONTRATO = [
    "CC",
    "POUP",
    "CDB",
    "LCI",
    "CONSORCIO",
    "SEGURO",
]

TIPOS_LANCAMENTO = [
    "DEBITO",
    "CREDITO",
    "TARIFA",
    "JUROS",
    "IOF",
]

# Códigos fictícios para a demonstração.
# Não são códigos COSIF oficiais.
COSIF_MOCK = {
    "CC": "COSIF-MOCK-001",
    "POUP": "COSIF-MOCK-002",
    "CDB": "COSIF-MOCK-003",
    "LCI": "COSIF-MOCK-004",
    "CONSORCIO": "COSIF-MOCK-005",
    "SEGURO": "COSIF-MOCK-006",
}

CARACTERES_CNPJ = string.digits + string.ascii_uppercase
QUANTIDADE_CONTAS_PADRAO = 1000


def _calcular_digito_verificador_cnpj(base: str) -> str:
    """Calcula um dígito verificador do CNPJ alfanumérico."""
    if len(base) == 12:
        pesos = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    elif len(base) == 13:
        pesos = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    else:
        raise ValueError("A base do CNPJ precisa ter 12 ou 13 caracteres")

    soma = sum(
        (ord(caractere) - 48) * peso
        for caractere, peso in zip(base, pesos)
    )
    resto = soma % 11

    return str(0 if resto < 2 else 11 - resto)


def validar_cnpj(cnpj: str) -> bool:
    """Valida o formato e os dígitos verificadores do CNPJ alfanumérico."""
    if not isinstance(cnpj, str):
        return False

    if re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", cnpj) is None:
        return False

    base = cnpj[:12]
    primeiro_digito = _calcular_digito_verificador_cnpj(base)
    segundo_digito = _calcular_digito_verificador_cnpj(
        base + primeiro_digito
    )

    return cnpj == base + primeiro_digito + segundo_digito


def gerar_cnpjs_unicos(quantidade: int) -> list[str]:
    """Gera CNPJs alfanuméricos únicos, com dígitos verificadores."""
    cnpjs = []
    cnpjs_gerados = set()

    while len(cnpjs) < quantidade:
        base = "".join(random.choices(CARACTERES_CNPJ, k=12))

        # Evita uma base formada pelo mesmo caractere repetido.
        if len(set(base)) == 1:
            continue

        primeiro_digito = _calcular_digito_verificador_cnpj(base)
        segundo_digito = _calcular_digito_verificador_cnpj(
            base + primeiro_digito
        )
        cnpj = base + primeiro_digito + segundo_digito

        if cnpj not in cnpjs_gerados:
            cnpjs_gerados.add(cnpj)
            cnpjs.append(cnpj)

    return cnpjs


def criar_contas_e_contratos(
    quantidade_contas: int = QUANTIDADE_CONTAS_PADRAO,
) -> list[dict]:
    """Cria contas, agências e CNPJs únicos, com três a cinco contratos por conta."""
    if quantidade_contas < 1:
        raise ValueError("quantidade_contas precisa ser maior que zero")

    # Códigos de agência de 0001 a 9999: no máximo 9.999 únicos.
    if quantidade_contas > 9999:
        raise ValueError("quantidade_contas não pode exceder 9999")

    numeros_conta = random.sample(range(1, 1_000_000), quantidade_contas)
    numeros_agencia = random.sample(range(1, 10_000), quantidade_contas)
    cnpjs = gerar_cnpjs_unicos(quantidade_contas)

    contratos = []

    for numero_conta, numero_agencia, cnpj in zip(
        numeros_conta,
        numeros_agencia,
        cnpjs,
    ):
        id_conta = f"{numero_conta:06d}"
        cod_agencia = f"{numero_agencia:04d}"

        tipos = random.sample(
            TIPOS_CONTRATO,
            k=random.randint(3, 5),
        )

        for indice, tipo in enumerate(tipos, start=1):
            contratos.append({
                "id_conta": id_conta,
                "cnpj": cnpj,
                "id_contrato": f"{tipo}-{id_conta}-{indice}",
                "cod_agencia": cod_agencia,
                "tipo_contrato": tipo,
                "cod_cosif": COSIF_MOCK[tipo],
            })

    return contratos


def gerar_registros(
    quantidade: int,
    data_processamento: date,
    id_lote: str | None = None,
) -> list[dict]:
    """Gera lançamentos fictícios conforme o contrato de dados."""
    if quantidade < 1:
        raise ValueError("quantidade precisa ser maior que zero")

    if not isinstance(data_processamento, date) or isinstance(
        data_processamento, datetime
    ):
        raise TypeError("data_processamento precisa ser datetime.date")

    id_lote = id_lote or str(uuid.uuid4())
    contratos = criar_contas_e_contratos()

    contratos_por_conta = {}
    for contrato in contratos:
        contratos_por_conta.setdefault(
            contrato["id_conta"], []
        ).append(contrato)

    quantidade_contas = len(contratos_por_conta)
    if quantidade < quantidade_contas:
        raise ValueError(
            "quantidade precisa ser pelo menos igual ao número de contas "
            "para incluir todas no arquivo"
        )

    # Garante pelo menos um lançamento para cada conta.
    contratos_selecionados = [
        random.choice(contratos_da_conta)
        for contratos_da_conta in contratos_por_conta.values()
    ]

    # Lançamentos adicionais são distribuídos entre os contratos.
    contratos_selecionados.extend(
        random.choice(contratos)
        for _ in range(quantidade - quantidade_contas)
    )
    random.shuffle(contratos_selecionados)

    registros = []

    for contrato in contratos_selecionados:
        dias_antes = random.randint(0, 30)
        data_lancamento = data_processamento - timedelta(days=dias_antes)

        dt_lancamento = datetime.combine(
            data_lancamento,
            time(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            ),
        )

        valor = Decimal(random.randint(100, 500_000)).scaleb(-2)

        registros.append({
            "id_transacao": str(uuid.uuid4()),
            "id_contrato": contrato["id_contrato"],
            "id_conta": contrato["id_conta"],
            "cnpj": contrato["cnpj"],
            "cod_agencia": contrato["cod_agencia"],
            "tipo_contrato": contrato["tipo_contrato"],
            "tipo_lancamento": random.choice(TIPOS_LANCAMENTO),
            "valor_lancamento": valor,
            "dt_lancamento": dt_lancamento,
            "dt_processamento": data_processamento,
            "cod_cosif": contrato["cod_cosif"],
            "flag_estorno": random.random() < 0.01,
            "id_lote": id_lote,
        })

    return registros
