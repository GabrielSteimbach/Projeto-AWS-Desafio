# Projeto AWS — Gerador de dados de contratos



Componente para gerar lançamentos financeiros sintéticos em Parquet e enviá-los ao Amazon S3. A execução é feita por uma função AWS Lambda.

> Os dados são fictícios. Os códigos COSIF gerados são exemplos mock e não representam códigos oficiais.

## Fluxo do gerador

1. A Lambda recebe a data de processamento e a quantidade de registros.
2. O módulo `data_factory` gera os lançamentos sintéticos.
3. O `parquet_writer` converte os registros para Parquet.
4. O `s3_writer` envia o arquivo ao bucket S3.
5. A execução e suas etapas são registradas no CloudWatch Logs.

## Estrutura relacionada

```text
src/data_generator/
├── handler.py
├── data_factory.py
├── parquet_writer.py
└── s3_writer.py

infra/                 # destinada à infraestrutura Terraform
tests/unit/            # testes unitários com pytest
```text

## Execução da Lambda

A função aceita um evento com `processing_date` e `record_count`. A data também pode vir dentro de `detail`.

Exemplo de evento:

```json
{
  "processing_date": "2026-10-07",
  "record_count": 5,
  "run_id": "teste-001"
}
```text

`run_id` é opcional. Se não for informado, a execução gera um identificador automaticamente. Se `processing_date` não for informado, o código usa a data atual de São Paulo.

### Variáveis de ambiente

| Variável | Obrigatória | Padrão | Descrição |
|---|---:|---|---|
| `RAW_BUCKET` | Sim | — | Bucket S3 de destino |
| `RECORD_COUNT` | Não | `1000` | Quantidade de registros quando não enviada no evento |
| `RAW_PREFIX` | Não | `contratos` | Prefixo dos arquivos no bucket |

O resultado da Lambda inclui o status, a quantidade de registros, a data de processamento, o `run_id` e a URI S3.

## Dados gerados

Cada lançamento segue o contrato usado pelo gerador:

| Campo | Tipo |
|---|---|
| `id_transacao` | STRING |
| `id_contrato` | STRING |
| `id_conta` | STRING |
| `cod_agencia` | STRING |
| `tipo_contrato` | STRING |
| `tipo_lancamento` | STRING |
| `valor_lancamento` | DECIMAL(18,2) |
| `dt_lancamento` | TIMESTAMP |
| `dt_processamento` | DATE |
| `cod_cosif` | STRING, nullable |
| `flag_estorno` | BOOLEAN |
| `id_lote` | STRING |

O gerador usa valores positivos para `valor_lancamento`, e as datas de lançamento são geradas até 30 dias antes da data de processamento. Os códigos COSIF são mock e devem ser substituídos ou validados contra uma tabela oficial para uso contábil.

## Organização no S3

O caminho segue o formato:

```text
s3://<bucket>/<prefixo>/ano=YYYY/mes=MM/dia=D/part-<run_id>.parquet
```text

Exemplo:

```text
s3://meu-bucket/contratos/ano=2026/mes=10/dia=7/part-teste-001.parquet
```text

## Desenvolvimento local

No Git Bash, na raiz do projeto:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```text

Para sair do ambiente virtual:

```bash
deactivate
```text

## Testes

Instale as ferramentas de desenvolvimento:

```bash
python -m pip install pytest pytest-cov
```text

Execute os testes com relatório de cobertura:

```bash
python -m pytest \
  --cov=src.data_generator \
  --cov-report=term-missing \
  --cov-fail-under=90
```text

A meta é atingir pelo menos 90% de cobertura no pacote `src.data_generator`. O resultado só deve ser considerado confirmado depois de a suíte estar criada e o comando terminar com sucesso.

Os testes unitários devem simular as chamadas ao S3; eles não devem gravar dados reais na AWS.

## Implantação e dependências AWS

A `.venv` local não é enviada automaticamente para a Lambda. As dependências externas, como Faker e PyArrow, precisam estar no pacote de implantação ou em layers anexadas à função.

A Lambda usada neste projeto executa em Python 3.12. Dependências com componentes compilados, como PyArrow, precisam ser empacotadas para um ambiente compatível com o runtime da Lambda — não se deve presumir que um pacote instalado no Windows funcionará na AWS.

A role de execução da Lambda precisa permitir a gravação no bucket S3 e a emissão de logs no CloudWatch.

## Verificação dos logs

No Console AWS, acesse:

**Lambda → função → Monitorar → Visualizar logs do CloudWatch**

O grupo de logs segue o formato:

```text
/aws/lambda/<nome-da-funcao>
```text

Entre os eventos estruturados esperados estão:

- `execucao_iniciada`
- `parametros_validados`
- `geracao_registros_iniciada`
- `geracao_registros_concluida`
- `conversao_parquet_iniciada`
- `conversao_parquet_concluida`
- `upload_s3_iniciado`
- `upload_s3_concluido`
- `execucao_concluida`
- `execucao_falhou`

O CloudWatch pode exibir os horários em UTC. Para converter para o horário de Brasília, subtraia três horas.

## Infraestrutura

A pasta `infra/` é reservada aos arquivos Terraform. Arquivos de estado, credenciais e variáveis com valores sensíveis não devem ser versionados.

## Contexto do desafio

O desafio propõe uma plataforma financeira com processamento distribuído em Apache Spark executado no AWS Glue, gerenciamento de metadados pelo Glue Data Catalog e escrita em Apache Iceberg V3. Também descreve saídas Gold de saldo por contrato e conta, classificação COSIF e métricas de reconciliação.

Este README descreve especificamente o componente gerador de dados. A documentação dos demais componentes deve refletir somente o que estiver implementado no repositório.
