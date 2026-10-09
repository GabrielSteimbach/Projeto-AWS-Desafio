from datetime import date, datetime, time, timedelta
from decimal import Decimal
import random
import uuid

from faker import Faker


fake = Faker("pt_BR")

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


def criar_contas_e_contratos(quantidade_contas: int = 250) -> list[dict]:
    """Cria contas fictícias com três a cinco contratos por conta."""
    contratos = []
    contas_criadas = set()

    while len(contas_criadas) < quantidade_contas:
        id_conta = fake.numerify(text="########")

        if id_conta in contas_criadas:
            continue

        contas_criadas.add(id_conta)
        cod_agencia = fake.numerify(text="####")

        tipos = random.sample(
            TIPOS_CONTRATO,
            k=random.randint(3, 5),
        )

        for indice, tipo in enumerate(tipos, start=1):
            contratos.append({
                "id_conta": id_conta,
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
    registros = []

    for _ in range(quantidade):
        contrato = random.choice(contratos)

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
