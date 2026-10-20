<div align="center">
 
# Pipeline de Dados Contábeis na AWS
 
**Pipeline batch com AWS Glue, PySpark, Apache Iceberg e Terraform**
 
![AWS](https://img.shields.io/badge/AWS-Cloud-orange?logo=amazonaws)

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)

![Apache Spark](https://img.shields.io/badge/Apache-Spark-red?logo=apachespark)

![Iceberg](https://img.shields.io/badge/Apache-Iceberg-blue)
 
</div>
 
---

 
## Objetivo
 
Construir um pipeline para processar lançamentos contábeis e calcular, nas camadas

Medallion, saldos consolidados por contrato e por conta. O projeto usa dados

sintéticos e serve como protótipo técnico; testes pequenos não demonstram, por si

só, capacidade de produção ou atendimento ao SLA do desafio.

 
## Estado do projeto
 
| Componente | Estado |

| Ingestão Bronze | Job existente lê Parquet e grava a tabela Bronze em Iceberg V3. |

| Consulta da Bronze no Athena | Athena não conseguiu ler a tabela V3 no ambiente testado. |

| Tabela alternativa para Athena | Existe uma cópia auxiliar Iceberg V2; não substitui a Bronze V3. |

| Silver | O job foi testado com sucesso; a infraestrutura e os dados de teste foram removidos. |

| Gold | Planejada para uma etapa posterior. |

| Terraform de ponta a ponta | Em evolução; o gerenciamento completo e a destruição segura ainda precisam ser implementados. |

 
## Arquitetura

 
### Protótipo existente
 
O fluxo inicialmente implementado utiliza geração de dados sintéticos, armazenamento

em S3, orquestração e processamento com AWS Glue:
 

EventBridge Scheduler
        ↓
Step Functions
        ↓
Lambda — geração de dados sintéticos
        ↓
S3 — arquivos Parquet de entrada
        ↓
AWS Glue / Spark
        ↓
S3 e Glue Data Catalog — tabela Bronze em Iceberg V3

 
### Arquitetura-alvo
 
A evolução planejada é gerenciar pelo Terraform os recursos próprios do projeto:

bucket de saída dedicado, banco Glue, papéis e políticas IAM, scripts e jobs Glue,

Step Functions, EventBridge Scheduler e monitoramento.
 
O bucket de origem `s3://mockdesafio-aws/contratos/` será tratado como entrada

externa e somente para leitura. A destruição do ambiente do projeto não deverá

apagar essa origem.
 

S3 de origem externo
        ↓
Glue Bronze — Iceberg V3
        ↓
Glue Silver — Iceberg V3
        ↓
Glue Gold — Iceberg V3 (planejada)
 
EventBridge Scheduler → Step Functions → execução dos jobs Glue

 
Os recursos existentes fora do estado Terraform não devem ser considerados

gerenciados pelo Terraform até serem importados ou substituídos por recursos próprios.

 
## Camada Bronze
 
O job existente `glue-job-aws`:
 
- Lê arquivos Parquet de `s3://mockdesafio-aws/contratos/`.

- Confere a presença das colunas esperadas pelo contrato.

- Acrescenta as colunas técnicas `_source_file` e `_ingested_at`.

- Grava `desafio_glue.fin_contabilidade_saldo_contrato_bronze` como Iceberg V3.
 
O script atual usa `createOrReplace()`. Portanto, sua execução substitui a tabela;

não representa, por si só, uma ingestão incremental diária. A estratégia de

reprocessamento deve ser definida antes de automatizar execuções recorrentes.
 
## Compatibilidade com Athena
 
No ambiente testado, o Athena retornou erro ao consultar a tabela Iceberg V3:

`Iceberg format version 3 is not supported`.
 
Existe uma tabela auxiliar chamada

`desafio_glue.fin_contabilidade_saldo_contrato_bronze_alt`, gravada em Iceberg V2

no prefixo:
 
s3://mockdesafio-iceberg/athena-alt/fin_contabilidade_saldo_contrato_bronze_alt/

Essa cópia serve apenas para consulta no Athena. Não é a tabela Bronze oficial e

deve ser atualizada ou recriada quando a Bronze original mudar.

 
## Contrato e qualidade de dados
 
O contrato de referência inclui:
 
- Identificadores de transação, contrato, conta, agência e lote.

- Tipo de contrato e tipo de lançamento.

- Valor do lançamento e datas de lançamento e processamento.

- Código COSIF e indicador de estorno.
 
As regras previstas incluem:
 
- Campos obrigatórios preenchidos.

- `id_transacao` único globalmente.

- `valor_lancamento > 0`; estornos são identificados por `flag_estorno`.

- `dt_lancamento <= dt_processamento`.

- `cod_cosif` existente no domínio de referência.
 
A presença dessas regras no contrato não significa que todas estejam implementadas.

Cada validação deve ser testada e documentada antes de ser marcada como concluída.

Registros inválidos devem ser tratados de forma explícita, sem descarte silencioso.

 
## Infraestrutura como código
 
O objetivo é que o Terraform crie e destrua os recursos próprios do ambiente de

desenvolvimento. A infraestrutura-alvo inclui:
 
- Bucket de dados dedicado ao projeto.

- Banco Glue e configuração dos jobs.

- Papéis e políticas IAM com privilégio mínimo.

- Jobs Glue para as camadas implementadas.

- Step Functions para orquestração.

- EventBridge Scheduler para agendamento.

- Logs e métricas para monitoramento.
 
O bucket de entrada continuará externo. O bucket dedicado de desenvolvimento poderá

ser removido com seus dados na destruição, sem afetar os dados de origem. O plano de

destruição deve ser revisado antes da confirmação.
 

## Testes locais
 
Com Python e as dependências do projeto instaladas:
 
python -m venv .venv

pip install -r requirements.txt

python -m pytest app/tests -q

 
## Segurança
 
- Utilize apenas dados sintéticos nos testes.

- Não inclua credenciais, chaves, arquivos `.env` ou dados pessoais no repositório.

- Revise os planos do Terraform antes de aplicar ou destruir recursos.

- Não configure a destruição do bucket de origem como parte do ambiente descartável.

 
## Limitações conhecidas
 
- O job Bronze existente faz uma leitura ampla da origem e substitui a tabela.

  A ingestão incremental e o reprocessamento idempotente ainda precisam ser definidos.

- O Athena do ambiente testado não lê a tabela Iceberg V3; a tabela `_alt` é uma

  cópia V2 para consulta.

- A execução com amostras pequenas não comprova o SLA nem a capacidade necessária

  para centenas de milhões de transações.

- Silver foi validada em um teste, mas seus recursos e dados de teste foram removidos.

- Gold ainda não foi implementada.

 