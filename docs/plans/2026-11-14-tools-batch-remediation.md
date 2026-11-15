# Plano de correção da batelada das tools do Deep Research

- **Data:** 2026-11-14
- **Status:** E0 finalizada com diagnóstico inconclusivo; E1 concluída localmente; E2/E3 encerradas sem patch por decisão do operador; entrega de E1 pendente
- **Issue de origem:** [`docs/issues/2026-11-14-tools-batch-deep-research.md`](../issues/2026-11-14-tools-batch-deep-research.md)
- **Owner e único aprovador:** Bill Kopp
- **Runtime observado:** Positronic `deep-research` 3.0.1, imagem `sha256:55e0cec23cf185fd753e2023d7f608eb381107d97458eb4294a7c68d9dec8990`, instalação revisão 23, configuração revisão 1
- **Escopo atual:** entregar DR-BATCH-02 por verificação local, candidato rastreável e rollout somente quando expressamente solicitado; DR-BATCH-01 permanece sem correção e não bloqueia essa entrega
- **Evidência da execução E0–E3:** [seção de execução da issue](../issues/2026-11-14-tools-batch-deep-research.md#execução-de-e0e3-em-2026-11-14)
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

| Etapa | Trabalho | Depende de | Saída verificável |
| --- | --- | --- | --- |
| E0 | Preservar baseline e esgotar a evidência acessível | acesso read-only disponível no agente | baseline registrado e limitações de diagnóstico explícitas |
| E1 | Criar regressão e corrigir DR-BATCH-02 | E0 somente para baseline | quick search envelopado e testes verdes |
| E2 | Reavaliar DR-BATCH-01 com as reproduções controladas | E0 e autorização explícita para as chamadas já realizadas | resultado do timeout e do sucesso posterior registrados |
| E3 | Decidir se DR-BATCH-01 comporta correção baseada em evidência | E2 e decisão do operador | encerramento sem patch e critérios de reabertura |
| E4 | Reconciliar a verificação local de DR-BATCH-02 | E1; reutiliza a suíte válida da mesma revisão | suíte, lint/format e diff limpos, sem revalidação redundante |
| E5 | Construir e qualificar o candidato de DR-BATCH-02 | E4 | image ID, labels e probes pertinentes à quick search |
| E6 | Aplicar no Positronic e executar smoke da quick search | E5 e solicitação explícita de rollout | mesma imagem pinada, envelope real e rollback preservado |
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
  source diff, versão e plataforma. **Bloqueado em E0:** não há contexto Docker
  alternativo, socket acessível ou operação de inspeção no executor. O manifesto
  localizado pertence à imagem distinta `4fd1d8d0…` e não foi usado como evidência.
- [x] Preservar a imagem baseline para rollback; não remover imagens nem executar
  prune.

### 4.2 Recuperação dos logsexit

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

Comparar a stack com estes pontos, sem presumir qual deles falhou:

- chamada/protocolo do worker: `percival_research/tools/deep_research.py:138-153`
  e `percival_research/research_worker_client.py:80-160`;
- validação de contexto/fontes/URLs: `research_worker_client.py:163-192`;
- reidratação de `GPTResearcher`: `deep_research.py:153-165`;
- inserção no registry: `deep_research.py:166-177`;
- extração/cache/formatação: `deep_research.py:180-197`;
- conversão no erro genérico e log interno: `utils.py:704-722`.

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
correção permanece local: nenhuma imagem nova, rollout ou release foi realizado.

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
com causa desconhecida. E4 não constrói nem instala imagem. E5 está registrada
abaixo como bloqueada; E6 segue pendente conforme o escopo autorizado.

## 8. E5 — Candidato local e probes pertinentes

- [ ] Construir pela receita/manager canônico do projeto, em `linux/amd64`, com
  `VERSION` e `GIT_SHA` explícitos, registrando SHA, dirty state/diff, comando,
  plataforma, rede, image ID e OCI labels. Um build direto, se utilizado, deve ser
  identificado como tal e não como recibo gerenciado.
- [ ] Executar `scripts/docker-ci-conformance.py --image <candidato>` com os
  argumentos esperados para as cinco tools e UID 1000; confirmar initialize,
  tools/list e stdout JSON-RPC puro.
- [ ] Na fixture `pipeline_probe.py --mode success`, além do fluxo existente,
  verificar que a quick search retorna o header exatamente uma vez e que o fluxo
  deep → getters → relatório continua íntegro.
- [x] Não executar os probes `timeout` e `cancel` para esta entrega: E1 não altera
  worker, deadline ou cleanup. Esses probes serão pertinentes somente a uma mudança
  futura nessas camadas.
- [x] Não publicar a imagem. Scan/SBOM devem ser produzidos quando exigidos pelo
  fluxo gerenciado ou por mudança de dependências/imagem, não como aceite extra
  para código já validado. O build falhou antes de produzir imagem/scan/SBOM.

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
Como não há imagem, labels OCI nem passagem explícita de `VERSION`/`GIT_SHA` pelo
CLI gerenciado também não puderam ser verificadas.

Não houve scan, SBOM, autorização nem publicação. E5 permanece bloqueada até haver
um build compatível com as dependências online do Dockerfile (ou bases/cache
completos e autorizados), seguido da produção e validação do candidato.

## 9. E6 — Rollout de teste Positronic e smoke real

Esta etapa exige solicitação explícita de rollout; a criação deste plano não a
executa nem autoriza publicação.

- [ ] Ler imediatamente antes da mutação `positronic mcp server show deep-research`
  e as imagens/autorizações necessárias. Usar as revisões atuais, não os números
  históricos deste plano.
- [ ] Confirmar que a imagem baseline está disponível para rollback.
- [ ] Autorizar o candidato local se exigido e aplicar `update-image` com CAS pelo
  manager Positronic. Reaplicar a configuração vigente preservando rede, mount RO,
  variáveis e as cinco tools permitidas; não ler ou imprimir o arquivo secreto.
- [ ] Executar `discover` e confirmar cinco tools e a imagem esperada. Handshake e
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

## 10. E7 — Fechamento documental e rollback

- [ ] Atualizar a issue com os arquivos alterados, regressões, comandos e resultados
  de DR-BATCH-02, SHA/diff, image ID e evidência do smoke quando houver. Para
  DR-BATCH-01, registrar o timeout, o sucesso posterior, a ausência de causa
  demonstrada e a decisão de não intervir; não preencher uma causa hipotética.
- [ ] Marcar DR-BATCH-02 como resolvida localmente por `e9bf7ee` e como implantada
  somente após E6. Marcar DR-BATCH-01 como encerrada sem correção neste plano, com
  risco residual e critérios de reabertura explícitos.
- [ ] Mover a issue para `docs/issues/closed/` após o escopo de entrega solicitado
  ser reconciliado, amparado pela decisão explícita do operador de encerrar
  DR-BATCH-01 sem patch. O fechamento não pode declarar a intermitência eliminada.
- [ ] Mover este plano para `docs/plans/closed/` quando E4–E6, conforme o escopo
  solicitado, e esta documentação estiverem reconciliados. Observabilidade futura
  não impede o fechamento e deve ter registro próprio se for executada.
- [ ] Se o candidato falhar, restaurar pelo manager a imagem baseline ainda
  disponível, usando a revisão atual, e registrar o resultado. Não editar
  registry/config/audit diretamente e não operar o ambiente Percival.

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
