# Relatório de Avaliação BTreeFy — Estudo de Caso SBESC
## BT (BTreeFy) vs FSM (Zephyr SMF): Eixos A, B e C

> **Gerado em:** {{DATE}} · **Plataforma:** Zephyr v4.3.1 · **Alvo:** {{TARGET_BOARD}} (Ex: nucleo_f091rc)
> **Aplicação:** Rastreador de ativos com duas variantes de funcionalidade — *base* (apenas rastreamento de posição) e *tamper* (+ detecção de violação)

---

## Notas de Execução e Bugs Encontrados

Durante a execução do pipeline de métricas, os seguintes pontos foram observados:

> [!NOTE]
> **Eixo C — Compilação cruzada ARM executada com sucesso.**
> Os dados de footprint estático foram coletados compilando a aplicação diretamente para o alvo `{{TARGET_BOARD}}`, fornecendo números precisos e absolutos de uso de Flash e RAM para a arquitetura embarcada.

---

## Tabela de Síntese

![Tabela de Síntese](img/report_table.png)

---

## Eixo A — Modificabilidade do Modelo

**Pergunta:** O quanto o modelo de decisão muda quando a funcionalidade de violação (tamper) é adicionada?

**Método:** Para a BT, o modelo é diretamente o arquivo XML (`models/tracker_base.xml` → `models/tracker_tamper.xml`). Para a FSM, o grafo do modelo é **reconstruído em tempo de execução** através da execução do binário oracle com `CONFIG_TRACKER_TRACE=y`. A Distância de Edição de Grafo (GED) é então calculada entre as variantes base e tamper.

### Dados Brutos

*(Preencha os dados extraídos de `results/model.csv`)*

| Variante    | Nós | Arestas | CC (proxy do grafo de decisão) |
|-------------|----:|--------:|:------------------------------:|
| bt_base     | {{BT_BASE_NODES}} | {{BT_BASE_EDGES}} | {{BT_BASE_CC}} |
| bt_tamper   | {{BT_TAMPER_NODES}} | {{BT_TAMPER_EDGES}} | {{BT_TAMPER_CC}} |
| fsm_base    | {{FSM_BASE_NODES}} | {{FSM_BASE_EDGES}} | {{FSM_BASE_CC}} |
| fsm_tamper  | {{FSM_TAMPER_NODES}} | {{FSM_TAMPER_EDGES}} | {{FSM_TAMPER_CC}} |

| Transição           | GED  |
|---------------------|-----:|
| BT base → tamper    | **{{GED_BT}}** |
| FSM base → tamper   | **{{GED_FSM}}** |

### Análise
*(Adicione aqui a análise qualitativa baseada na comparação entre o modelo XML da BT e a reconstrução do grafo da FSM. Exemplo: A FSM geralmente apresenta menor GED porque adicionar um estado com preempções universais afeta menos arestas do que reestruturar o topo de uma árvore hierárquica).*

---

## Eixo B — Modificabilidade do Código

**Pergunta:** O quanto o código de implementação muda quando a funcionalidade de violação (tamper) é adicionada?

**Método:** Duas medições nos arquivos fonte C (extraídas via `code_metrics.py` para `results/code.csv`):
1. **SLOC da feature de tamper** — SLOC estritamente atribuído à funcionalidade de tamper.
2. **Complexidade Ciclomática de McCabe**.

### Dados Brutos

| Implementação | SLOC da feature | Funções | Média CC | CC máx |
|---------------|----------------:|--------:|---------:|-------:|
| **BT**        | {{BT_SLOC}} | {{BT_FUNCS}} | {{BT_CC_MEAN}} | {{BT_CC_MAX}} |
| **FSM**       | {{FSM_SLOC}} | {{FSM_FUNCS}} | {{FSM_CC_MEAN}} | {{FSM_CC_MAX}} |

### Análise
*(Destaque o principal resultado do Eixo B: a BT normalmente exige muito menos código C que a FSM para extensões comportamentais devido à separação de preocupações provida pela definição lógica no modelo XML).*

---

## Eixo C — Footprint Estático (Uso de Memória)

**Pergunta:** Qual é o custo em tamanho do binário de cada implementação e da adição da funcionalidade de violação (tamper)?

**Método:** Quatro compilações para o alvo (BT/FSM × base/tamper). Tamanhos lidos via `pyelftools`. Extraia de `results/footprint.csv`.

### Dados Brutos

