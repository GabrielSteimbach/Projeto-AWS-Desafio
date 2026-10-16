<div align="center">

# Pipeline de Dados Contábeis na AWS

**Geração de dados sintéticos e ingestão na camada Bronze com AWS**

![AWS](https://img.shields.io/badge/AWS-Cloud-orange?logo=amazonaws)
![Python](https://img.shields.io/badge/Python-Lambda-blue?logo=python)
![Apache Spark](https://img.shields.io/badge/Apache-Spark-red?logo=apachespark)
![Escopo](https://img.shields.io/badge/escopo-Bronze-blue)

</div>

---

## Sobre o projeto

Protótipo de pipeline para gerar transações sintéticas em Parquet e carregá-las na camada Bronze usando AWS Lambda, AWS Step Functions e AWS Glue.

**Escopo atual:** geração dos dados e ingestão Bronze. As camadas Silver e Gold e as validações completas de qualidade de dados não fazem parte da implementação atual.

## Arquitetura

<div align="center">
 <img src="./docs/ProjetoAWS.jpg"
     alt="Diagrama da arquitetura do pipeline AWS"
     width="950" />
</div>

### Fluxo de execução

EventBridge Scheduler
        ↓
Step Functions — sf-aws-desafio
        ↓
Lambda — gerador-parquet-contratos
        ↓
S3 — arquivos Parquet de entrada
        ↓
AWS Glue — glue-job-aws
        ↓
S3 / Glue Data Catalog — camada Bronze em Iceberg V3

O agendamento está configurado para três execuções diárias, às **09:00, 13:00 e 23:00**, no fuso `America/Sao_Paulo`. A Step Functions aguarda a geração dos arquivos pela Lambda antes de iniciar o job do Glue.

## Componentes

| Componente | Responsabilidade |
|---|---|
| `gerador-parquet-contratos` | Gera dados sintéticos e arquivos Parquet de entrada. |
| `sf-aws-desafio` | Orquestra a Lambda geradora e o job do Glue. |
| `glue-job-aws` | Lê os Parquet e grava os dados na camada Bronze. |
| EventBridge Scheduler | Inicia a máquina de estados três vezes ao dia. |

## Contrato e qualidade de dados

O contrato de referência inclui identificadores de transação, contrato, conta e agência; tipo de contrato e lançamento; valor; datas de lançamento e processamento; código COSIF; indicador de estorno e identificador do lote.

As seguintes regras precisam ser validadas antes de considerar a camada Bronze completa:

- Campos obrigatórios preenchidos.
- `id_transacao` único.
- `valor_lancamento > 0`.
- `dt_lancamento <= dt_processamento`.
- `cod_cosif` existente no domínio COSIF.

A intenção é preservar os dados de origem e registrar ou encaminhar os registros inválidos, sem descartá-los silenciosamente.

## Testes locais

Com Python e as dependências do projeto instaladas:

python -m venv .venv
pip install -r requirements.txt
python -m pytest app/tests -q

## Configuração AWS

O ambiente atual utiliza a região `us-east-1`. Buckets, caminhos S3, banco e tabela do Glue Data Catalog devem ser configurados conforme o ambiente; não inclua credenciais ou chaves no código.

A execução manual ponta a ponta foi validada. A primeira execução automática do cronograma deve ser acompanhada no EventBridge e no histórico de execuções da Step Functions.

## Próximas etapas

- Implementar e testar as regras de qualidade de dados.
- Registrar métricas de registros aceitos e rejeitados.
- Avaliar reprocessamento idempotente e ingestão incremental.
- Desenvolver as camadas Silver e Gold.
- Medir desempenho com volumes representativos antes de afirmar capacidade de produção.

## Segurança

Os arquivos de entrada devem conter somente dados sintéticos. Não publique dados pessoais ou regulatórios, credenciais, arquivos `.env` ou o PDF confidencial do desafio.
