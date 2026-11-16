# Plano de correção da batelada das tools do Deep Research

- **Data:** 2026-11-14
- **Status encerrado em 2026-11-16:** E0 finalizada com diagnóstico inconclusivo; E1/E4/E5 concluídas; E2/E3 encerradas sem patch. E6 concluída localmente pela candidata P3 e sua integração no Positronic Q4; DR-BATCH-02 implantada. P5 instrumentada e P6 do incidente encerradas localmente, com P5.1 reconciliada por desvio. A investigação causal do OOM terminou sem identificar a causa interna. E7 concluída documentalmente. DR-BATCH-01 encerrada sem patch neste escopo; baseline histórica ausente e controller/rollback genérico não qualificado.
- **Issue de origem:** [`docs/issues/closed/2026-11-14-tools-batch-deep-research.md`](../../issues/closed/2026-11-14-tools-batch-deep-research.md)
- **Owner e único aprovador:** Bill Kopp
- **Baseline histórico:** Positronic `deep-research` 3.0.1, imagem `sha256:55e0cec23cf185fd753e2023d7f608eb381107d97458eb4294a7c68d9dec8990`, instalação revisão 23, configuração revisão 1. Não representa o estado atual; reler revisões e imagem antes de operar.
- **Escopo encerrado:** DR-BATCH-02 qualificada e implantada localmente por P3/Q1–Q6; E7 concluída documentalmente. DR-BATCH-01 permanece sem patch, com causa desconhecida, e não bloqueou essa entrega.
- **Evidência da execução E0–E3:** [seção de execução da issue](../../issues/closed/2026-11-14-tools-batch-deep-research.md#execução-de-e0e3-em-2026-11-14)
- **Fora de escopo:** publicação, alteração do manager Percival, mudança de provider/credencial, aumento de timeouts, persistência de sessões, alteração da semântica de `source_urls`, novas reproduções pagas de DR-BATCH-01 e implementação da observabilidade futura

## 1. Resultado pretendido

Entregar a correção determinística de DR-BATCH-02 sem mascarar a falha
intermitente nem enfraquecer o isolamento de processo e o hardening existentes:

1. **DR-BATCH-01:** encerrar a investigação atual como inconclusiva, sem patch.
   As falhas genéricas e o timeout observado podem ter origens diferentes; o
   sucesso posterior não comprova correção nem falta de créditos. Observabilidade
   e eventual remediação operacional de quota serão tratadas separadamente se
   houver evidência ou recorrência.
2. **DR-BATCH-02:** toda resposta normal de `research_quick_search` deve começar
   com `UNTRUSTED_CONTENT_HEADER`, inclusive a resposta vazia, preservando
   `result_count`, ordem e conteúdo dos resultados. Erros locais continuam
   começando com `Error:` e não recebem envelope de conteúdo externo.

O plano poderá ser encerrado após a entrega de DR-BATCH-02 e o registro explícito
do risco residual de DR-BATCH-01. Esse fechamento não significa que a falha
intermitente foi corrigida nem que toda dependência externa permanecerá disponível.

## 2. Princípios de execução e decisões já tomadas

- Não alterar `research_deep` por hipótese. Os IDs `crl-727bc57b`,
  `crl-1592f22c` e `crl-68cc130c` não foram correlacionados a logs internos;
  nenhum deles autoriza um patch no escopo atual.
- Não executar novas reproduções pagas de DR-BATCH-01 neste plano. Uma recorrência
  só reabre a correção se trouxer exceção/ramo demonstrados ou evidência sanitizada
  de quota/billing; falta de créditos confirmada exige ação operacional, não retry
  ou mudança arbitrária do pipeline.
- Não adicionar retry da pesquisa inteira, aumentar o deadline ou aceitar dados
  vazios como sucesso para fazer o sintoma desaparecer.
- Não substituir o worker isolado por execução in-process e não relaxar o hard
  deadline, o cleanup ou o rate limiter.
- Preservar a sanitização das respostas públicas. Stack traces, respostas do
  provider, snippets, queries e credenciais não devem ser acrescentados a logs ou
  documentos novos.
- Cada correção terá uma regressão que falha sem o patch. Testes e scans são
  evidência, não aprovações adicionais.
- Reutilizar evidência válida da mesma revisão/imagem; não repetir suíte, build,
  scan ou smoke como segunda aceitação.
- As referências de linha abaixo descrevem o checkout lido no planejamento e devem
  ser reconciliadas com o SHA efetivo antes da edição. O HEAD local
  `3782de8687226f0fc0aa7e62618242014ab0f4dd` não é atribuído à imagem sem OCI label.

## 3. Sequência e dependências

### 3.1 Atualização pelos contratos Docker do Positronic

As limitações históricas de CLI/socket/autoridade motivaram o
[plano Docker first](../../../alternative-positronic/positronic/docs/plans/POSITRONIC_DOCKER_FIRST_HOST_ADMIN_PLAN.md).
As entregas D1–D6, incorporadas no checkout Positronic até `45ae4c3437`,
incluem renderer com socket/GID/staging para servidor e reconciliador, seleção
de endpoint/Engine, tools administrativas legado/V2 comprovadas no request do
runner, dispatcher host para a CLI da release OCI e entrega de autoridade de
policy sem mount da chave privada. D3 entrega aquisição direta e recovery por
Engine/CID/owner, preservando CAS e perfil; D4 atualiza instruções/skill e D5
prepara harness, sessão com IDs/prazo e controller de corte/rollback.

A qualificação operacional local V0–V3 foi concluída por Q1–Q6 em
2026-11-16. A release Positronic Q4 `0.1.0-dev.bd0fc500bba6`, imagem
`sha256:50e78aa50b3591f826ff67d2d35a7270cf95f495f0a64efb96d396dd8ba6d09f`,
foi instalada e validada no Engine `omarchy-main`, ID
`3ff6ad9a-7b61-4001-847a-8bffd1742cc7`. Q2 comprovou build gerenciado; Q3
corrigiu seleção deprecated e comprovou Notes pelo runner V2; Q4 executou as
fixtures oficiais de integração, recovery e retries limitados; Q5 confirmou
restart na mesma Q4, bootcheck com seis MCPs prontos e TUI nova, incluindo
conferência visual de Bill. Q6 consolidou o aceite local. Esses resultados
substituem as pendências operacionais históricas de E6, sem repetir testes.

Builds gerais usam shell/CLI/Buildx/Compose no Engine autorizado. Manutenção
tipada mantém recibos, scan/SBOM e autorização; scan exato e build são operações
distintas e scan-only não autoriza promoção. A aquisição direta da imagem
selecionada não exige atualizar a allowlist legada do executor nem refazer build
ou scan para desbloqueá-la. A ponte permanece para VCS, policy e manutenção.

O [plano de recuperação Positronic](../../../alternative-positronic/positronic/docs/plans/POSITRONIC_MCP_RECONNECT_OOM_RECOVERY_PLAN.md)
é o registro canônico de P0/P3/P4/P5, sessão OOM, instalação e reintegração.
Este plano conserva o contrato e a evidência de DR-BATCH-02. Reusar provas da
mesma imagem/inputs; reconstrução só quando necessária, com identidade própria.
DR-BATCH-01 e a investigação de memória do agente são problemas distintos.

**Reconciliação com o encerramento do incidente — 2026-11-16.** Para o estado
final, prevalecem os registros “Conclusão P5 instrumentada”, “P5.1 reconciliada
com desvio”, “Consolidação desta revisão” de P6 e “Investigação causal do OOM”
do plano de recuperação. Seu resumo inicial e alguns snapshots ainda descrevem
pendências anteriores; não representam o resultado final dessas etapas.

| Registro Positronic | Resultado efetivo e efeito neste plano |
| --- | --- |
| P0/P5: sessão histórica | Inputs e parts reconciliados no limite das APIs; um turno de provider permanece sem outcome consultável e não foi repetido. Não é evidência causal de DR-BATCH-01 |
| P1/P2 e Q4: contenção | Regressão e falha MCP isolada qualificaram aquisição limitada e refresh coalescido. Não demonstram a causa do crescimento de memória |
| P3/P4 e Q1–Q6: reintegração | Candidata Deep Research `3c8f1c69…` adquirida no Engine correto, perfil preservado, cinco tools e restart/TUI qualificados; E6 concluída localmente |
| P5: observação instrumentada | Falha controlada somente em fixture, seguida de recuperação e limpeza; uso normal observado na Q4 sem novo OOM/restart. Medições limitadas às janelas registradas |
| P5.1: limpeza | Encerrada por reconciliação do desvio: prune amplo sem inventário individual e sem preservar imagens históricas de rollback. Os critérios seletivos originais não foram cumpridos |
| P6 e investigação OOM | Escopo local encerrado; causa interna não identificada, outcome de provider incerto e controller/rollback genérico não qualificado permanecem limites explícitos |

A instrumentação posterior de P5 complementou Q4/Q5: em 51 s de falha
`list-error`, houve uma reconexão explícita e três retries, totalizando quatro
eventos `create`, com CPU, memória e crescimento do audit medidos. Foi uma cópia
temporária instrumentada da fixture, usando o digest Q4 confirmado; não uma nova
execução oficial do script nem falha induzida no Deep Research operacional.
Após recuperação da fixture, duas amostras de uso normal separadas por 30 s
mostraram o servidor saudável e audit sem crescimento. Os valores e os limites
da comparação com o baseline permanecem no
[registro P5](../../../alternative-positronic/positronic/docs/plans/POSITRONIC_MCP_RECONNECT_OOM_RECOVERY_PLAN.md#conclusão-p5-instrumentada--2026-11-16).
Essas observações curtas não provam ausência de leak ou estabilidade indefinida.

Q2 comprovou um build gerenciado de `percival-notes-mcp/canonical`, não a
reexecução bem-sucedida do job Deep Research de E5. O erro desse job continua
com diagnóstico limitado ao recibo histórico; a entrega local de E5/E6 foi
concluída pelos candidatos diretos identificados em §8–§9.

| Etapa | Trabalho | Depende de | Saída verificável |
| --- | --- | --- | --- |
| E0 | Preservar baseline e esgotar a evidência acessível | acesso read-only disponível no agente | baseline registrado e limitações de diagnóstico explícitas |
| E1 | Criar regressão e corrigir DR-BATCH-02 | E0 somente para baseline | quick search envelopado e testes verdes |
| E2 | Reavaliar DR-BATCH-01 com as reproduções controladas | E0 e autorização explícita para as chamadas já realizadas | resultado do timeout e do sucesso posterior registrados |
| E3 | Decidir se DR-BATCH-01 comporta correção baseada em evidência | E2 e decisão do operador | encerramento sem patch e critérios de reabertura |
| E4 | Reconciliar a verificação local de DR-BATCH-02 | E1; reutiliza a suíte válida da mesma revisão | suíte, lint/format e diff limpos, sem revalidação redundante |
| E5 | Construir e qualificar o candidato de DR-BATCH-02 | E4 | image ID, labels e probes pertinentes à quick search |
| E6 | Aplicar no Positronic e executar smoke da quick search | E5 e solicitação explícita de rollout | mesma imagem pinada, envelope real e aquisição comprovada; baseline disponível em P3, removida depois em P5.1 |
| E7 | Atualizar issue/plano e encerrar o escopo concluído | critérios E4–E6 conforme o escopo solicitado | DR-BATCH-02 entregue e risco residual de DR-BATCH-01 explícito |

E2/E3 estão encerradas para este plano: não houve regressão nem correção de
DR-BATCH-01. Essa decisão não bloqueia E4–E7. Observabilidade e ação de quota são
trabalhos futuros independentes, não etapas ocultas desta entrega.

## 4. E0 — Baseline e diagnóstico preservado

### 4.1 Identidade e estado

- [x] Registrar `git status --short`, SHA do checkout e alterações pré-existentes;
  não sobrescrever nem incluir `.positronic/state.sqlite` em commits.
- [x] Confirmar no manager a imagem, instalação e configuração atuais antes de
  qualquer mutação futura. O baseline observado é revisão 23/configuração 1, mas
  esses números não devem ser reutilizados cegamente em um rollout posterior.
- [ ] No host, inspecionar os OCI labels da imagem `55e0cec2…`: source revision,
  source diff, versão e plataforma. **Não obtidos em E0:** naquela sessão não havia
  acesso ao Engine nem inspeção pelo executor. O manifesto localizado pertence à
  imagem distinta `4fd1d8d0…` e não foi usado como evidência. O acesso Docker foi
  qualificado depois no Positronic, mas a baseline foi removida em P5.1; não há
  inspeção retrospectiva dessa imagem disponível no Engine local.
- [x] Preservar a imagem baseline durante E0 e a aplicação P3, sem prune nessas
  etapas. Registro histórico: a limpeza ampla posterior, autorizada separadamente,
  removeu essa imagem; este item não atesta rollback disponível atualmente.

### 4.2 Recuperação dos logs

- [x] Esgotar as interfaces read-only disponíveis para localizar
  `crl-727bc57b` e `crl-1592f22c`. O socket Docker indisponível dentro do agente
  não foi contornado nem tratado como prova de que o Engine esteja parado.
- [ ] Para cada ID, registrar timestamp, tipo da exceção, ramo/stack do código,
  worker ID, `outcome`, `last_stage`, `reaped` e marcadores
  `PERCIVAL_FAILURE`/busca permitidos. **Bloqueado em E0:** os arquivos de
  execução contêm somente lease/owner/container ID, sem stdout/stderr; os IDs não
  aparecem nos logs persistidos acessíveis. Nenhum conteúdo upstream foi exposto.
- [ ] Verificar se ambos os erros têm a mesma assinatura. **Indeterminado:** sem
  exceções e stacks, não é possível agrupar ou separar as causas.

Resultado da correlação em E0:

| Correlation ID | Worker/outcome | Último stage | Ramo de `deep_research` | Exceção sanitizada | Causa demonstrada? |
| --- | --- | --- | --- | --- | --- |
| `crl-727bc57b` | não recuperado | não recuperado | não recuperado | não recuperada | não — investigação encerrada |
| `crl-1592f22c` | não recuperado | não recuperado | não recuperado | não recuperada | não — investigação encerrada |

### 4.3 Mapa de localização

Em eventual reabertura, comparar a stack com estes pontos do código atual,
sem presumir qual deles falhou:

- chamada/protocolo, subprocesso, timeout e reap: `run_research_worker` e
  `_run_worker` em `percival_research/research_worker_client.py`;
- validação de contexto/fontes/URLs: `validate_research_data` no mesmo arquivo;
- chamada do worker, reidratação de `GPTResearcher`, inserção no registry,
  extração/cache/formatação e cleanup: `_do_deep_research` em
  `percival_research/tools/deep_research.py`;
- conversão no erro público genérico e log interno: `handle_exception` em `utils.py`.

Esses caminhos continuam presentes no checkout; sua existência não correlaciona
os correlation IDs históricos a um ramo específico.

**Resultado de E0:** etapa finalizada com evidência insuficiente, não com causa
raiz identificada. Os itens não marcados em 4.1 e 4.2 registram evidências que
não puderam ser obtidas com as interfaces disponíveis; não representam ações
pendentes neste plano. Não haverá novas tentativas de diagnóstico neste plano;
acesso aos logs ou observabilidade equivalente será necessário apenas em uma
reabertura.

**Gate G1 — condição para futura correção:** como os logs não identificaram
exceção e ramo, DR-BATCH-01 permanece sem patch. Não “corrigir” apenas a mensagem
genérica nem inferir provider/retriever pela intermitência. G1 não bloqueia a
entrega independente de DR-BATCH-02.

## 5. E1 — Correção determinística de DR-BATCH-02

### 5.1 Regressões antes do patch

Editar `tests/test_tools_quick_search.py` e, somente se necessário para o
contrato MCP, o teste de transporte correspondente:

- [x] Em `test_quick_search_sucesso`, exigir
  `result.startswith(UNTRUSTED_CONTENT_HEADER)` além das asserções atuais de
  contagem, ordem e resultados. Esse teste deve falhar na implementação atual.
- [x] Adicionar resultado com `title`, `href` e `body`, sendo `body` um texto de
  injection benigno de fixture. Confirmar que o texto permanece literalmente como
  dado, que o header aparece exatamente uma vez e que nenhuma sanitização remove
  ou executa o snippet.
- [x] Em `test_quick_search_sem_resultados`, definir e verificar o contrato de
  envelope para a resposta vazia. A opção preferida é envelopar também esse ramo
  para manter todos os retornos normais da tool uniformes.
- [x] Manter `test_quick_search_rejeita_injection` e
  `test_quick_search_trata_excecao` começando com `Error:`; acrescentar asserção
  de que erros locais não são apresentados como conteúdo web.
- [x] Confirmar que métricas, acquire/release do limiter e `result_count` não
  mudam.

### 5.2 Implementação mínima

Em `percival_research/tools/quick_search.py:11-16` e `:59-88`:

- [x] Importar `wrap_untrusted_content` de `utils`.
- [x] Envolver `"\n".join(lines)` somente no retorno normal de
  `_do_quick_search`, após a conclusão da busca e da formatação.
- [x] Não envolver o retorno de `handle_exception`, erros de validação ou erro de
  admissão do rate limiter.
- [x] Aplicar o envelope uma única vez; não adicionar um segundo prefixo em
  camadas MCP, prompts ou clientes.
- [x] Preservar o schema `(query) -> str`, os nomes das tools e a estrutura
  `result_count`/`[Result N]` já consumida pelos agentes.

### 5.3 Documentação

- [x] Atualizar a descrição de `research_quick_search` e o security boundary no
  README para declarar que snippets rápidos também usam o prefixo.
- [x] Não alterar a versão do produto nem o changelog como se a correção já
  estivesse instalada; qualquer bump/release fica fora deste plano.

**Aceite DR-BATCH-02:** as regressões falham sem o patch e passam com ele; saída
normal começa com o header; erro local continua `Error:`; contagem, ordem e
conteúdo dos resultados permanecem intactos.

**Resultado de E1:** concluída no commit `e9bf7ee`. As regressões apresentaram
`3 failed, 2 passed` antes do patch e `5 passed` depois; a suíte completa registrou
`455 passed, 3 skipped`, com Ruff aprovado. A evidência completa está na issue. A
correção era apenas local ao fim de E1; a construção e a implantação posteriores
estão em E5/E6, sem alterar o resultado histórico dos testes.

## 6. E2/E3 — Encerramento de DR-BATCH-01 sem patch

### 6.1 Evidência e decisão

- [x] Executar uma única reprodução controlada da consulta original, com
  `include_context=true` e sem retry. O resultado foi timeout de 90 s com
  `correlation_id=crl-68cc130c`, sem `research_id`; worker stage e exceção interna
  não foram recuperados.
- [x] Repetir a mesma chamada uma única vez após solicitação explícita do operador.
  O resultado foi `research_id=9364add8-9a31-4b0a-8c2d-96bf935c3b06` e
  `source_count=9`, sem alteração de código ou configuração entre as observações.
- [x] Registrar que o sucesso é compatível com falha externa transitória, inclusive
  quota, mas não comprova falta de créditos nem identifica as falhas genéricas.
- [x] Encerrar as reproduções pagas e não criar teste genérico, retry, aumento de
  timeout ou alteração de provider sem uma causa demonstrada.

**Resultado de E2/E3:** etapas encerradas por decisão do operador em 2026-11-14.
DR-BATCH-01 não foi corrigida e seu mecanismo permanece desconhecido. O sucesso
posterior confirma o fluxo executado naquele momento, não uma remediação. Nenhum
arquivo de `research_deep`, worker, timeout, retry ou provider foi alterado.

### 6.2 Critérios para reabertura

| Nova evidência | Encaminhamento |
| --- | --- |
| Exceção sanitizada e ramo/stage correlacionados a uma recorrência | abrir correção específica e primeiro criar regressão que falhe sem patch |
| Status/tipo sanitizado de quota ou billing, como HTTP 402/429 | verificar créditos, quota e alertas; tratar operacionalmente, sem alterar o pipeline por hipótese |
| Timeout recorrente com `worker`, `outcome`, `last_stage` e `reaped` | diagnosticar o stage atingido; não aumentar o deadline sem demonstrar que ele é o defeito |
| Somente novo sucesso ou repetição da resposta genérica sem logs | não reabrir correção; melhorar acesso à evidência antes de novas chamadas pagas |

**Gate G2 — regressão para eventual reabertura:** um teste que passa no código sem
patch não reproduz o defeito e não autoriza correção. A regressão deve usar a mesma
assinatura e o mesmo estágio demonstrados, sem rede ou credenciais reais, e verificar
ausência de sessão/cache parcial e worker remanescente quando aplicável.

### 6.3 Observabilidade futura, fora desta entrega

Uma tarefa separada poderá preservar, com acesso read-only equivalente no host ou
no manager, `correlation_id`, worker ID, `outcome`, `last_stage`, `reaped`, tipo de
exceção allowlisted e status/classe sanitizada do provider. Não registrar queries,
prompts, corpos upstream, respostas do provider ou credenciais. Essa instrumentação
não é pré-requisito de E4–E7 e não está autorizada como parte oculta do rollout de E1.

## 7. E4 — Verificação local integrada de DR-BATCH-02

Esta etapa não depende de DR-BATCH-01. A suíte `455 passed, 3 skipped`, cobertura
`88.96%` e Ruff aprovado em `e9bf7ee` são a evidência canônica da correção atual;
não repetir essas validações enquanto o código e as dependências permanecerem os
mesmos. Executar somente as verificações necessárias se houver nova alteração de
código e revisar o diff documental no fechamento.

Comandos de referência quando uma nova validação for necessária:

```bash
uv run pytest -q --no-cov \
  tests/test_tools_quick_search.py \
  tests/test_tools_deep_research.py \
  tests/test_research_lifecycle.py

uv run pytest -q
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
git diff --check
```

- [x] Confirmar se houve `uv sync`: não houve; portanto, o patch
  `uv run python scripts/patch_gpt_researcher.py` não precisou ser reaplicado.
- [x] Registrar os totais: suíte completa `455 passed, 3 skipped`, cobertura
  `88.96%`; Ruff `check` aprovado e `format --check` confirmou 66 arquivos
  formatados. Não foi introduzido skip novo nesta reconciliação.
- [x] Revisar o diff da correção e desta reconciliação: os arquivos de código,
  testes e dependências permanecem iguais a `e9bf7ee`; a evidência de E1 continua
  válida e esta atualização altera somente este plano.
- [x] Declarar que a suíte valida DR-BATCH-02, mas não fecha nem corrige
  DR-BATCH-01.

**Resultado de E4:** concluída por reconciliação em 2026-11-15. A comparação de
`percival_research/tools/quick_search.py`, `tests/test_tools_quick_search.py`,
`pyproject.toml` e `uv.lock` com `e9bf7ee` não encontrou diferenças. A evidência
canônica de testes e Ruff acima foi reutilizada sem reexecução redundante;
`git diff --check` passou na reconciliação. DR-BATCH-01 permanece sem correção e
com causa desconhecida. E4 não constrói nem instala imagem. E5 foi inicialmente
bloqueada pelo build gerenciado, mas foi concluída depois por build direto local,
documentado abaixo; E6 foi concluída posteriormente pela integração P3/Q1–Q6 (§9).

## 8. E5 — Candidato local e probes pertinentes

- [x] Construir pela receita/manager canônico do projeto, em `linux/amd64`, com
  `VERSION` e `GIT_SHA` explícitos, registrando SHA, dirty state/diff, comando,
  plataforma, rede, image ID e OCI labels. Build direto deve ser identificado como
  tal e não como recibo gerenciado.
- [x] Executar `scripts/docker-ci-conformance.py --image <candidato>` com os
  argumentos esperados para as cinco tools e UID 1000; confirmar initialize,
  tools/list e stdout JSON-RPC puro.
- [x] Na fixture `pipeline_probe.py --mode success`, além do fluxo existente,
  verificar que a quick search retorna o header exatamente uma vez e que o fluxo
  deep → getters → relatório continua íntegro.
- [x] Não executar os probes `timeout` e `cancel` para esta entrega: E1 não altera
  worker, deadline ou cleanup. Esses probes serão pertinentes somente a uma mudança
  futura nessas camadas.
- [x] Não publicar a imagem. Scan/SBOM devem ser produzidos quando exigidos pelo
  fluxo gerenciado ou por mudança de dependências/imagem, não como aceite extra
  para código já validado. O build gerenciado falhou antes de produzir imagem;
  o build direto local não alterou dependências, Dockerfile ou imagens-base.

**Execução E5 (2026-11-15):** submissão gerenciada `canonical` pelo comando
`positronic mcp maintenance submit --project percival-deep-research --recipe
canonical --session ses_e2343746bffe4054vyfcheIXII --request-id
e5-ses-e2343746-20261115 --directory /home/bill/Projects/percival-deep-research`.
Receita efetiva: Dockerfile `Dockerfile`, plataforma `linux/amd64`, rede `none`,
timeout 120000 ms, recipe SHA-256
`6d280a491c59a6659270cd88650a2dfcf6f69077e14b0b6b8a1ac8c28745dab2`. Snapshot:
commit `23623549ad55512f222b64821d54d0610e8accd2`, dirty `true` (somente a
atualização documental de E4), context SHA-256
`0afb10e9ff5a2bbda2e9fc8506ddc5ffa3bc3d3411e8e0517e3c2ffbac6dcd1c`. Job
`9a2d2c8808dc531ec4a3d0062264d9b16c91123c61a74d03290c8d6b24a7f107` chegou à
fase `build` e falhou com exit code 1; o recibo reporta diagnóstico `unclassified`
e 21065 bytes de stderr, sem imagem/image ID. Assim, conformance e
`pipeline_probe.py --mode success` não foram executados. O Docker CLI local também
não alcança Engine (`/var/run/docker.sock` ausente); nenhum build direto foi feito.
**Diagnóstico adicional (2026-11-15):** causa provável identificada: a receita
gerenciada impõe `network=none`, enquanto o Dockerfile exige acesso a fontes
externas durante o build. `uv sync` nas linhas 43 e 54 resolve/instala dependências;
`apt-get update` na linha 147 consulta `snapshot.debian.org`. O job não tem bases
locais permitidas (`localBases: []`). Em contraste, `.github/workflows/ci.yml`
usa Buildx sem restringir a rede do build e fornece explicitamente `VERSION`,
`GIT_SHA` e `SOURCE_DATE_EPOCH`. A combinação da receita offline com um cache
ausente/incompleto explica o erro, mas o recibo sanitizado não revela qual comando
foi o primeiro a falhar; portanto, ainda não é causa-raiz confirmada. Reconsultar
`maintenance status --print-logs --log-level DEBUG` não expôs stderr, apenas os
mesmos 21065 bytes e `unclassified`; `runtime_policy_get` retornou
`policy-unavailable`. `docker version` confirmou cliente 29.9.2, mas não há Engine
local em `/var/run/docker.sock`, então não foi possível reproduzir o build direto.
Testes adicionais: `docker context ls` mostrou apenas `default` apontando para esse
socket; `docker buildx version` retornou cliente Buildx 0.39.0, mas `docker buildx
inspect` falhou ao conectar ao mesmo Engine. A ajuda de `maintenance submit` não
expõe override de rede ou build args, e `runtime_capabilities` informa
`authorityConfigured: false` para policy. Assim, não existe neste ambiente um
caminho autorizado para testar `network=default` ou fornecer bases locais. Um novo
submit com a mesma receita repetiria as mesmas condições sem distinguir a causa;
nenhuma segunda tentativa idêntica foi iniciada. Sem imagem produzida, não é
possível verificar labels OCI; o CLI de submissão tampouco expõe parâmetros para
conferir a passagem explícita de `VERSION`/`GIT_SHA`.

Naquela submissão gerenciada não houve imagem, scan, SBOM, autorização ou
publicação. O handoff proposto para alterar temporariamente a rede da receita não
foi executado; nenhum estado do manager foi alterado. A qualificação local
posterior está registrada abaixo e não confirma a causa-raiz do erro gerenciado.

### Candidato direto local (2026-11-15)

Docker Buildx no Engine local (`docker info`: `Name=omarchy-main`, Buildx driver
`docker`), sem usar o manager Positronic.
No momento do build, `HEAD=2159fe1ced4bfc7345ab489bf6a9d03b55324bc8`, worktree
limpo (`dirty=false`, diff vazio). Comando:

```bash
docker buildx build --load --platform linux/amd64 --network default \
  --provenance=false --tag percival-deep-research:e5-direct-2159fe1 \
  --build-arg VERSION=3.0.1 \
  --build-arg GIT_SHA=2159fe1ced4bfc7345ab489bf6a9d03b55324bc8 \
  --build-arg SOURCE_DATE_EPOCH=1794706976 --file Dockerfile .
```

Resultado: build direto local concluído, sem push. Image ID
`sha256:b0a9fd2e48a34050d49b34fbc89a73a867aa5446092161218005da4ee6c6affc`;
OCI labels `org.opencontainers.image.version=3.0.1` e
`org.opencontainers.image.revision=2159fe1ced4bfc7345ab489bf6a9d03b55324bc8`;
plataforma `linux/amd64`, usuário não-root `percival`, healthcheck ausente. O image
ID baseline `sha256:55e0cec23cf185fd753e2023d7f608eb381107d97458eb4294a7c68d9dec8990`
também existe nesse Engine local, o que não comprova sua disponibilidade no
manager Positronic.

Conformance executada com `MCP_TRANSPORT=stdio`, UID 1000 e as cinco tools
esperadas; resultado: initialize + tools/list aprovados, cinco tools e stdout
JSON-RPC válido. Comando:

```bash
uv run --no-sync python scripts/docker-ci-conformance.py \
  --image percival-deep-research:e5-direct-2159fe1 \
  --secret-env INFERENCE_API_KEY=ci-sentinel-not-a-secret \
  --env INFERENCE_BASE_URL=https://api.openai.com/v1 \
  --env MCP_TRANSPORT=stdio \
  --expected-tool research_quick_search \
  --expected-tool research_deep \
  --expected-tool research_get_context \
  --expected-tool research_get_sources \
  --expected-tool research_write_report \
  --expected-uid 1000 --compose-service percival-deep-research-stdio \
  --compose-profile stdio
```

O probe integrado passou em `mode=success` com fixture local:
44.134 s, duas chamadas de inferência simuladas, zero embeddings, zero workers
remanescentes e cinco tools exercitadas. O probe agora exige que a resposta da
quick search comece com `UNTRUSTED_CONTENT_HEADER` e contenha exatamente uma
ocorrência; a alteração local de harness está em `scripts/pipeline_probe.py` e foi
feita depois do build, sem alterar o código runtime incluído no candidato.
Suíte canônica após essa asserção: 455 passed, 3 skipped, cobertura 88.96%; Ruff
check e format aprovados; `git diff --check` aprovado. Não foram executados scan ou
SBOM: o build foi direto/local, sem alteração de dependências, Dockerfile ou
imagens-base, e nenhum fluxo gerenciado exigiu esses artefatos.

**Resultado de E5:** concluída para qualificação local do candidato. Isso não é
recibo de build gerenciado, não autoriza a imagem no manager e não demonstra que a
imagem baseline está disponível para rollback naquele manager. Naquele momento E6 permanecia
pendente, sem mutação de runtime nem smoke real com provider; a integração
posterior da candidata reconstruída está em §9.

## 9. E6 — Rollout de teste Positronic e smoke real

Etapa executada pela integração P3 autorizada no Positronic e concluída com
Q1–Q6; evidências e limites abaixo. A criação deste plano não autorizou publicação.

- [x] Ler imediatamente antes da mutação `positronic mcp server show deep-research`
  e as imagens/autorizações necessárias. Usar as revisões atuais, não os números
  históricos deste plano.
- [x] Confirmar que a imagem baseline estava disponível para rollback na aplicação
  P3. Essa prova é histórica: a limpeza posterior a removeu (limite abaixo).
- [x] Autorizar o candidato local se exigido e aplicar `update-image` com CAS pelo
  manager Positronic. Reaplicar a configuração vigente preservando rede, mount RO,
  variáveis e as cinco tools permitidas; não ler ou imprimir o arquivo secreto.
- [x] Executar `discover` e confirmar cinco tools e a imagem esperada. Handshake e
  `running/connected` são apenas evidência de transporte, não do pipeline.

Smoke controlado de DR-BATCH-02, sem retry automático:

1. Chamar `research_quick_search` uma única vez com uma consulta pública curta e
   confirmar header exatamente uma vez, contagem coerente e resultados preservados.
2. Em erro explícito da aplicação, registrar o correlation ID e não repetir para
   “obter sucesso”. Após timeout/erro ambíguo de transporte, inspecionar o estado
   original antes de qualquer nova chamada.
3. Não executar `research_deep`, getters ou `research_write_report` neste smoke:
   E1 não altera esse pipeline e uma falha externa intermitente não deve bloquear
   ou ser confundida com a validação do envelope da quick search.
4. Não usar `research://{topic}` como recuperação. O sucesso da pesquisa profunda
   na imagem baseline não é evidência da imagem candidata nem de DR-BATCH-01.

Um smoke real bem-sucedido demonstra o envelope da quick search na imagem
candidata. Ele não declara DR-BATCH-01 corrigida nem elimina intermitência externa.

**Situação histórica de E6 (2026-11-15, anterior à integração P3):** não executada. A interface Positronic suportada
para consultar/atualizar o servidor não estava disponível nesta sessão; o comando
`positronic` local expõe apenas `opencode attach`. A imagem candidata e a baseline
foram verificadas somente no Engine Docker local, sem prova de disponibilidade no
manager. Não houve `update-image`, alteração de runtime nem smoke real; o rollback
no manager também não pôde ser confirmado.

### Evidência posterior e critério vigente de E6

O registro P3 “candidata reconstruída e autorização” do plano de recuperação
Positronic documenta build no Engine `omarchy-main`, commit
`64e005491f63a907005276726a9fe64635023264`, árvore
`7bd9680edb6cea7b004fdaa511a64f294e7a0062` e imagem
`sha256:3c8f1c6956158b6cb1069eb8994abbebde276dddb45eafd8b3523ceed50e24c2`.
Essa imagem é distinta de `b0a9fd2…` da E5; não transferir evidência entre IDs.
O mesmo registro comprova imports, initialize/tools/list, cinco tools,
autorização local e seleção por CAS até revisão 27, com baseline preservado.
Uma única quick search pública via stdio dessa imagem retornou cinco resultados
e header exatamente uma vez, sem `research_deep`. Reusar essa evidência sem
repetir chamada paga apenas para aceitação.

**Impedimento histórico resolvido.** A primeira aquisição persistente falhou
com `execution-acquire-failed` no backend executor, sem bootcheck concluído.
A qualificação posterior em
[§12.4 do plano Docker first](../../../alternative-positronic/positronic/docs/plans/POSITRONIC_DOCKER_FIRST_HOST_ADMIN_PLAN.md#124-v3--deep-research-e-retries)
comprovou backend `direct` no servidor e reconciliador e aquisição da imagem
`sha256:3c8f1c69…` nas Locations global e projeto, com Engine/CID/owner
correlacionados. O gestor releu instalação revisão 27, configuração revisão 1,
autorização revisão 26, bridge, mount RO e cinco tools preservados. São as
revisões daquele registro, não parâmetros para nova mutação.

O bootcheck host foi concluído em Q1; Q5 comprovou restart na release Q4,
seis MCPs prontos, ownership renovado e nova TUI funcional. A janela relatada
`2026-11-16T12:50:12Z–12:58:00Z` não mostrou novos erros, restart ou OOM.
Os 12 containers MCP representam seis servidores em duas Locations legítimas.

- [x] Confirmar release compatível, Engine, interfaces e backend direto de
  servidor/reconciliador: §12.4 e Q1/Q5 do plano Docker first.
- [x] Reler imagem, perfil, revisões e baseline pelo gestor: P3/§12.4, com
  preservação da configuração. Disponibilidade da baseline limitada àquela coleta.
- [x] Comprovar aquisição direta da candidata exata, CID/Engine/owner e cinco
  tools; seis MCPs prontos e bootcheck: §12.4, Q1 e Q5.
- [x] Associar a evidência funcional ao image ID adquirido: conformance e única
  quick search via stdio da imagem `3c8f1c69…`, sem nova chamada paga. Não é
  evidência de `tools/call` mediada pelo agente nem de `research_deep`.
- [x] Registrar resultado e limite de rollback no plano do incidente e reconciliar
  E7 nesta revisão documental.

**Resultado de E6 — concluída localmente.** DR-BATCH-02 está implantada na
candidata P3, distinta da E5 `b0a9fd2…`. O smoke funcional da mesma imagem e a
prova independente de aquisição/readiness satisfazem os critérios vigentes,
sem transferir resultados entre IDs. A integração do agente não corrige
DR-BATCH-01 nem explica a causa do OOM.

**Rollback após a limpeza Docker — 2026-11-16.** A limpeza geral posteriormente
solicitada por Bill preservou as imagens em uso, inclusive Deep Research
`3c8f1c69…` e Positronic Q4. A inspeção somente leitura registrada em P5.1 confirmou
que a baseline `55e0cec2…` e o candidato E5 `b0a9fd2…` já não existem no Engine
local. A disponibilidade registrada no rollout não é garantia atual de rollback.
O [registro P5.1 do incidente](../../../alternative-positronic/positronic/docs/plans/POSITRONIC_MCP_RECONNECT_OOM_RECOVERY_PLAN.md#limpeza-posterior-autorizada--2026-11-16)
concentra resultado, desvio de inventário e limitações. P5.1 foi encerrada por
reconciliação documental, sem satisfazer os dois critérios originais de limpeza
seletiva; a lista de elegibilidade/remoção por imagem não pode ser reconstruída.
Não houve rollback acionado e esse fechamento não qualifica controller/rollback.
Antes de futura mutação,
verificar uma opção de recuperação realmente disponível pelo fluxo suportado;
esta revisão não reconstrói nem reinstala imagens históricas.

Preservar IDs de sessão, mensagem, chamada, request e recibo disponíveis sem
secrets. Após resposta perdida, consultar a operação original; prazo esgotado
ou resultado incompleto não é sucesso e não autoriza reenviar efeito/provider.
Não editar registry, policy privada ou estado do manager para contornar falhas.

## 10. E7 — Fechamento documental e rollback

**Revisão documental de 2026-11-16:** E6 reconciliada com P3/§12.4 e Q1–Q6;
DR-BATCH-02 entregue no Positronic. A falha de aquisição/bootcheck foi superada
e o restart foi qualificado. A prova V2 Notes qualifica aquele fluxo; não é uma
chamada Deep Research mediada pelo agente. O critério funcional de E6 reutiliza
o smoke stdio da mesma imagem adquirida (§9). E7 mantém
somente a atualização/organização final da issue e o arquivamento dos documentos;
nenhum teste adicional do agente, build ou smoke pago é necessário para isso.
Os arquivos permanecem nos caminhos solicitados nesta revisão.

P0/P5 foram reconciliadas, P5.1 encerrada com desvio e P6 encerrado localmente
no plano do incidente. A investigação do kernel confirmou OOM de cgroup no
`opencode` sob limite de 5 GiB, com consumo predominantemente anônimo; sem perfil
ou série temporal de alocações, não foi possível identificar a causa interna.
A tempestade de aquisições é condição observada, com contribuição plausível e
não demonstrada. Esse encerramento não declara DR-BATCH-01 corrigida, o outcome
do provider recuperado nem controller/rollback genérico qualificado. As provas e
os limites estão na
[investigação causal](../../../alternative-positronic/positronic/docs/plans/POSITRONIC_MCP_RECONNECT_OOM_RECOVERY_PLAN.md#investigação-causal-do-oom--2026-11-16)
e em P6; não são novas tarefas de E7.

E7 está concluída: o resumo da issue foi atualizado para refletir E2/E3 e E6,
inclusive o limite atual de rollback e a causa do OOM não identificada. Issue e
plano foram movidos para os respectivos diretórios `closed`. Nenhum teste
adicional, build ou smoke pago foi necessário para estas ações documentais.

- [x] Atualizar a issue com os arquivos alterados, regressões, comandos e resultados
  de DR-BATCH-02, SHA/diff, image ID e evidência do smoke quando houver. Para
  DR-BATCH-01, registrar o timeout, o sucesso posterior, a ausência de causa
  demonstrada e a decisão de não intervir; não preencher uma causa hipotética. A
  issue aponta para este registro E5, que mantém os detalhes do candidato.
- [x] Marcar DR-BATCH-02 como corrigida por `e9bf7ee` e implantada localmente
  pela integração P3/§12.4 e Q1–Q6. DR-BATCH-01 encerrada sem correção neste plano,
  com risco residual e critérios de reabertura explícitos.
- [x] Atualizar o resumo da issue com o fechamento E6 e o limite atual de rollback,
  apontando para este registro; o item de atualização acima registra a entrega
  documental anterior e não declara essa edição adicional já executada.
- [x] Mover a issue para `docs/issues/closed/` após o escopo de entrega solicitado
  ser reconciliado, amparado pela decisão explícita do operador de encerrar
  DR-BATCH-01 sem patch. O fechamento não pode declarar a intermitência eliminada.
- [x] Mover este plano para `docs/plans/closed/` quando E4–E6, conforme o escopo
  solicitado, e esta documentação estiverem reconciliados. Observabilidade futura
  não impede o fechamento e deve ter registro próprio se for executada.
- **Rollback condicional, não acionado:** se houver falha futura, reler imagem,
  revisões e opções de recuperação disponíveis pelo manager; a baseline histórica
  não existe localmente após a limpeza. Registrar o procedimento aplicável antes
  da mutação. Não editar registry/config/audit diretamente nem operar a stack
  Percival como parte desta entrega.

## 11. Riscos e controles

| Risco | Controle |
| --- | --- |
| Patch de DR-BATCH-01 tratar sintoma errado | nenhum patch neste plano; reabertura somente com stack/stage ou evidência operacional classificada |
| Hipótese de créditos tratada como causa | status/tipo sanitizado do provider; sucesso isolado não confirma quota |
| Envelope duplicado ou aplicado a erro local | wrap somente no retorno normal e testes de prefixo único/`Error:` |
| Vazamento de segredos/conteúdo em logs e issue | somente IDs, estágios, tipos allowlisted e dados públicos de fixture |
| Retry oculto aumentar custo e trabalho órfão | nenhuma nova reprodução de DR-BATCH-01; smoke restrito a uma quick search |
| Regressão de timeout/cancelamento | worker isolado preservado e probes específicos somente se essa camada mudar |
| Evidência atribuída à imagem errada | SHA/diff + OCI labels + image ID registrados no candidato e no smoke |
| Sucesso externo circunstancial confundido com correção | sucesso registrado apenas como observação; DR-BATCH-01 permanece explicitamente sem correção |
| Contenção MCP atribuída como causa resolvida do OOM | causa interna não identificada; usar as janelas limitadas P2/Q4/P5 somente para os comportamentos medidos |
| Recuperação depender de imagem removida | baseline `55e0cec2…` e E5 `b0a9fd2…` ausentes; obter e qualificar opção compatível antes de futura mutação, sem presumir controller/rollback qualificado |

## 12. Revisão contra o código — 2026-11-16

Checkout Percival `fc850dc84ef8317dd1d273d0aedd39703c284b92`, com alterações
documentais pré-existentes neste plano, além de `.obsidian/workspace.json` e
`.positronic/state.sqlite`. Esta revisão preserva essas alterações e mantém
issue/plano nos caminhos atuais. Checkout Positronic
`2252cb2732917202fd7ad67fd805d0132d095661`, com `.positronic/state.sqlite`
não rastreado e preservado.

| Código inspecionado | Contrato confirmado |
| --- | --- |
| `percival_research/tools/quick_search.py` e `utils.py` | `_do_quick_search` aplica `wrap_untrusted_content` no retorno normal, inclusive sem resultados; validação, timeout de admissão e exceção da busca retornam `Error:`. Limiter e métricas mantidos |
| `tests/test_tools_quick_search.py` e `scripts/pipeline_probe.py` | Regressões cobrem prefixo, conteúdo de fixture, contagem/resultados, resposta vazia e erros locais; probe success exige prefixo exatamente uma vez |
| `percival_research/tools/deep_research.py` e `research_worker_client.py` | Worker continua isolado em subprocesso, com timeout, kill/reap e validação; nenhum patch de DR-BATCH-01 foi acrescentado |
| Positronic `packages/opencode/src/mcp/index.ts` e `location-tools.ts` | Mutações serializadas por Location, falha estável para comando/refreshKey inalterados e eventos coalescidos em um worker de refresh; reconnect explícito ou mudança efetiva permite nova tentativa |
| Positronic `positronic/runtime/mcp-reconcile.ts` | Até três ações de reconnect por `[directory, server.id]` enquanto não observa `ready`; contador em memória, zerado em `ready` ou restart do companion, sem reset por mudança de geração/configuração |

O limite do companion não é durável nem sensível à geração. Esgotado o contador,
alterar a configuração sozinho não renova suas tentativas até observar `ready`
ou reiniciar; a tentativa interna do serviço MCP ao observar nova geração é um
controle distinto. São limites da contenção entregue, sem nova correção neste
plano.

Comparações com `e9bf7ee` confirmaram runtime Percival, Dockerfile, dependências
e regressões de quick search inalterados. A comparação com `64e0054` também
confirmou testes e probe inalterados. Reutilizadas as evidências E1/E4/E5 e P3,
sem transferir o resultado do pipeline E5 `b0a9fd2…` para a candidata P3
`3c8f1c69…`: nesta última, o pipeline probe não iniciou por ausência de `tzlocal`
no checkout Nanobot, e a evidência funcional é a quick search stdio registrada.

Verificação desta revisão documental: leitura dos contratos e diffs, conferência
das referências locais e `git diff --check`. Nenhum código, dependência, imagem,
configuração ou runtime foi alterado; não houve nova suíte, build, scan ou chamada
ao provider.