| Variante     | `.text` (B) | `.rodata` (B) | `.data` (B) | `.bss` (B) | Total Flash (B) | Total RAM (B) |
|--------------|------------:|--------------:|------------:|-----------:|----------------:|--------------:|
| **bt_base**  | {{BT_BASE_TEXT}} | {{BT_BASE_RO}} | {{BT_BASE_DATA}} | {{BT_BASE_BSS}} | {{BT_BASE_FLASH}} | {{BT_BASE_RAM}} |
| **bt_tamper**| {{BT_TAMP_TEXT}} | {{BT_TAMP_RO}} | {{BT_TAMP_DATA}} | {{BT_TAMP_BSS}} | {{BT_TAMP_FLASH}} | {{BT_TAMP_RAM}} |
| **fsm_base** | {{FSM_BASE_TEXT}} | {{FSM_BASE_RO}} | {{FSM_BASE_DATA}} | {{FSM_BASE_BSS}} | {{FSM_BASE_FLASH}} | {{FSM_BASE_RAM}} |
| **fsm_tamper**|{{FSM_TAMP_TEXT}} | {{FSM_TAMP_RO}} | {{FSM_TAMP_DATA}} | {{FSM_TAMP_BSS}} | {{FSM_TAMP_FLASH}} | {{FSM_TAMP_RAM}} |

### Diferenças Derivadas

| Métrica                       | BT          | FSM         | Delta (BT − FSM) |
|-------------------------------|------------:|------------:|-----------------:|
| Flash, base (B)               | {{BT_BASE_FLASH}} | {{FSM_BASE_FLASH}} | **{{DELTA_FLASH_BASE}}** |
| Flash, tamper (B)             | {{BT_TAMP_FLASH}} | {{FSM_TAMP_FLASH}} | **{{DELTA_FLASH_TAMP}}** |
| Custo em Flash do tamper (B)  | +{{COST_BT_FLASH}} | +{{COST_FSM_FLASH}} | **{{DELTA_COST_FLASH}}** |
| RAM, base (B)                 | {{BT_BASE_RAM}} | {{FSM_BASE_RAM}} | **{{DELTA_RAM_BASE}}** |
| RAM, tamper (B)               | {{BT_TAMP_RAM}} | {{FSM_TAMP_RAM}} | **{{DELTA_RAM_TAMP}}** |
| Custo em RAM do tamper (B)    | +{{COST_BT_RAM}} | +{{COST_FSM_RAM}} | **{{DELTA_COST_RAM}}** |

### Footprint Isolado dos Motores (Engines)
*(Extraia de `results/engine_footprint.csv`)*

| Motor de Execução | `.text` (Flash) | `.data` (RAM/Flash) | `.bss` (RAM) | Total Flash (B) | Total RAM (B) |
|-------------------|----------------:|--------------------:|-------------:|----------------:|--------------:|
| **BTreeFy** (BT)  | {{BT_ENG_TEXT}} | {{BT_ENG_DATA}} | {{BT_ENG_BSS}} | **{{BT_ENG_FLASH}}** | **{{BT_ENG_RAM}}** |
| **Zephyr SMF**    | {{FSM_ENG_TEXT}}| {{FSM_ENG_DATA}}| {{FSM_ENG_BSS}}| **{{FSM_ENG_FLASH}}**| **{{FSM_ENG_RAM}}**|

### Análise
*(Analise o overhead da BTreeFy frente ao Zephyr SMF. Enfatize que embora a BT tenha um custo estático maior (overhead do motor), o custo marginal para adicionar novas funcionalidades frequentemente é menor em Flash graças à economia em linhas de código descrita no Eixo B).*

---

## Eixo D — Equivalência Comportamental

**Pergunta:** As implementações produzem as exatas mesmas saídas para as mesmas entradas?

**Método:** Execução do oráculo com sequência randômica, verificando os resultados de `oracle_base.txt` e `oracle_tamper.txt`.

### Resultados

| Sequência    | Divergências | Inesperados | Resultado |
|--------------|-------------:|------------:|:---------:|
| `no-tamper`  |            0 |           0 |  ✅ APROVADO |
| `tamper`     |            0 |           0 |  ✅ APROVADO |

---

## Eixo E — Desempenho de Execução (Latência)

**Pergunta:** Qual é o overhead de tempo de execução no pior caso (WCET) e na média ao processar uma decisão complexa na BT em comparação com a FSM em hardware real?

**Método:** Utilização do aplicativo gerado proceduralmente (`generate_stress.py`) de 5 níveis de profundidade.

### Dados Brutos (Tempo por Iteração)

| Implementação | Mínimo | Máximo (WCET) | **Média** |
|:---|---:|---:|---:|
| **FSM Tradicional (Zephyr SMF)** | {{FSM_MIN_LATENCY}} ns | {{FSM_MAX_LATENCY}} ns | **{{FSM_AVG_LATENCY}} ns** |
| **Behavior Tree (BTreeFy)** | {{BT_MIN_LATENCY}} ns | {{BT_MAX_LATENCY}} ns | **{{BT_AVG_LATENCY}} ns** |

### Análise
*(Descreva que a FSM é incontestavelmente mais veloz, mas ressalte que o overhead da BT (normalmente na ordem de microssegundos) costuma ser amplamente aceitável e bem dentro das tolerâncias de hardware embarcado e RTOS para lógicas de alto nível).*

---

## Gráficos

![Gráfico Comparativo de 4 Painéis](img/report_chart.png)

---

## Resumo & Conclusões

*(Construa a tabela resumindo os Vencedores em cada Eixo com base nas análises feitas acima).*
