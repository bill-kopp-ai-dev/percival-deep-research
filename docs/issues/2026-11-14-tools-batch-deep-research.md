# Batelada das tools: falhas intermitentes em `research_deep` e ausência de isolamento em `research_quick_search`

- **Status:** DR-BATCH-02 corrigida e qualificada em candidato local não implantado; DR-BATCH-01 permanece sem causa demonstrada
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

Em uma reprodução controlada adicional autorizada em 2026-11-14, a primeira
consulta foi executada uma única vez, novamente com `include_context=true` e sem
retry automático. Dessa vez o resultado foi:

```text
Error: Research exceeded the 90s internal limit (correlation_id=crl-68cc130c). Try a more specific query or increase PERCIVAL_RESEARCH_TIMEOUT_S.
```

Não houve `research_id`. Essa resposta pertence ao ramo explícito de timeout, não
às respostas genéricas originalmente observadas. O novo correlation ID não foi
localizado nos logs persistidos acessíveis; worker ID, outcome, último stage e
marcadores sanitizados permanecem desconhecidos. O evento não demonstra a causa
das falhas originais nem justifica aumentar o timeout.

Após nova solicitação explícita do operador, a mesma consulta e os mesmos
argumentos foram executados mais uma única vez, sem retry adicional. A chamada
concluiu com `research_id=9364add8-9a31-4b0a-8c2d-96bf935c3b06` e
`source_count=9`. O sucesso confirma que pesquisa e inferência estavam operacionais
nesse momento, mas não demonstra que as falhas anteriores foram causadas por falta
de créditos: nenhum status do provider ou log correlacionado foi obtido. Também não
houve alteração de código ou configuração entre essas observações.

### Impacto

Quando ocorre, a falha impede a obtenção de `research_id` e bloqueia todo o fluxo
de contexto, fontes e relatório. A resposta genérica preserva o diagnóstico
sanitizado, mas, sem os logs correlacionados, não permite distinguir falha de
busca, scraping, inferência, validação ou registro da sessão.

### Limitações do diagnóstico

O socket Docker não está disponível neste ambiente do agente; a tentativa de
verificação retornou `dial unix /var/run/docker.sock: connect: no such file or
directory`. Assim, os logs dos três correlation IDs não foram inspecionados e as
causas raiz permanecem desconhecidas. Não se deve atribuir o problema ao provider,
ao retriever ou ao worker sem essa evidência.

### Próxima ação

1. Recuperar os logs/worker stages de `crl-727bc57b`, `crl-1592f22c` e, para
   classificar o evento adicional, `crl-68cc130c` no host.
2. Classificar as exceções e verificar separadamente se existe um erro transitório
   convertido no ramo genérico de `handle_exception` e qual stage atingiu o deadline.
   Para a hipótese de créditos, procurar somente status/tipo sanitizado de quota ou
   billing, como HTTP 402/429, sem copiar corpos upstream.
3. Após identificar cada causa, adicionar regressão que a reproduza e retestar o
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

### E0 — finalizada com diagnóstico inconclusivo e gate G1 ativo

- Checkout inicial preservado em `3782de8687226f0fc0aa7e62618242014ab0f4dd`, com a
  issue, o plano e `.positronic/state.sqlite` já não rastreados antes das alterações
  de código. E1 foi posteriormente commitada como `e9bf7ee`.
- O manager confirmou novamente a imagem `55e0cec2…`, instalação revisão 23 e
  configuração revisão 1. A imagem permanece autorizada e disponível; nenhuma
  mutação de runtime foi realizada.
- O Docker CLI 29.9.2 possui somente o contexto `default`, apontando para
  `unix:///var/run/docker.sock`, que continua inacessível. Não há contexto
  alternativo nem socket rootless acessível no ambiente do agente.
- O executor gerenciado anuncia somente build/scan/status/cancel/authorize/remove;
  não oferece inspeção de imagem ou logs. As execuções persistidas do manager
  contêm somente lease/owner/container ID, sem stdout/stderr, e os dois correlation
  IDs não aparecem nos logs acessíveis.
- Nenhum recibo acessível vincula a imagem baseline a um source SHA. O manifesto
  `percival-deep-research-stage2-upgrade-manifest.json` pertence à imagem distinta
  `4fd1d8d0…` e à revisão `09c3903…`; ele não foi usado para atribuir labels à
  baseline.
- **Resultado:** source revision/diff, versão/plataforma por OCI label, worker IDs,
  outcomes, últimos stages, exceções e ramos dos dois eventos permanecem
  desconhecidos. Não é possível determinar se as falhas compartilham assinatura.
  E0 está finalizada com evidência insuficiente. G1 permanece como condição para
  uma futura correção de DR-BATCH-01, sem bloquear a entrega independente de
  DR-BATCH-02; novas tentativas de diagnóstico ficam para uma eventual reabertura
  com acesso aos logs ou observabilidade equivalente.

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

Não concluídos: o gate G1 exige exceção e ramo demonstrados pelos logs, e o gate G2
exige uma regressão que falhe sem o patch. A reprodução controlada adicional gerou
`crl-68cc130c`, mas no ramo explícito de timeout de 90 s, sem expor o worker stage
ou reproduzir a resposta genérica original. Nenhum novo evento foi pesquisado por
retry. Sem evidência da causa, nenhum arquivo de `research_deep`, worker, timeout,
retry ou provider foi alterado e nenhuma regressão genérica foi criada. O
desbloqueio requer acesso read-only aos logs do host e aos OCI labels da imagem,
ou evidência equivalente que identifique o ramo e a exceção dos eventos.

## E5 — Candidato local de DR-BATCH-02 (2026-11-15)

O build gerenciado `canonical` falhou sem produzir imagem. Depois, um build direto
no Docker Engine local produziu e qualificou o candidato
`sha256:b0a9fd2e48a34050d49b34fbc89a73a867aa5446092161218005da4ee6c6affc`,
vinculado ao SHA `2159fe1ced4bfc7345ab489bf6a9d03b55324bc8`, com versão `3.0.1`.
Conformance MCP e `pipeline_probe.py --mode success` passaram usando fixtures
locais; a imagem não foi publicada nem instalada. Os detalhes do comando, labels,
probes e limites para E6 estão no [registro E5 do plano](../plans/2026-11-14-tools-batch-remediation.md#candidato-direto-local-2026-11-15).

DR-BATCH-02 continua corrigida localmente, ainda não implantada. E6 não foi
executada; DR-BATCH-01 permanece sem correção e com risco residual explícito.

## Fora do escopo desta batelada

Não foram testadas a coerção de tipos inválidos de `include_context` por cliente
MCP cru, a deduplicação de chamadas concorrentes, a saturação do rate limit, o
TTL/restart, o resource `research://{topic}` ou os prompts. O checkout local estava em
`3782de8687226f0fc0aa7e62618242014ab0f4dd`, mas essa revisão não é atribuída à
imagem sem inspeção do OCI label; os resultados acima pertencem ao image ID
explicitamente identificado no início desta issue.
