# Stage-2 — Remediação do Percival Deep Research MCP

**Data / revisão:** 2026-10-27 / 1.0 — execução local registrada em 2026-10-28 / 2.0; revisões documentais em 2026-10-29 / 2.1 e 2.2; simplificação de governança em 2026-10-30 / 2.3; execução local e reconciliação de evidências em 2026-11-01 / 2.4; diretriz do owner para ensaio via Percival em 2026-11-01 / 2.5; pinagem inicial no Percival em 2026-11-01 / 2.6; ensaio integrado parcial em 2026-11-01 / 2.7; correção multicamada preparada em 2026-11-01 / 2.9; gateway/broker atualizados e nova pinagem Deep Research em 2026-11-01 / 2.10.
**ID / estado:** S2-DR / execução local concluída parcialmente; **parcial** (7 ações
verificadas, 2 parciais; Deep Research `feecce…` pinado e gateway/broker Compose
atualizados; perfil de runtime A-009 pendente; V-PILOT funcional ainda não repetido
após essas atualizações; 1 ação encerrada por decisão explícita de risco; publicação
continua fora de escopo).
**Checkout executor:** `/home/bill/Projects/percival-deep-research`.  
**Owner, operador e signatário:** Bill Kopp (`bill.kopp.dev@gmail.com`), único proprietário e responsável por esta aplicação e pela infraestrutura IaC da Positronic Bean Labs (PBLabs); é também a única pessoa trabalhando nesses projetos e a única autoridade para decidir e assinar. Site: `labs.positronicbean.com`. As instruções e decisões de Bill autorizam o trabalho dentro do escopo explicitado, sem reaprovação ou aceite duplicado. A rotação da chave de teste foi dispensada por `R-01`.

## 1. Objetivo, fontes e limites

