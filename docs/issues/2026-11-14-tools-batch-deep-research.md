# Batelada das tools: falhas intermitentes em `research_deep` e ausência de isolamento em `research_quick_search`

- **Status:** parcialmente resolvida localmente; DR-BATCH-02 corrigida e DR-BATCH-01 bloqueada no diagnóstico
- **Reportado em:** 2026-11-14
- **Severidade proposta:** alta para DR-BATCH-01; média para DR-BATCH-02
- **Versão declarada pela instalação:** 3.0.1
- **Imagem testada:** `sha256:55e0cec23cf185fd753e2023d7f608eb381107d97458eb4294a7c68d9dec8990`
- **Runtime:** Positronic, servidor global `deep-research`, revisão 23, configuração revisão 1, transporte stdio, rede bridge
- **Escopo:** chamadas reais às cinco tools instaladas; nenhuma alteração de imagem, configuração, credencial ou instalação

## Resumo

Foram executadas 26 chamadas às cinco tools, cobrindo casos felizes, entradas
vazias, excesso de tamanho, padrões de prompt injection, IDs malformados ou
inexistentes, `include_context=true/false` e relatório padrão/customizado.

O fluxo completo pesquisa → contexto/fontes → relatório funcionou na sessão
`6b537205-851d-443b-9e23-a7ab7b01959d`, mas `research_deep` também retornou duas
falhas genéricas intermitentes. Além disso, as duas buscas rápidas bem-sucedidas
retornaram snippets externos sem o prefixo/envelope de conteúdo não confiável
exigido pelas convenções de hardening do projeto.

## Cobertura executada

| Tool | Casos observados | Resultado |
| --- | --- | --- |
| `research_deep` | 5 sucessos, 2 falhas genéricas, 2 rejeições esperadas de entrada | DR-BATCH-01 |
| `research_quick_search` | 2 sucessos com 5 resultados cada; rejeições esperadas para vazio, 531 caracteres e injection | DR-BATCH-02 |
| `research_get_context` | sucesso com ID real; UUID inexistente e ID malformado rejeitados corretamente | sem nova falha funcional |
| `research_get_sources` | sucesso com ID real; UUID inexistente e ID malformado rejeitados corretamente | sem nova falha funcional |
| `research_write_report` | relatórios padrão e customizado concluídos; ID inválido/inexistente, prompt vazio e injection rejeitados corretamente | sem nova falha funcional |

Também foi confirmado que:

- `include_context=true` devolveu contexto com `[SECURITY WARNING:...]`;
- `research_get_context` e `research_get_sources` devolveram o mesmo prefixo;
- os relatórios padrão e customizado não trouxeram bloco auxiliar `<think>`;
- consulta Unicode em português funcionou na busca rápida.

## DR-BATCH-01 — `research_deep` falha intermitentemente com erro genérico

- **Status da remediação:** bloqueada no gate G1; nenhuma alteração aplicada a este fluxo

### Evidência

A consulta abaixo foi chamada com `include_context=true` e falhou:

```text
Na documentação oficial do Python 3.12, qual é a diferença de comportamento entre asyncio.TaskGroup e asyncio.gather quando uma das tarefas falha? Cite as fontes oficiais.
```

Resposta:

```text
Error: Failed to execute 'Deep research' (correlation_id=crl-727bc57b). Check the server logs for details.
```

Uma segunda consulta válida, com `include_context=false`, também falhou:

```text
Python asyncio documentation
```

Resposta:

```text
Error: Failed to execute 'Deep research' (correlation_id=crl-1592f22c). Check the server logs for details.
```

Posteriormente, sem qualquer alteração de configuração, a primeira consulta foi
repetida com os mesmos argumentos e concluiu com:

```text
research_id: b9e6a230-52cf-4787-8a0a-7f9539359bed
source_count: 4
```

Outras quatro pesquisas válidas também concluíram nesta batelada. Portanto, a
falha não foi reproduzida de forma determinística para uma consulta fixa; o
resultado observado é de intermitência no runtime, não de rejeição permanente da
consulta.

### Impacto

Quando ocorre, a falha impede a obtenção de `research_id` e bloqueia todo o fluxo
de contexto, fontes e relatório. A resposta genérica preserva o diagnóstico
sanitizado, mas, sem os logs correlacionados, não permite distinguir falha de
busca, scraping, inferência, validação ou registro da sessão.

### Limitações do diagnóstico

O socket Docker não está disponível neste ambiente do agente; a tentativa de
verificação retornou `dial unix /var/run/docker.sock: connect: no such file or
directory`. Assim, os logs dos dois correlation IDs não foram inspecionados e a
causa raiz permanece desconhecida. Não se deve atribuir o problema ao provider,
ao retriever ou ao worker sem essa evidência.

### Próxima ação

1. Recuperar os logs/worker stages de `crl-727bc57b` e `crl-1592f22c` no host.
2. Classificar a exceção e verificar se existe um erro transitório que esteja
   sendo convertido no ramo genérico de `handle_exception`.
3. Após identificar a causa, adicionar regressão que a reproduza e retestar o
   mesmo fluxo sem repetir pesquisas pagas indiscriminadamente.

## DR-BATCH-02 — `research_quick_search` expõe snippets externos sem envelope de segurança

