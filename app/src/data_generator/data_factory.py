import csv
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
import random
import re
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

QUANTIDADE_IDENTIDADES = 1000
CAMINHO_IDENTIDADES = (
    Path(__file__).resolve().parent / "data" / "identidades.csv"
)


def carregar_identidades() -> list[dict[str, str]]:
    """Lê e valida as identidades fixas do CSV do projeto."""
    if not CAMINHO_IDENTIDADES.is_file():
        raise FileNotFoundError(
            f"Arquivo de identidades não encontrado: {CAMINHO_IDENTIDADES}"
        )

    with CAMINHO_IDENTIDADES.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as arquivo:
        leitor = csv.DictReader(arquivo)

        colunas_esperadas = ["id_conta", "agencia", "cnpj"]
        if leitor.fieldnames != colunas_esperadas:
            raise ValueError(
                f"O CSV precisa ter estas colunas: {colunas_esperadas}"
            )

        identidades = [
            {
                "id_conta": (linha["id_conta"] or "").strip(),
                "agencia": (linha["agencia"] or "").strip(),
                "cnpj": (linha["cnpj"] or "").strip().upper(),
            }
            for linha in leitor
        ]

    if len(identidades) != QUANTIDADE_IDENTIDADES:
        raise ValueError(
            f"O CSV precisa ter {QUANTIDADE_IDENTIDADES} identidades; "
            f"foram encontradas {len(identidades)}"
        )

    tuplas = set()

    for identidade in identidades:
        if re.fullmatch(r"\d{4}", identidade["id_conta"]) is None:
            raise ValueError(
                f"id_conta inválido no CSV: {identidade['id_conta']}"
            )

        if re.fullmatch(r"\d{4}", identidade["agencia"]) is None:
            raise ValueError(
                f"Agência inválida no CSV: {identidade['agencia']}"
            )

        # Identificador fictício: nove caracteres alfanuméricos,
        # começando com zero. Não é um CNPJ fiscal válido.
        if re.fullmatch(r"0[A-Z0-9]{8}", identidade["cnpj"]) is None:
            raise ValueError(
                f"Identificador CNPJ inválido no CSV: {identidade['cnpj']}"
            )

        tupla = (
            identidade["id_conta"],
            identidade["agencia"],
            identidade["cnpj"],
        )

        if tupla in tuplas:
            raise ValueError(f"Tupla duplicada no CSV: {tupla}")

        tuplas.add(tupla)

    return identidades


def criar_contas_e_contratos(
    quantidade_contas: int = QUANTIDADE_IDENTIDADES,
) -> list[dict]:
    """Cria contratos usando as identidades fixas do CSV."""
    identidades = carregar_identidades()

    if quantidade_contas < 1:
        raise ValueError("quantidade_contas precisa ser maior que zero")

    if quantidade_contas > len(identidades):
        raise ValueError(
            f"quantidade_contas não pode exceder {len(identidades)}"
        )

    contratos = []

    for identidade in identidades[:quantidade_contas]:
        id_conta = identidade["id_conta"]
        cnpj = identidade["cnpj"]
        cod_agencia = identidade["agencia"]

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
    """Gera lançamentos usando as identidades fixas do CSV."""
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

    # Distribui os lançamentos adicionais entre os contratos.
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