Tratar integralmente os 21 registros da **seção 6** do
[relatório Deep Research](../../../positronic-bean-IaC/docs/reports/2026-10-27-percival-deep-research-iac-readiness-report.md#6-achados-issues-e-inconsistências),
incluindo a observação positiva F-019, as limitações por design e as falhas ainda
hipotéticas. Seções 7 e 9 fornecem 12 ações (5 P1, 5 P2, 2 P3), sem P0.
Baseline e HEAD na emissão: `defc9434487be4db7dbc13003db1709047297471`.
**HEAD no início da execução:** `230798e0ea28b4e9b06a7d2d379a9a6d7e5c9798`.
A nota histórica `docs/issues/2026-10-10-f3-status.md` está localmente excluída;
preservar essa alteração e acordar com o dono seu destino documental.

[Coordenador stage-2](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
— retorno S2-DR nas seções 3 e 7. Referências:
[consolidação](../../../positronic-bean-IaC/docs/reports/2026-10-26-stage-1-consolidated-readiness-report.md),
[D-01..D-06](../../../positronic-bean-IaC/docs/decisions/2026-10-27-iac-stage-1-scope-and-pilot-decisions.md).

Esta revisão registra decisões, autorizações e a pinagem da imagem candidata no
Percival reportada pelo owner; não afirma que o perfil estreito de runtime ou os
testes integrados foram executados. Publicação permanece fora de escopo. As
decisões registradas não precisam ser solicitadas ou aprovadas novamente.
Preservar 5 tools, 4 prompts, resource template, envelopes de fontes não
confiáveis e single-endpoint inference. Bill autorizou o piloto complementar de
Deep Research para fechar S2-DR, sem substituir o par original D-01 (Percival +
Notes). O rollout autorizado limita-se ao ambiente de teste e ao manager
responsável; não autoriza produção nem publicação no catálogo. Não rotacionar a
credencial conforme `R-01`.

Uma evidência técnica vale para a revisão/imagem exata que identifica. Executar e
registrar cada verificação uma vez, reutilizando sua referência neste plano e em
relatórios coordenadores; não criar novos aceites para repetir o mesmo resultado.
Verificações diferentes continuam necessárias quando cobrem riscos distintos,
como teste local versus piloto integrado no manager.

## 2. Preparação e decisões discriminantes

- [x] Ler instruções/README/CI atuais; registrar SHA/worktree, Python, lock e versão
  efetivamente embarcada de `gpt-researcher`. Decidir versão alvo antes de alterar
  patch, health ou pipeline. Não fixar automaticamente 0.15.1 por ser o baseline.
  **Registrado (2026-10-28):** SHA inicial `230798e0ea28b4e9b06a7d2d379a9a6d7e5c9798`;
  worktree com uma exclusão pré-existente (`docs/issues/2026-10-10-f3-status.md`,
  preservada e não versionada); suíte local em Python 3.12.14 com `gpt-researcher`
  0.16.0; imagem em Python 3.12.16 com `gpt-researcher` 0.16.0. **Alvo decidido
  pelo owner: Python 3.12 + `gpt-researcher==0.16.0`** (fixado no `pyproject.toml`,
  no `uv.lock` e no `Dockerfile`; o patch continua aplicado porque 0.16.0 é a
  versão afetada).
- [x] Usar inferência/retrievers simulados e rede interna controlada. “Sem egress”
  nesta prova significa sem saída à Internet, **com acesso à fixture de provedor**;
  não promete pesquisa real sem acesso aos provedores configurados.
  **Registrado:** o ensaio de deadline usa um fixture HTTP interno que nunca
  responde (`scripts/timeout_probe.py`); o caminho feliz do worker usa um upstream
  simulado por stub (`tests/test_research_worker.py`). Nenhum provedor real foi
  chamado.
- [x] Medir cancelamento antes de escolher correção de timeout; a hipótese de
  `CancelledError` absorvido não prova qual mecanismo o corrigirá.
  **Registrado:** a hipótese do upstream absorver o cancelamento não foi
  confirmada isoladamente; por isso a correção escolhida (owner: “isolar o
  pipeline em subprocesso”) não depende de resolver a hipótese — o pai mata o
  processo, o que encerra o trabalho de qualquer forma.
- [x] Decisões do operador aplicáveis a este plano:
  `R-01` encerra a solicitação de rotação da chave de teste; a credencial continua
  como risco residual explicitamente aceito e não deve ser rotacionada nesta
  campanha. `R-10` (2026-10-29) supersede `R-02` quanto ao default do broker Percival,
  que permanece amplo conforme B14/B22/B23–B25; perfis de Research devem declarar
  explicitamente seus mounts necessários e não depender do default. Aumentar perfil
  restrito para Full requer confirmação e auditoria. `R-03` remove
  o dimensionamento de esforço, custo e prazo. `R-05` centraliza F3 em
  `pblabs-mcp-index`, por imagem publicada, com links nos checkouts. `R-06` adota
  o schema externo versionado de `server.json`, a extensão operacional
  `pblabs.app.yaml` e `pblabs-mcp-index` como destino, sem dependência do Docker
  MCP Catalog. `R-07` exige VEX por CVE associado ao image ID e assinado pelo
  owner, tratando CVEs da imagem base por herança. `R-08` fixa pin aprovado e
  operação em janela única datada. `R-09` define a matriz por transporte,
  método e deadline, permitindo declarar limitações sem obrigar implementação
  geral de cancelamento.
- [x] `R-11` (2026-10-29): Trivy é o scanner padrão e está instalado; o agente
  pode executar scans locais autonomamente quando necessários, cobrindo todas
  as severidades, atualizando a DB quando necessário e registrando versão, DB,
  SHA e image ID. Preferir TAR do
  candidato sem Docker socket. A decisão não autoriza VEX, release ou promoção:
  VEX continua ligado ao image ID e assinado pelo owner conforme `R-07`.
- [x] `R-01` encerra A-005 como rotação; A-004 (reconciliação de runtime) e a
  aplicação do perfil de A-009 continuam dependências operacionais distintas.
- [x] D-05/R-02 define a prova vertical no daemon host existente, com fixture
  dedicada; não criar DinD privilegiado para este piloto.
- [x] **Decisões do owner para S2-DR (2026-10-29):**
  - `DR-DEC-01` — Atualizar `authlib`, `dnspython` e `litellm` para versões
    estáveis atuais e compatíveis, corrigindo os achados registrados antes do
    rollout/piloto e da publicação. Esta decisão substitui a decisão temporária
    de 2026-10-28 de manter as versões antigas
    nesta rodada. Rebuild, regressões, scan do candidato final e VEX assinado
    devem corresponder ao mesmo image ID.
  - `DR-DEC-02` — Bill ratifica o conteúdo dos contratos S2-C01/S2-C03
    (`0.2-approved`, IaC `bf9c25201453f1f9c89b9a49030def4b2a053599`). O índice
    canônico é `/home/bill/Projects/pblabs-mcp-index`: `catalog.yaml` controla
    a composição; cada app usa `servers/deep-research/server.json` e
    `servers/deep-research/pblabs.app.yaml`; `public/catalog.json` é gerado.
    O Registry schema está pinado em
    `schemas/server.schema.2025-12-11.json` (SHA-256
    `3fba09590c99f61735d234822279f4223fab9e300c0a81e81c91ab62a4114de0`);
    a extensão `pblabs.app.yaml` usa o schema PBLabs 0.1.
    O `.app.yaml` existente continua draft, `server.json` ainda precisa ser
    criado/validado e o catálogo está vazio. Revisar o draft com o perfil de
    runtime; esta aprovação de contrato não aprova publicação.
  - `DR-DEC-03` — Aprovar e manter um harness MCP comum versionado, conforme a
    recomendação S2-C04 do relatório IaC: repositório dedicado (nome de trabalho
    `pblabs-mcp-harness`, fora da IaC e do índice), Python/SDK oficial `mcp`,
    tags/commits imutáveis, schema de evidência versionado e adaptadores/testes
    específicos mantidos em cada produto. Implementação e prova de reuso ainda
    pendentes.
  - `DR-DEC-04` — Autorizar rollout direto no ambiente de teste pelo manager
    responsável, sem aprovação adicional ou janela formal. Limitar a operação
    à instância de teste; identificar imagem/revisão e configuração atuais,
    preservar dados/recursos alheios e manter rollback simples. Esta decisão
    simplifica `R-08` somente para este rollout de teste; produção não é abrangida.
  - `DR-DEC-05` — Autorizar um piloto complementar Percival agent →
    `percival-deep-research` MCP para fechar S2-DR, sem alterar o par global
    D-01. Usar o daemon/manager existente e a fixture dedicada de D-05/R-02,
    após atualizar/revalidar o candidato; o piloto está autorizado, mas ainda
    não executado.
  - `DR-DEC-06` — Aplicar `R-09`: documentar a limitação de cancelamento MCP
    por transporte/método/deadline; não implementar cancelamento geral, salvo
    se o piloto ou um consumidor demonstrar necessidade.
    Limitação atual registrada: no stdio, `tools/call` e
    `research://{topic}` têm deadline interno rígido de 2 s; propagação de
    `notifications/cancelled` do cliente não foi testada nem é garantida. Não
    alegar cancelamento imediato do protocolo; o worker é encerrado pelo limite
    interno. Só ampliar suporte se o piloto exigir.
  - `DR-DEC-07` (2026-10-30) — Bill é o único owner, operador e signatário da
    aplicação e da IaC. Sua instrução direta autoriza o escopo que ela nomeia;
    não há segunda aprovação, aceite repetido, revisão obrigatória por outra
    pessoa ou handoff entre owners. Registrar evidência uma vez por revisão ou
    image ID e referenciá-la onde necessário. Manter os limites de escopo já
    aprovados: autorização de teste não autoriza produção nem publicação.

## 3. Matriz integral de ações e critérios de aceite

A tabela preserva as 12 ações de origem e seus critérios de aceite; os estados
evidenciados após a execução local estão registrados na seção 6. Prioridades
originais preservadas; F-017 P1 está agrupado em A-001.
Os critérios abaixo são verificações técnicas, não aprovações adicionais. Para
A-004/A-009, a autorização de rollout de teste já foi dada em `DR-DEC-04`; não
solicitar novo aceite para a mesma operação.

| Ação | Achados / P | Trabalho e áreas previstas | Dependências / dono externo | Aceite verificável |
|---|---|---|---|---|
| A-001 | F-001, F-017 / P1 | Falhar com exit não zero sem credencial e alinhar Python/dependências entre Dockerfile, CI e suíte | Decisão da versão alvo pelo produto | Startup sem credencial falha; suíte roda contra combinação realmente embarcada e CI a verifica; se alvo mudar, registrar em vez de exigir 0.15.1 histórica |
| A-002 | F-002, F-015 / P1 | Pré-popular cache tiktoken identificado na imagem; declarar/fixar mapa LiteLLM e destinos de rede | Política de rede com owner; S2-C01 | `research_deep` completo contra fixture interna sem Internet e sem cache externo; import não precisa de download oculto ou exceção explicitamente decidida |
| A-003 | F-003 / P1 | Investigar timeout/cancelamento em `tools/deep_research.py` e camada upstream; aplicar limite efetivo e limpar tarefas | Contrato de duração e hipótese discriminada | Limite 2 s contra pipeline 6 s devolve timeout em menos de 3 s, tarefas liberadas e sem “Research complete”; teste também o fluxo normal. Registrar suporte/limitação MCP por transporte/método/deadline conforme `R-09`; não é obrigatório implementar cancelamento geral |
| A-004 | F-004 / P1 | Preparar candidato rastreável e reconciliar imagem/estado pelo manager de teste | Candidato final revalidado; `DR-DEC-04` | Aplicar uma vez no ambiente de teste autorizado; registrar imagem/revisão, configuração anterior, estado observado e rollback. Sem janela ou aprovação adicional; sem alteração de produção |
| A-005 | F-005 / P1 | Preservar a entrega por arquivo e registrar o risco residual da credencial de teste, sem executar rotação nesta campanha | Decisão explícita `R-01`; S2-NB-X01 somente para o contrato de entrega | **Rotação encerrada por decisão de risco:** não revogar a chave nem emitir substituta agora; manter o risco aceito explícito e não expor seu valor. A configuração por arquivo continua documentada, mas não é requisito para fechar a rotação |
| A-006 | F-006, F-016, F-018 / P2 | Alinhar `/health` ao registry real/suporte declarado, validar `INFERENCE_LLM` e remover código inerte ou declarar dependências | Versão decidida A-001 | Retriever suportado saudável; LLM malformado reflete configuração inválida/degraded; sem imports de pacote só transitivo; docs sincronizados |
| A-007 | F-007 / P2 | Ativar cobertura no comando canônico/CI e corrigir documentação | Política de teste existente >=70% | `uv run pytest -q` mede e aplica limiar 70%; prova de que queda abaixo falha; suíte normal verde |
| A-008 | F-008, F-009 / P2 | Condicionar/eliminar patch gpt-researcher por versão; registrar divergência em manifesto/SBOM; normalizar metadados/timestamps de build | A-001 | Dois builds limpos sem cache, entradas/builder identificados, image IDs iguais conforme aceite de origem; conteúdo/SBOM/patch coerentes; divergência medida permanece aberta se não resolvida |
| A-009 | F-010 / P2 | Declarar perfil RO/cap-drop/NNP/init e mounts mínimos explícitos; aplicar diretamente no manager de teste | Perfil declarado; `R-10` e autorização `DR-DEC-04` | Aplicar e inspecionar junto com A-004, sem operação ou aceite duplicado; declarar mounts Research necessários sem herdar o default amplo do broker; não montar cache host RW sem justificativa; registrar configuração anterior e rollback; sem alterar produção |
| A-010 | F-011 / P2 | Documentar volatilidade de research_id/cache de tópicos e efeito de recriação | Limitação stateless por design | README/contrato explicam expiração; sessão válida antes e erro explícito após recriação; não adicionar persistência por suposição |
| A-011 | F-012, F-013 / P3 | Derivar versão do produto em serverInfo e corrigir contagem de caracteres das fontes | Contrato preservado e versão do candidato | Handshake igual à versão do pacote (3.0.1 apenas se continuar vigente); fonte fixture com conteúdo conhecido não reporta zero incorretamente |
| A-012 | F-014, F-019, F-020, F-021 / P3 | Remover apt/setuid desnecessários; adotar harness comum (`DR-DEC-03`); atualizar dependências vulneráveis; scan Trivy (`R-11`); metadados no índice conforme `R-06`/`DR-DEC-02`; VEX conforme `R-07` | Dependências atualizadas; contratos de metadados ratificados; harness comum implementado | Uma qualificação do candidato final; `server.json` validado contra schema e `.app.yaml` coerente no índice; um scan Trivy registrando versão/data da DB, SHA e image ID; VEX por CVE ligado a esse image ID e assinado por Bill; CVEs da imagem base tratados por herança. O verificador CI atual só compara IDs de vulnerabilidade e não substitui a vinculação/assinatura do VEX |

Não copiar credencial de configuração para relatório/log. `R-01` encerra a
rotação como decisão explícita de risco; reescrever config ou reduzir mode não
revogaria a chave e não é solicitado. O risco residual permanece registrado.
F-019 é evidência positiva de reuso: preservar e vincular sua versão, não “corrigir
um bug”. Scan sem findings não justifica inventar CVEs/declarações VEX.

## 4. Sequência de execução

1. **Código e candidato:** atualizar dependências e executar uma rodada de
   regressão no SHA final; revalidar timeout, retrievers, patch e formato público.
   Produzir o candidato rastreável e executar nele os checks locais pertinentes.
2. **Segurança e metadados:** escanear o candidato final uma vez; associar o VEX
   assinado por Bill ao mesmo image ID. Preparar/validar os metadados no índice
   conforme os contratos já ratificados. Esses passos não exigem aprovações
   adicionais nem repetição de resultados em cada documento.
3. **Teste integrado:** A-004/A-009 já estão autorizadas para o ambiente de teste.
   Aplicar o perfil e verificar a instância uma vez, guardando evidência e
   rollback. Executar o V-PILOT autorizado após revalidar o candidato.
   A-005 permanece encerrada por `R-01`.

Produção e publicação não estão autorizadas por este plano. O ciclo de vida
completo continua relacionado à etapa 5 IaC, mas não é pré-aprovação para o
rollout de teste já autorizado.

Riscos: timeout externo pode deixar trabalho órfão; alteração de dependência muda
retrievers/patch; hardening pode exigir paths temporários explícitos. Só escalar
trade-offs que alterem materialmente escopo ou segurança; nos demais casos, seguir
os critérios registrados. `R-03` remove a exigência de estimar esforço, custo ou prazo.

## 5. Qualificação futura no projeto

- [ ] No SHA final, executar uma vez `uv run pytest -q` e os checks de lint/format
  do CI relevantes. Não repetir medições históricas como se fossem resultados
  atuais.
- [ ] Qualificar o candidato final com os probes Docker aplicáveis: build,
  conformance/handshake, signals/EOF, timeout e pipeline com fixtures. Registrar
  os resultados juntos para V-BUILD/V-RUN/V-CONFIG/V-MCP/V-FUNC; confirmar a
  semântica stateless uma vez para V-DATA. A limitação MCP está registrada na
  seção 2; só implementar cancelamento se o piloto demonstrar necessidade.
- [x] S2-C04 comum entregue: o harness versionado `pblabs-mcp-stdio/v1` foi
  executado em Notes e Weather na mesma revisão, cobrindo o subconjunto stdio
  comum. Isso não qualifica o pipeline funcional Deep Research nem substitui
  seus testes específicos; não há prova de que este MCP tenha sido consumidor
  do harness.
- [ ] Executar o teste integrado `V-PILOT` já autorizado em `DR-DEC-05`
  (Percival agent → Deep Research MCP), no ambiente de teste e pela receita
  D-05/R-02, usando o candidato atualizado/revalidado. Nenhum piloto ou provedor
  real foi executado nesta revisão; timeout interno não prova cancelamento
  end-to-end do protocolo.
- [ ] A-004/A-009: aplicar e verificar o perfil no manager de teste uma vez,
  com estado anterior e rollback registrados; não exigir nova aprovação ou
  repetir a inspeção para cada ação.
  A-005 está encerrada por `R-01`. Publicação, CI remoto e smoke real não são
  inferidos da fixture local.

Aceite local distinto de qualificação externa. Publicação e reconciliação de
runtime pendentes mantêm o resultado parcial; a rotação foi dispensada por
decisão explícita de risco (`R-01`).

## 6. Penúltima etapa — documentar execução neste plano

- [x] Atualizar por ação: mudança, owner/data, SHA inicial/final, ambiente/versões,
  comandos/resultados, evidências sanitizadas locais e decisões pendentes.
- [x] Registrar revalidação `V-*` e limites; acrescentar retorno à seção 9 do
  relatório IaC quando autorizado, preservando sua coleta original.

**Execução: 2026-10-28, owner `bill`, executor Positronic (execução local).**
**SHA inicial:** `230798e0ea28b4e9b06a7d2d379a9a6d7e5c9798` ·
**SHA final (código):** `5b50966` (`fix(research): alinhar runtime, rede e deadline
do pipeline de pesquisa`) · este documento é versionado no commit seguinte.
Ambiente: Linux x86_64 (Omarchy), Docker 29.9.2, `uv` 0.12.18 em
`$HOME/.local/bin` (fora do PATH padrão), Python 3.12.14 no `.venv` local e
3.12.16 na imagem. Suíte: `uv run --no-sync pytest -q` → **434 passed, 3 skipped**
(cobertura **89,35 %**, `fail_under=70` aplicado pelo próprio comando canônico);
`ruff 0.16.10 check` e `format --check` limpos (59 arquivos).

| Ação | Estado | Mudança e evidência local verificada | Dependências / pendências |
|---|---|---|---|
| A-001 (F-001, F-017) | **verificada** | Alvo Python 3.12 + `gpt-researcher==0.16.0` fixado em `pyproject.toml`, `uv.lock` e `Dockerfile` (bases `python:3.12-slim@sha256:6b25cbe6…` e `uv:0.9.30-python3.12-trixie-slim@sha256:41eb2281…`; CI em 3.12). `server.py` passou a terminar com `SystemExit(1)` sem credencial: `docker run --rm --network none <img>` → **exit 1** e mensagem `INFERENCE_API_KEY … not found`. Suíte e CI rodam contra a mesma combinação embarcada (`gpt-researcher` 0.16.0 no host e na imagem, conferido por `importlib.metadata`). | Patch continua obrigatório em 0.16.0; o script recusa versões não suportadas. |
| A-002 (F-002, F-015) | **parcial** | Imagem pré-popula o encoding `o200k_base` (`TIKTOKEN_CACHE_DIR=/app/.cache/tiktoken`, arquivo presente) e usa o mapa local do LiteLLM (`LITELLM_LOCAL_MODEL_COST_MAP=true`): com `--network none` o import resolve `o200k_base` e 2 953 modelos sem qualquer download. Documentados em `README.md` e em `docs/runtime-profile.md` (destinos de rede reais: endpoint de inferência + retriever). No ensaio reportado em 2026-11-01, `research_quick_search` retornou resultados, mas `research_deep` expirou aos 30 s do cliente sem corpo nem `research_id`; pipeline de síntese continua não demonstrado. | Alinhar o timeout do cliente Percival ao limite efetivo do servidor e repetir uma chamada controlada, sem retry automático. O código do produto usa `PERCIVAL_RESEARCH_TIMEOUT_S=90` por padrão; o valor efetivo no container não foi verificado. A busca rápida teve qualidade inconsistente (duas chamadas com resultados, uma vazia; primeira dominada por fontes comerciais). |
| A-003 (F-003) | **verificada; limitação MCP documentada** | O pipeline passou a rodar em processo isolado (`percival_research/research_worker.py`, cliente em `research_worker_client.py`); o pai aplica `PERCIVAL_RESEARCH_TIMEOUT_S` como limite rígido e mata o worker. Ensaio com upstream lento (`scripts/timeout_probe.py`, limite 2 s): resposta **“Error: Research exceeded the 2s internal limit” em 2,03 s**, sem “Research complete”, container encerrando com exit 0. O mesmo limite vale para `research://{topic}`. Para stdio, `notifications/cancelled` não é testado nem prometido; o limite interno encerra o worker. | Implementar propagação de cancelamento somente se o piloto ou um consumidor exigir; E-042 permanece como limitação, não como bloqueio atual. |
| A-004 (F-004) | **pinagem do candidato concluída; teste integrado pendente** | O owner reportou pinagem pela UI Percival em 2026-11-01. Capturas mostram `update-image` iniciado às 13:25:15 e commits às 13:25:28/13:25:37 (hora exibida na UI), com imagem corrente `sha256:4fd1d8d01b242cafe57603ac2c04bc12e34843b54f7b4bf72a83802d7eaaa61d` (`3.0.1`, label OCI revision `09c3903944ae52584c350647f4900b78fc0ea262`). A tela posterior mostra Docker `running`, gateway intent `running`, MCP `connected` e 5 tools observadas. | As capturas mostram a configuração preservada durante a troca: bridge network, Full host access e 3 variáveis de ambiente. Portanto A-009 não foi aplicado; remover/reconciliar os seis mounts host RW amplos antes de aceitar o perfil de teste. A imagem anterior era `sha256:265891c14514c809e9c05587549631426ef080219c03fde21e5d703623d3793d`; a UI avisa que rollback só tenta usá-la se ainda estiver disponível localmente e que camadas antigas não são arquivadas. Teste funcional/piloto ainda pendente. |
| A-005 (F-005) | **encerrada por decisão explícita de risco (`R-01`)** | Formato de entrega por arquivo permanece especificado (`docs/runtime-profile.md`: `/app/.env` RO, host 0600, nunca valor literal no ambiente) e a leitura do arquivo foi verificada localmente. | A rotação não será executada nesta campanha: o operador aceitou manter a chave descartável de teste porque outros serviços dependem dela. O risco residual continua registrado; esta decisão não equivale a revogação ou correção técnica. |
| A-006 (F-006, F-016, F-018) | **verificada** | `/health` valida o retriever contra o registry real do `gpt-researcher` embarcado e detecta as variáveis de ambiente obrigatórias lendo o módulo upstream: `RETRIEVER=searx` com `SEARX_URL` → **200 healthy**; sem `SEARX_URL` → **503 degraded** (antes: sempre 503 para `searx`). `INFERENCE_LLM` malformado → `degraded`. Código inerte: `percival_research/retrievers/duckduckgo.py` passou a usar o pacote declarado `ddgs` (o `duckduckgo_search` não declarado saiu) e `httpx` passou a ser dependência declarada; o registry local ficou documentado como camada de extensão, fora do `/health`. | `/health` não valida reachability do provedor nem validade das credenciais — limitação declarada no README. |
| A-007 (F-007) | **verificada** | `addopts` do pytest passa a medir cobertura (`--cov=server --cov=utils --cov=config --cov=llm_bridge --cov=percival_research --cov-report=term-missing`) com `fail_under=70`: `uv run pytest -q` reporta **89,35 %** e falha quando o piso não é atingido (prova local: `--cov-fail-under=99` → exit 1; passo equivalente no CI). Documentação sincronizada (README, AGENTS, PROJECT). | — |
| A-008 (F-008, F-009) | **verificada** | Patch condicionado à versão: `scripts/patch_gpt_researcher.py` só aplica em 0.16.0, é no-op quando a versão não precisa e **recusa** versões desconhecidas. Divergência declarada em proveniência: labels `io.percival.gpt-researcher.version` / `.patch` e campo `gpt_researcher` no manifesto de build (SBOM CycloneDX no CI). Reprodutibilidade: `SOURCE_DATE_EPOCH` + `cp -a` (em vez de `COPY --from`, que carimba diretórios com a hora do build) → **dois builds `--no-cache` do mesmo SHA produzem o mesmo image ID** (`sha256:a53f74436c65…`), verificado por `scripts/check_reproducible_build.sh` (passo no CI). | A comparação usa `--provenance=false`: com a atestação padrão, o índice OCI carrega metadados por build (a identidade reproduzível é o manifest da plataforma). Divergência de conteúdo entre builds: 0. |
| A-009 (F-010) | **pendente** (perfil local pronto) | Perfil declarado em `docs/runtime-profile.md`: user 1000, rootfs RO, `cap_drop ALL`, `no-new-privileges`, init do launcher, tmpfs, `pids_limit`, mounts mínimos (`/app/.env` RO 0600, logs, reports) e política de rede (só endpoint de inferência + retriever). | **Não executada:** a tela pós-pin ainda reporta bridge network e Full host access; aplicar/reconciliar o perfil estreito pela UI, remover os mounts host RW amplos observados (`/`, `/boot`, `/home`, `/tmp`, `/var/log`, cache pacman) e registrar configuração anterior, imagem e rollback. Não foi apresentada evidência de perfil hardened. |
| A-010 (F-011) | **verificada** | README documenta a volatilidade: `research_id` e cache de tópicos vivem em memória, expiram pelo TTL e são perdidos ao recriar o container; o erro explícito “Research ID not found or expired. Please run a new research session.” foi preservado e testado. Nenhuma persistência foi adicionada. | — |
| A-011 (F-012, F-013) | **verificada** | `serverInfo.version` deriva da versão do produto (`FastMCP(version=__version__)`); o harness de conformance compara o handshake com a versão de `pyproject.toml` e falha se divergirem. Contagem de caracteres das fontes corrigida: o upstream guarda o corpo em `raw_content`, e o formatador agora lê `raw_content` (com fallback para `content`) — a fonte de fixture com conteúdo conhecido reporta o tamanho real, não zero. | — |
| A-012 (F-014, F-019, F-020, F-021) | **parcial** | Hardening e S2-C04 comum estão verificados. As dependências vulneráveis foram atualizadas; ver seção 6.2. Trivy 0.76.1 com DB atualizada em 2026-11-01 encontrou **0 vulnerabilidades** no image ID `sha256:4fd1d8d01b242cafe57603ac2c04bc12e34843b54f7b4bf72a83802d7eaaa61d`; não há findings que justifiquem VEX para este candidato. No índice PBLabs, `pblabs.app.yaml` está `manifest-approved` (aprovação de metadados, não de release), `server.json` continua ausente e o catálogo permanece vazio; `docker/server.json` do produto contém placeholders de publicação e não é manifest do índice. | **Próximo ciclo, conforme decisão do owner (2026-11-01):** criar/validar `server.json` no índice quando houver identidade/namespace e digest efetivos. Até lá, manter o catálogo vazio; esta tarefa não bloqueia o ciclo atual de testes em Percival. |

**Revalidação `V-*` (2026-10-28, escopo local):**

| Cenário | Estado | Observação |
|---|---|---|
| `V-BUILD` | aprovado | Build local `linux/amd64`, 8 camadas, `User=percival`, entrypoint e labels coerentes, **reprodutível** (dois builds limpos → mesmo image ID). |
| `V-RUN` | aprovado | Falha fechada sem credencial → exit 1; `SIGTERM`/EOF e o limite rígido de pesquisa verificados; sem container órfão no probe. |
| `V-CONFIG` | aprovado (parcial) | Segredo por arquivo, recusas de entrada e `/health` coerente com o registry real; a rotação foi explicitamente dispensada por `R-01`, com risco residual aceito. |
| `V-DATA` | não aplicável | Semântica stateless preservada; volatilidade documentada (A-010). |
| `V-MCP` | aprovado | Handshake real, 5 tools, 1 resource template, `serverInfo.version` = versão do produto, stdout JSON-RPC puro. |
| `V-FUNC` | **parcial; pesquisa profunda não passou** | No ensaio do owner, `research_quick_search` retornou fontes em 2 chamadas (5 resultados e depois 4/5 oficiais) e uma terceira chamada foi vazia. `research_deep` não retornou em 30 s; sem resposta, ID ou fontes não é possível validar síntese, getters ou relatório. O limite padrão do cliente Nanobot é 30 s (`nanobot/config/schema.py`); o código Deep Research usa 90 s internos por padrão (`config.py`), mas o override runtime não foi lido. |
| `V-PILOT` | parcial; pinagem concluída, fluxo principal bloqueado | Diagnóstico reportado pelo owner: broker `ready`, servidor `running/connected`, 5 tools e 4 prompts; initialize/list e prompt de health responderam. A pesquisa profunda expirou no cliente; getters foram chamados apenas com ID sintético e retornaram erro esperado, relatório não foi chamado. `resources/list` vazio/read 409; `resources/templates/list` não é suportado pelo broker atual. O pipeline funcional e o resource template permanecem não verificados. |
| `V-REUSE` | **entrega comum demonstrada; escopo estreito** | `pblabs-mcp-stdio/v1` passou em Notes e Weather; prova identidade/versão, initialize/tools/list, stdout de protocolo, UID opcional e encerramento. Não demonstra funcionalidade Deep Research, HTTP, CI universal ou V-PILOT. |

**Limites desta execução:** nenhuma chamada a provedor real e nenhum piloto
executado; a autorização de `DR-DEC-05` ainda não foi exercida. Nenhuma mutação
de runtime foi feita nesta revisão; a imagem candidata não foi publicada
(sem `RepoDigest`); o CI remoto não foi observado (a execução é local) e a
exclusão local pré-existente de `docs/issues/2026-10-10-f3-status.md` foi
preservada sem ser versionada. Conforme `R-05`, o destino canônico de F3 é
`pblabs-mcp-index`; esta exclusão local permanece preservada e não será
substituída por uma cópia concorrente.

**Aditivo após o commit (2026-10-28):** o candidato final foi reconstruído a
partir do SHA versionado `3a9b3b3c810e0e34ac1cb89fe51b9b4beb7a685e`
(`SOURCE_DATE_EPOCH` do próprio commit, sem cache):
`percival-deep-research:stage2-candidate` → image ID
`sha256:e91f6a3dd8b8b39053f60b2bc84f63454ee383644cef454459c56dc5eaf29b36`,
com label `org.opencontainers.image.revision` = esse SHA. Dois builds limpos
desse commit produziram **o mesmo image ID**. Reexecução sobre esse candidato:
conformance stdio verde (5 tools), falha fechada sem credencial → **exit 1**,
deadline de 2 s → erro em **2,03 s** sem “Research complete”. A imagem é local
(sem `push`/`RepoDigest`) e não substitui a publicação da Etapa 2.

### 6.1. Harmonização com IaC — 2026-10-31

- A convenção de ownership `R-12` do coordenador IaC consolida Bill como owner
  e decisor final, sem handoffs ou aprovações duplicadas. Isso preserva os testes
  técnicos e não amplia a autorização de rollout, publicação ou uso de provider
  real.
- O default amplo de mounts em `R-10` e a arquitetura de executor C02 pertencem
  ao broker Percival. O perfil Deep Research continua declarando seus próprios
  mounts estreitos e requisitos de rede; não herda configuração ou topologia do
  Percival. O smoke DinD Percival+Notes não é o `V-PILOT` Deep Research, que
  continua autorizado no plano, mas não executado.
- S2-C04 está entregue no escopo comum: `pblabs-mcp-stdio/v1` foi demonstrado
  em Notes e Weather. O resultado cobre somente probes stdio comuns e não fecha
  `V-FUNC`, HTTP ou integração do Deep Research.
- A ação A-011 do plano IaC, sobre provenance do bundle, é do bootstrap
  Percival, testada localmente com fixtures/doubles e sem release pública
  verificada. Não a tratar como requisito já implementado para Deep Research.

### 6.2. Atualização local de dependências e candidato — 2026-11-01

- Worktree baseado em HEAD `09c3903944ae52584c350647f4900b78fc0ea262`; `uv.lock`
  foi atualizado (SHA-256 `8b938d140b869ecd07e4bfb27661e91bde213fe306a013c952eb1628258fd00d`).
  Versões resultantes: `authlib 1.9.1`, `dnspython 2.9.1`, `litellm 1.106.6`,
  `joserfc 1.7.7`, `langgraph 1.2.19`, `langgraph-cli 0.4.40` e `pypdf 6.21.4`.
  O patch suportado de `gpt-researcher 0.16.0` foi reaplicado após cada `uv sync`.
- Verificações: `uv run pytest -q` → **434 passed, 3 skipped**, cobertura
  **89,35%**; Ruff check e format check passaram. Dois builds `--no-cache` da
  mesma árvore produziram o mesmo ID
  `sha256:4fd1d8d01b242cafe57603ac2c04bc12e34843b54f7b4bf72a83802d7eaaa61d`
  (`linux/amd64`; label de revisão `09c3903944ae52584c350647f4900b78fc0ea262`).
  Conformance stdio passou com 5 tools e UID 1000; timeout fixture passou em
  **2,165 s** para deadline de 2 s, sem alegar sucesso.
- Scan final: Trivy **0.76.1**, vulnerability DB `UpdatedAt=2026-11-01T13:02:34Z`
  (DownloadedAt `2026-11-01T14:54:21Z`), **0 findings** em
  `sha256:4fd1d8d01b242cafe57603ac2c04bc12e34843b54f7b4bf72a83802d7eaaa61d`.
  O primeiro scan, com DB anterior, revelou achados transitivos; eles foram
  atualizados antes do rebuild e o scan final foi repetido com DB renovada.
- **Limites:** a imagem foi construída de worktree com `uv.lock` modificado
  (não de commit limpo); o label SHA identifica o HEAD-base e o manifest local
  registra o hash do lock, mas não substitui uma revisão commitada. Nenhum
  rollout, V-PILOT ou pipeline completo contra fixture de provedor foi executado.
  O inventário Percival mostra o pin ativo antigo e seis mounts host RW amplos;
  uma sessão autenticada da interface do manager não está disponível aqui para
  reconciliar esses mounts e aplicar o perfil autorizado. No índice local,
  `pblabs.app.yaml` já está aprovado como metadado, mas `server.json` de release
  e a entrada do catálogo dependem de digest/identidade efetivos; não inventá-los.

### 6.3. Pinagem do candidato e estado do ensaio via Percival — 2026-11-01

- Bill definiu que os testes de A-002/V-FUNC, A-004/A-009 e V-PILOT serão
  realizados pelo agente Percival, com pinagem manual pela UI. Capturas fornecidas
  pelo owner registram `update-image` iniciado às 13:25:15 e commits às 13:25:28
  e 13:25:37 de 2026-11-01 (hora da UI); a tela pós-operação mostra o image ID
  `sha256:4fd1d8d01b242cafe57603ac2c04bc12e34843b54f7b4bf72a83802d7eaaa61d`,
  Docker/gateway `running`, MCP `connected` e 5 tools observadas. O diálogo confirma
  que a configuração é preservada durante `update-image`.
- A mesma tela pós-pin ainda informa bridge network, Full host access e 3 variáveis
  de ambiente. Assim, a pinagem está concluída, mas A-009/perfil estreito não está
  aplicado. Remover/reconciliar os seis mounts host RW amplos e registrar a
  configuração anterior/rollback antes de considerar o perfil de teste concluído.
  `V-FUNC` e as chamadas funcionais do piloto continuam pendentes; a UI conectada
  e a lista de tools não provam o pipeline real contra fixture de provedor.
- A-012 — criar/validar `server.json` no índice — foi explicitamente adiada para
  o próximo ciclo, quando houver identidade/namespace e digest efetivos. Manter
  o catálogo vazio; essa tarefa não bloqueia os testes atuais em Percival.

### 6.4. Ensaio funcional via Percival — resultado reportado em 2026-11-01

- Bill compartilhou o relatório do agente Percival. É evidência reportada pelo
  owner, não uma inspeção independente nesta sessão. O diagnóstico registra
  broker `ready`/servidor `registered`, `running` e `connected`, initialize,
  tools/list (5 tools) e prompts/list (4 prompts); o prompt de health retornou
  seu template. Nenhuma configuração, imagem ou servidor foi alterado no ensaio,
  segundo o relatório.
- `research_quick_search` funcionou em duas das três chamadas: a primeira retornou
  5 resultados, a segunda 5 (4 oficiais) e a terceira nenhum. A primeira busca
  priorizada por fontes oficiais trouxe sobretudo páginas comerciais, indicando
  qualidade/seleção de fontes inconsistente; isso não prova ausência de conteúdo
  oficial, pois a consulta seguinte recuperou resultados oficiais.
- `research_deep` expirou no cliente MCP aos 30 s, sem corpo de resposta e sem
  `research_id`. O código Nanobot consultado define `tool_timeout=30` s;
  `config.py` do servidor define `PERCIVAL_RESEARCH_TIMEOUT_S=90` s como padrão.
  O valor efetivo do container não foi verificado, e o timeout do cliente não
  permite concluir se o worker do servidor terminou ou foi cancelado. O probe
  local anterior com 2 s usou override explícito e não valida este limite real.
- `research_get_context`/`research_get_sources` foram chamados com ID sintético,
  retornando o erro de ID ausente; isso confirma apenas resposta de validação, não
  os caminhos com ID válido. `research_write_report` foi corretamente omitida
  sem ID válido. Nenhum resultado de pesquisa profunda, source_count ou relatório
  foi obtido.
- O resource template `research://{topic}` não foi descoberto (`resources/list`
  vazio; leitura concreta reportada como 409). A inspeção do código local do
  broker mostra allowlist para `resources/list` e `resources/read`, mas não para
  `resources/templates/list`; o manager não expõe atualmente a descoberta do
  template por esse método. A causa exata do 409 não foi distinguida no ensaio.
- **Follow-up do owner (2026-11-01):** a imagem MCP `b44a…` foi pinada, mas o
  runtime manteve o gateway e broker antigos. O ensaio repetiu o timeout de 30 s;
  o relatório confirmou também HTTPX 30 s e broker `select(...,18)` por resposta.
  `resources/read` da URI template retornou 409 e `resources/templates/list`
  400. A evidência confirma que só atualizar o servidor Deep Research não corrige
  a cadeia cliente→HTTPX→broker; os novos candidatos de §6.6 tratam os três
  limites e a rota de template.

### 6.5. Primeiro candidato de timeout — supersedido pelo ensaio reportado — 2026-11-01

- Em `nanobot/agent/tools/mcp.py`, MCPs gerenciados são convertidos em
  `MCPServerConfig` sem timeout explícito, herdando 30 s. O novo candidato de
  gateway define `DEEP_RESEARCH_TOOL_TIMEOUT_SECONDS=120` exclusivamente para
  `server_id == "deep-research"`; o default dos demais serviços é preservado.
  O README e a descrição MCP documentam que esse timeout só passa a valer após
  instalar esse gateway.
- Testes Percival: `tests/mcp_docker/test_contract.py` → **24 passed** (quatro
  avisos Pydantic preexistentes do fixture); Ruff check passou; BasedPyright do
  módulo `nanobot/agent/tools/mcp.py` → **0 errors, 0 warnings** com o ambiente
  Python 3.12 de QA explicitamente selecionado. O teste confirma 120 s para
  Deep Research e o default normal para Weather.
- Novo candidato Deep Research: `percival-deep-research:3.0.1-09c3903-f2-7337813c2124`,
  image ID `sha256:b44a6a6e4fe9a80e44111c77732be1f2154a0744085ded92ed80de58045413aa`,
  source revision base `09c3903944ae52584c350647f4900b78fc0ea262`, diff SHA-256
  `7337813c2124ca6f9e3b7c43b50cb190c11238ec1ba48b5f7e4b1ef2d6a09a57`.
  A imagem passou conformance stdio (UID 1000, 5 tools) e timeout probe de 2 s
  em fixture sintética (`2.171 s`, resposta de timeout explícita, exit 0).
- Novo candidato gateway Percival: `percival-gateway:0.1.0-26cad20-f2-fe3f97d1c563`,
  image ID `sha256:58bee2a6c9af2725887827e4d676b636c08afeb589cc0ff059f1b81d6ab7556b`,
  source revision base `26cad20fab23931f537028148f54e27cfbc4c60a`, diff SHA-256
  `fe3f97d1c563d9ffc97dd455a3ce26cc9082516cd77c2fbc209566b7459f1d17`.
  Execução isolada confirmou timeout configurado de 120 s para Deep Research e
  30 s default para demais MCPs.
- Regressão ampla Nanobot no ambiente externo de QA: **8.662 passed, 66 skipped,
  6 failed**. As falhas observadas foram por dependências ausentes do ambiente
  (`nh3`/Matrix, `bun`/`npm` para WebUI e `npx` para preset Playwright); não
  correspondem ao código de timeout. `ruff check .` passou. BasedPyright amplo
  reportou erros por extras/canais opcionais ausentes; verificação do módulo
  alterado `nanobot/agent/tools/mcp.py` com Python 3.12 selecionado passou com
  **0 errors, 0 warnings**. Portanto a regressão completa do gateway não está
  verde nesta configuração de QA.
- Trivy **0.76.1**, DB `2026-11-01T13:02:34Z`: Deep Research candidate teve
  **0 vulnerabilidades**. Gateway candidate reportou 397 entradas (4 Critical,
  80 High, 127 Medium, 172 Low, 14 Unknown). A comparação com o gateway ativo
  `sha256:2ef398971ec5effc90a11dd298530a23ffc82a8726ae379ab99531bca980a3d0`
  encontrou os mesmos 397 identificadores/pacotes/versões/severidades — nenhum
  adicionado ou removido. Os quatro Critical são associados a
  `openssh-client 1:10.6p1-1+local1`; findings não adjudicados continuam no
  risco do gateway e qualquer VEX exige decisão/assinatura do owner conforme
  `R-07`. Esta comparação não é uma classificação de explorabilidade.
- **Limite:** os dois builds são candidatos locais de worktrees dirty, sem push e
  sem atualização de runtime. A configuração atual continua apontando para as
  imagens antigas; o teste Percival integrado não foi repetido. Não houve
  promoção/publicação do gateway candidate. A issue
  [`2026-11-01-percival-tool-timeout.md`](../issues/2026-11-01-percival-tool-timeout.md)
  permanece aberta até o V-PILOT gerar um ID real e concluir getters/relatório.

### 6.6. Follow-up: limites do broker e resource templates — 2026-11-01

- O owner pinou `sha256:b44a6a6e4fe9a80e44111c77732be1f2154a0744085ded92ed80de58045413aa`
  às 14:18:56 -03:00 (`percival-mcp-deep-research`). O relatório subsequente ainda
  observa timeout aos 30 s e nenhum `research_id`. Inventário read-only confirma
  gateway ativo `percival-gateway:0.1.0-e4630dc-f3-4ddbd3bacec0` (image ID
  `sha256:2ef398971ec5effc90a11dd298530a23ffc82a8726ae379ab99531bca980a3d0`)
  e broker ativo `percival-mcp-broker:0.1.0-1fa2813` (image ID
  `sha256:1d90f1357345e85acc55ddca3bc6b7ba35d41a1c59a7664b80958f90c579295e`).
- Análise de código do stack ativo: timeout MCP wrapper 30 s, HTTPX read 30 s e
  broker `select()` 18 s por resposta. Assim, o candidato de gateway de 120 s da
  §6.5 não foi aplicado e, mesmo aplicado sozinho, não resolveria a leitura 18 s
  do broker nem o read timeout HTTPX. O relatório informa que `resources/read`
  do template retorna 409 e `resources/templates/list` retorna unsupported/400.
- Correção local: gateway Deep Research 180 s apenas para `deep-research`; HTTPX
  read/write/pool até 190 s; broker total 150 s em `tools/call`/`resources/read`
  (handshake incluso), 18 s em métodos curtos; descoberta e allowlist de
  `resources/templates/list`, resolução de URI somente contra templates simples
  previamente anunciados; gateway expõe cada template como tool read-only derivada.
  Resource template do Deep Research pode iniciar novo trabalho em cache miss:
  após timeout não repetir por essa via; primeiro obter ID real, e ler somente
  tópico já cacheado.
- Testes locais após o refinamento de leitura bounded: broker/gateway MCP,
  timeout, recursos e templates: **272 passed**, Ruff passou, BasedPyright dos
  módulos alterados **0 errors**. Regressão completa Nanobot antes desse último
  refinamento: **8.795 passed, 61 skipped, 7 failed**; seis
  falhas por dependências opcionais (`nh3`, `bun`/`npm`, `npx`), uma falha
  HTTPX read timeout em teste remoto passou isolada. O executor local não chamou
  provider; `research_quick_search` do relatório do owner está em §6.4.
- Candidatos gateway/broker aplicados a pedido do owner via Compose; imagem Deep
  Research candidata segue sem pin manual:
  - gateway: `percival-gateway:0.1.0-26cad20-f2-7de42eb44f4e`, image ID
    `sha256:ba98f612aabbfe0c2a7d9454a55ace2e2f01827a6f713eac1bc2eb285d115b79`;
  - broker: `percival-mcp-broker:0.1.0-26cad20-f2-7de42eb44f4e`, image ID
    `sha256:5f449a092238634323ea735937e6ea0cec85b81f8a38318cbf9eb7599b7ddf0f`;
  - Deep Research doc/help refresh: `percival-deep-research:3.0.1-09c3903-f2-8e267db4bd7f`,
    image ID `sha256:feecce7c7575da94a6673cbb30440ee17a74164999c35086641f7096ce305629`.
- Deep Research candidate: conformance stdio (5 tools, UID 1000) passou; timeout
  probe sintético de 2 s respondeu em 2.257 s com erro explícito, exit 0; Trivy
  0.76.1 vulnerability scan/DB `2026-11-01T13:02:34Z`: zero vulnerabilities.
  Gateway e broker
  candidates têm os mesmos findings Trivy que as imagens ativas e nenhum
  identificador/pacote/severidade adicionado ou removido. Gateway ainda tem 4
  Critical/80 High; broker 46 High, sem VEX/classificação de explorabilidade
  assinados. Não promover/publicar esses core images.
- Pós-atualização, `docker inspect` confirmou gateway ativo em
  `sha256:ba98f612aabbfe0c2a7d9454a55ace2e2f01827a6f713eac1bc2eb285d115b79`
  (revision `26cad20`, diff `7de42eb44f4e…`) e broker ativo em
  `sha256:5f449a092238634323ea735937e6ea0cec85b81f8a38318cbf9eb7599b7ddf0f`
  (mesma revision/diff). Ambos estão `healthy`; o `docker compose config`
  sanitizado resolve exatamente para as imagens candidatas.
- Smoke read-only via MCPProvider do gateway atualizado, antes da pinagem
  final e contra a imagem `b44a…`: handshake, tools/list, prompts/list e
  resources/templates/list passaram; registro do agente mostrou os cinco tools
  nativos, quatro prompts e um wrapper read-only para `research://{topic}`. Nenhuma
  `research_deep`, `resources/read` ou chamada a provider foi feita.
- O owner pinou depois a candidata Deep Research
  `sha256:feecce7c7575da94a6673cbb30440ee17a74164999c35086641f7096ce305629`;
  `docker ps` e inspect confirmam o contêiner atualizado em execução (revision
  `09c3903`). A chamada funcional ainda está pendente.
- O owner também reportou chave de inferência legível em plaintext na config,
  `allowRemoteAdmin:true` e binds RW amplos. Nenhum segredo foi acessado ou copiado;
  config, variáveis, mounts e perfil de runtime não foram alterados; A-009/R-01
  permanecem. A-009 deve ser conciliada antes do aceite final do piloto.
- **Pendência:** confirmar `PERCIVAL_RESEARCH_TIMEOUT_S` efetivo sem segredos.
  No V-PILOT, uma única chamada sem retry deve retornar `research_id`; validar corpo,
  getters e relatório com o mesmo ID. A issue permanece aberta até esse teste.

## 7. Sincronização documental com o coordenador

- [x] O retorno técnico histórico de S2-DR foi registrado no plano coordenador;
  usar links para esta evidência como fonte de verdade, sem duplicar resultados
  nem exigir aceite separado para a sincronização documental.
- [x] Preservar os retornos dos demais projetos e resumir impactos nas etapas 2/4/5.
  A sincronização do coordenador acompanha o estado, mas não é aprovação nem bloqueia
  execução já autorizada neste plano.
- [x] Sincronizar a linha S2-DR com as decisões `DR-DEC-01..07`, atualização das
  dependências, candidato/scan local da seção 6.2, mounts observados no manager,
  rota via Percival/UI para A-002/A-004/A-009/V-PILOT e postergação de A-012 para
  o próximo ciclo. É atualização de estado, não aprovação adicional.

**Retorno histórico ao coordenador (2026-10-28):** o checkout IaC estava acessível;
a linha **S2-DR** da seção 3 e uma entrada na tabela da seção 7 do
[plano coordenador](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
foram atualizadas **preservando os retornos dos demais projetos**.
Contagem naquele retorno: **7 ações integralmente verificadas** (A-001, A-003,
A-006, A-007, A-008, A-010 e A-011); a parcela local de A-012 também estava
verificada, mas a ação permaneceu parcial junto com A-002. A-004 e A-009 estavam
aguardando operação no manager; A-005 estava encerrada por decisão explícita de
risco (`R-01`). O projeto permanecia
parcial; transferências não encerravam as dependências técnicas e a publicação
continuava fora de escopo. As autorizações para o ambiente de teste foram
atualizadas em 2026-10-29; nenhuma execução de manager ou publicação é afirmada
nesta revisão.

**Atualização documental (2026-10-30 / revisão 2.3):** o retorno acima descreve a
sincronização histórica de 2026-10-28. A linha S2-DR do plano coordenador ainda
precisa refletir as decisões DR-DEC-01..07 e os estados atuais; esse checkout não
foi alterado nesta revisão. Atualizá-la é sincronização documental, não novo aceite
nem pré-condição para trabalho já autorizado.