- **Status da remediação:** corrigida localmente; ainda não implantada na imagem gerenciada

### Evidência

As consultas `Python 3.12 asyncio TaskGroup documentation` e
`São Paulo café especial museu 2026` retornaram `result_count: 5`. Em ambas, a
saída começou diretamente com:

```text
result_count: 5

[Result 1] {'href': '...', 'body': '...', 'title': '...'}
```

Não houve `[SECURITY WARNING:...]` nem envelope XML. Na mesma batelada, os
getters de contexto/fontes e o contexto incluído por `research_deep` apresentaram
o prefixo esperado, evidenciando inconsistência entre read paths.

O campo `body` é conteúdo obtido de resultados web não verificados. Se um snippet
contiver instruções maliciosas, ele chega ao agente sem a sinalização usada pelas
demais tools.

### Comportamento esperado

Preservar o formato e a contagem dos resultados, mas envolver toda a resposta da
busca rápida com `wrap_untrusted_content` ou mecanismo equivalente, conforme a
convenção do projeto de isolar também snippets web.

### Correção e regressão sugeridas

- Aplicar o envelope no retorno de `research_quick_search`, inclusive no ramo
  `No results found.` se a resposta puder incorporar conteúdo externo futuramente.
- Adicionar teste com snippet contendo texto de injection, verificando que ele
  permanece como dado e que o prefixo/envelope está presente.
- Manter as validações de entrada existentes, que rejeitaram corretamente os
  casos maliciosos enviados diretamente como consulta.

## Evidência funcional da sessão principal

Para a sessão `6b537205-851d-443b-9e23-a7ab7b01959d`:

- `research_deep` retornou 5 fontes;
- `research_get_sources` retornou `source_count: 5`, com títulos, URLs e tamanhos;
- `research_get_context` retornou contexto não vazio e com prefixo de segurança;
- `research_write_report` concluiu tanto com `custom_prompt=null` quanto com um
  prompt customizado em português;
- não foi iniciada nova pesquisa para gerar esses relatórios.

## Execução de E0–E3 em 2026-11-14

### E0 — baseline e acesso à evidência

- Checkout preservado em `3782de8687226f0fc0aa7e62618242014ab0f4dd`, com a issue,
  o plano e `.positronic/state.sqlite` já não rastreados antes das alterações de código.
- O manager confirmou a imagem `55e0cec2…`, instalação revisão 23 e configuração
  revisão 1. A imagem permanece autorizada e disponível; nenhuma mutação de runtime
  foi realizada.
- As interfaces read-only disponíveis não expõem logs nem OCI labels. O executor
  gerenciado anuncia somente build/scan/status/cancel/authorize/remove para este
  projeto. O Docker CLI 29.9.2 está presente, mas o Engine continua inacessível por
  `unix:///var/run/docker.sock: connect: no such file or directory`.
- Os dois correlation IDs não foram localizados em logs persistidos acessíveis.
  Consequentemente, worker stage, exceção, ramo de código e labels da imagem seguem
  desconhecidos; o checkout não foi atribuído à imagem.

### E1 — DR-BATCH-02

Alterações locais:

- `percival_research/tools/quick_search.py`: aplica `wrap_untrusted_content` uma
  vez no retorno normal, inclusive para `No results found.`; erros de validação,
  admissão e exceção continuam começando com `Error:`.
- `tests/test_tools_quick_search.py`: cobre sucesso, resposta vazia, snippet com
  injection tratado literalmente como dado, prefixo único e ausência do envelope
  nos erros locais.
- `README.md` e `docker/tools.json`: documentam o prefixo também na busca rápida.

Evidência:

- Antes do patch: `.venv/bin/python -m pytest -q --no-cov tests/test_tools_quick_search.py`
  → **3 failed, 2 passed**, com as três novas asserções de envelope falhando.
- Depois do patch: o mesmo comando → **5 passed**.
- Suíte completa: `.venv/bin/python -m pytest -q` → **455 passed, 3 skipped**,
  cobertura **88.96%** (mínimo 70%).
- Ruff via `uv run --no-sync --with ruff`: `check .` → **All checks passed**;
  `format --check .` → **66 files already formatted**.
- `git diff --check` sem erros. Não houve `uv sync`, mudança de dependências ou
  necessidade de reaplicar o patch de `gpt-researcher`.

### E2/E3 — DR-BATCH-01

Não iniciados: o gate G1 exige exceção e ramo demonstrados pelos logs, e o gate G2
exige uma regressão que falhe sem o patch. Sem essa evidência, nenhum arquivo de
`research_deep`, worker, timeout, retry ou provider foi alterado. O desbloqueio
requer acesso read-only aos logs do host e aos OCI labels da imagem, ou uma nova
evidência equivalente que preserve os mesmos correlation IDs.

## Fora do escopo desta batelada

Não foram testadas a coerção de tipos inválidos de `include_context` por cliente
MCP cru, a deduplicação de chamadas concorrentes, a saturação do rate limit, o
TTL/restart, o resource `research://{topic}` ou os prompts. O checkout local estava em
`3782de8687226f0fc0aa7e62618242014ab0f4dd`, mas essa revisão não é atribuída à
imagem sem inspeção do OCI label; os resultados acima pertencem ao image ID
explicitamente identificado no início desta issue.
