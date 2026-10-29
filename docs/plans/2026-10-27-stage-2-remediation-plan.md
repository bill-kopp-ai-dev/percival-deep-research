# Stage-2 — Remediação do Percival Deep Research MCP

**Data / revisão:** 2026-10-27 / 1.0 — execução local registrada em 2026-10-28 / 2.0; revisões documentais em 2026-10-29 / 2.1 e 2.2.
**ID / estado:** S2-DR / execução local concluída parcialmente; **parcial** (7 ações
verificadas, 2 parciais, 2 operações de teste autorizadas mas ainda não executadas
nos managers, e 1 ação encerrada por decisão explícita de risco; publicação continua
fora de escopo).
**Checkout executor:** `/home/bill/Projects/percival-deep-research`.  
**Owner e autoridade final:** Bill Kopp (`bill.kopp.dev@gmail.com`), proprietário único do servidor MCP e da infraestrutura IaC da Positronic Bean Labs (PBLabs); somente Bill decide e aprova mudanças. Site da empresa: `labs.positronicbean.com` (em desenvolvimento). Execução técnica pode ser delegada, sem transferir autoridade de decisão. A rotação da chave de teste foi dispensada por `R-01`.

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

Esta revisão registra decisões e autorizações do owner; não afirma que rollout,
piloto, atualização de dependências ou publicação já foram executados. Preservar
5 tools, 4 prompts, resource template, envelopes de fontes não confiáveis e
single-endpoint inference. O piloto complementar de Deep Research foi autorizado
por Bill para fechar S2-DR, sem substituir o par original D-01 (Percival + Notes).
O rollout autorizado limita-se ao ambiente de teste e ao manager responsável; não
autoriza produção nem publicação no catálogo. Não rotacionar a credencial conforme
`R-01`.

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

## 3. Matriz integral de ações e critérios de aceite

A tabela preserva as 12 ações de origem e seus critérios de aceite; os estados
evidenciados após a execução local estão registrados na seção 6. Prioridades
originais preservadas; F-017 P1 está agrupado em A-001.

| Ação | Achados / P | Trabalho e áreas previstas | Dependências / dono externo | Aceite verificável |
|---|---|---|---|---|
| A-001 | F-001, F-017 / P1 | Falhar com exit não zero sem credencial e alinhar Python/dependências entre Dockerfile, CI e suíte | Decisão da versão alvo pelo produto | Startup sem credencial falha; suíte roda contra combinação realmente embarcada e CI a verifica; se alvo mudar, registrar em vez de exigir 0.15.1 histórica |
| A-002 | F-002, F-015 / P1 | Pré-popular cache tiktoken identificado na imagem; declarar/fixar mapa LiteLLM e destinos de rede | Política de rede com owner; S2-C01 | `research_deep` completo contra fixture interna sem Internet e sem cache externo; import não precisa de download oculto ou exceção explicitamente decidida |
| A-003 | F-003 / P1 | Investigar timeout/cancelamento em `tools/deep_research.py` e camada upstream; aplicar limite efetivo e limpar tarefas | Contrato de duração e hipótese discriminada | Limite 2 s contra pipeline 6 s devolve timeout em menos de 3 s, tarefas liberadas e sem “Research complete”; teste também o fluxo normal. Registrar suporte/limitação MCP por transporte/método/deadline conforme `R-09`; não é obrigatório implementar cancelamento geral |
| A-004 | F-004 / P1 | Preparar candidato rastreável e reconciliar imagem/estado pelo manager responsável | S2-NB A-007; S2-AP-X01; `R-08`, com exceção de teste `DR-DEC-04` | Runtime de teste mostra a revisão/imagem aprovada; saved/observed/connectivity coerentes; registrar estado anterior e rollback. Rollout direto autorizado pelo owner, sem janela formal; sem alteração de produção |
| A-005 | F-005 / P1 | Preservar a entrega por arquivo e registrar o risco residual da credencial de teste, sem executar rotação nesta campanha | Decisão explícita `R-01`; S2-NB-X01 somente para o contrato de entrega | **Rotação encerrada por decisão de risco:** não revogar a chave nem emitir substituta agora; manter o risco aceito explícito e não expor seu valor. A configuração por arquivo continua documentada, mas não é requisito para fechar a rotação |
| A-006 | F-006, F-016, F-018 / P2 | Alinhar `/health` ao registry real/suporte declarado, validar `INFERENCE_LLM` e remover código inerte ou declarar dependências | Versão decidida A-001 | Retriever suportado saudável; LLM malformado reflete configuração inválida/degraded; sem imports de pacote só transitivo; docs sincronizados |
| A-007 | F-007 / P2 | Ativar cobertura no comando canônico/CI e corrigir documentação | Política de teste existente >=70% | `uv run pytest -q` mede e aplica limiar 70%; prova de que queda abaixo falha; suíte normal verde |
| A-008 | F-008, F-009 / P2 | Condicionar/eliminar patch gpt-researcher por versão; registrar divergência em manifesto/SBOM; normalizar metadados/timestamps de build | A-001 | Dois builds limpos sem cache, entradas/builder identificados, image IDs iguais conforme aceite de origem; conteúdo/SBOM/patch coerentes; divergência medida permanece aberta se não resolvida |
| A-009 | F-010 / P2 | Declarar perfil RO/cap-drop/NNP/init e mounts mínimos explícitos; aplicar diretamente no manager de teste | S2-NB-X01 e S2-AP-X01; exceções com owner; etapa 5 IaC; `R-10` e `DR-DEC-04` | Runtime de teste inspecionado com postura compatível; perfil Research declara mounts mínimos explicitamente (incluindo secrets/logs necessários), sem herdar o default amplo do broker; cache host não montado RW sem justificativa; registrar estado anterior e rollback; sem alterar produção |
| A-010 | F-011 / P2 | Documentar volatilidade de research_id/cache de tópicos e efeito de recriação | Limitação stateless por design | README/contrato explicam expiração; sessão válida antes e erro explícito após recriação; não adicionar persistência por suposição |
| A-011 | F-012, F-013 / P3 | Derivar versão do produto em serverInfo e corrigir contagem de caracteres das fontes | Contrato preservado e versão do candidato | Handshake igual à versão do pacote (3.0.1 apenas se continuar vigente); fonte fixture com conteúdo conhecido não reporta zero incorretamente |
| A-012 | F-014, F-019, F-020, F-021 / P3 | Remover apt/setuid desnecessários; adotar harness comum (`DR-DEC-03`); atualizar dependências vulneráveis; scan Trivy (`R-11`); metadados no índice conforme `R-06`/`DR-DEC-02`; gate VEX conforme `R-07` | Conteúdo S2-C01/C03 aprovado; S2-C04 aprovado; implementação do harness, CI e etapas 2/4 IaC | Inventário sem residuais incompatíveis, smoke verde; `server.json` validado contra schema e `.app.yaml` coerente no índice; scan Trivy do candidato atualizado com versão/data da DB, SHA e image ID; VEX por CVE ligado ao image ID avaliado e assinado pelo owner; CVEs da imagem base tratados por herança |

Não copiar credencial de configuração para relatório/log. `R-01` encerra a
rotação como decisão explícita de risco; reescrever config ou reduzir mode não
revogaria a chave e não é solicitado. O risco residual permanece registrado.
F-019 é evidência positiva de reuso: preservar e vincular sua versão, não “corrigir
um bug”. Scan sem findings não justifica inventar CVEs/declarações VEX.

## 4. Lotes e handoffs

1. **DR-1:** A-001 define a combinação entregue/testada; A-002/A-003 corrigem
   rede e duração. A-004/A-009 têm rollout de teste direto autorizado por Bill,
   depois de atualizar e revalidar o candidato. A-005 está encerrada por `R-01`
   e não deve gerar solicitação de rotação. Não tocar em produção ou em recursos
   alheios ao teste.
2. **DR-2:** A-006/A-007/A-008/A-010/A-011; mudança de versão upstream requer
   revalidar timeout, retrievers, patch e formato público, não apenas imports.
3. **DR-3:** A-009/A-012 e parcela externa A-004, com os contratos aprovados,
   candidato atualizado/escaneado, piloto autorizado e rollout direto no manager
   de teste (`DR-DEC-04`/`DR-DEC-05`). A-005 não exige rotação por `R-01`.
   Publicação e catálogo aguardam etapas 2/4;
   lifecycle completo é etapa 5 IaC.

Riscos: timeout externo pode deixar trabalho órfão; alteração de dependência muda
retrievers/patch; hardening pode exigir paths temporários explícitos. Registrar
alternativas com o owner; `R-03` remove a exigência de estimar esforço, custo ou prazo.

## 5. Qualificação futura no projeto

- [ ] Regressões dos achados e `uv run pytest -q` (cobertura ativada em A-007);
  lint/format **check** conforme CI. Nenhuma medição histórica vira resultado atual.
- [ ] Build canônico identificado e suíte com Python/gpt-researcher da imagem.
  Handshake/tools/call e pipeline completo usando mocks de inferência/retriever.
- [ ] Repetir `V-BUILD`/`V-RUN`/`V-CONFIG`/`V-MCP`/`V-FUNC`, signals/EOF e
  timeout real medido; `V-DATA` stateless e volatilidade explícita. A limitação
  MCP atual está registrada na seção 2; implementar cancelamento apenas se o
  piloto ou um consumidor demonstrar essa necessidade (`R-09`/`DR-DEC-06`).
- [ ] Implementar S2-C04 conforme `DR-DEC-03`: harness versionado em repositório
  dedicado, schema de evidência e mesma revisão/tag executada por pelo menos dois
  MCPs; manter adaptadores/fixtures de produto nos checkouts donos.
- [ ] Executar `V-PILOT` complementar aprovado em `DR-DEC-05` (Percival agent →
  Deep Research MCP), no ambiente de teste e pela receita D-05/R-02, usando o
  candidato atualizado/revalidado. Nenhum piloto ou provedor real foi executado
  nesta revisão; timeout interno não prova cancelamento end-to-end do protocolo.
- [ ] A-004/A-009: aplicar e verificar o perfil diretamente no manager de teste,
  com estado anterior e rollback registrados; não exigir janela/aprovação adicional.
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
| A-002 (F-002, F-015) | **parcial** | Imagem pré-popula o encoding `o200k_base` (`TIKTOKEN_CACHE_DIR=/app/.cache/tiktoken`, arquivo presente) e usa o mapa local do LiteLLM (`LITELLM_LOCAL_MODEL_COST_MAP=true`): com `--network none` o import resolve `o200k_base` e 2 953 modelos sem qualquer download. Documentados em `README.md` e em `docs/runtime-profile.md` (destinos de rede reais: endpoint de inferência + retriever). | **Não verificado:** o pipeline completo (`research_deep` → “Research complete.”) contra um fixture de provedor com resposta válida. O caminho feliz foi provado com upstream simulado por stub (`tests/test_research_worker.py`), não com o pipeline real do upstream. Ensaio com fixture real fica para a qualificação (V-FUNC/V-PILOT). |
| A-003 (F-003) | **verificada; limitação MCP documentada** | O pipeline passou a rodar em processo isolado (`percival_research/research_worker.py`, cliente em `research_worker_client.py`); o pai aplica `PERCIVAL_RESEARCH_TIMEOUT_S` como limite rígido e mata o worker. Ensaio com upstream lento (`scripts/timeout_probe.py`, limite 2 s): resposta **“Error: Research exceeded the 2s internal limit” em 2,03 s**, sem “Research complete”, container encerrando com exit 0. O mesmo limite vale para `research://{topic}`. Para stdio, `notifications/cancelled` não é testado nem prometido; o limite interno encerra o worker. | Implementar propagação de cancelamento somente se o piloto ou um consumidor exigir; E-042 permanece como limitação, não como bloqueio atual. |
| A-004 (F-004) | **rollout de teste autorizado; execução pendente** | Existe candidato rastreável anterior em `percival-deep-research:stage2-candidate`, mas ele não deve ser promovido ao manager após `DR-DEC-01`: reconstruir após o upgrade, mantendo labels de proveniência e manifesto de build (`scripts/write_docker_ci_manifest.py`). Perfil e evidência esperada em `docs/runtime-profile.md`. | Nenhuma mutação foi feita nesta revisão. Após rebuild e scan, executar diretamente pelo manager responsável no ambiente de teste; registrar a imagem/revisão e configuração atuais e manter rollback; sem janela formal adicional (`DR-DEC-04`). |
| A-005 (F-005) | **encerrada por decisão explícita de risco (`R-01`)** | Formato de entrega por arquivo permanece especificado (`docs/runtime-profile.md`: `/app/.env` RO, host 0600, nunca valor literal no ambiente) e a leitura do arquivo foi verificada localmente. | A rotação não será executada nesta campanha: o operador aceitou manter a chave descartável de teste porque outros serviços dependem dela. O risco residual continua registrado; esta decisão não equivale a revogação ou correção técnica. |
| A-006 (F-006, F-016, F-018) | **verificada** | `/health` valida o retriever contra o registry real do `gpt-researcher` embarcado e detecta as variáveis de ambiente obrigatórias lendo o módulo upstream: `RETRIEVER=searx` com `SEARX_URL` → **200 healthy**; sem `SEARX_URL` → **503 degraded** (antes: sempre 503 para `searx`). `INFERENCE_LLM` malformado → `degraded`. Código inerte: `percival_research/retrievers/duckduckgo.py` passou a usar o pacote declarado `ddgs` (o `duckduckgo_search` não declarado saiu) e `httpx` passou a ser dependência declarada; o registry local ficou documentado como camada de extensão, fora do `/health`. | `/health` não valida reachability do provedor nem validade das credenciais — limitação declarada no README. |
| A-007 (F-007) | **verificada** | `addopts` do pytest passa a medir cobertura (`--cov=server --cov=utils --cov=config --cov=llm_bridge --cov=percival_research --cov-report=term-missing`) com `fail_under=70`: `uv run pytest -q` reporta **89,35 %** e falha quando o piso não é atingido (prova local: `--cov-fail-under=99` → exit 1; passo equivalente no CI). Documentação sincronizada (README, AGENTS, PROJECT). | — |
| A-008 (F-008, F-009) | **verificada** | Patch condicionado à versão: `scripts/patch_gpt_researcher.py` só aplica em 0.16.0, é no-op quando a versão não precisa e **recusa** versões desconhecidas. Divergência declarada em proveniência: labels `io.percival.gpt-researcher.version` / `.patch` e campo `gpt_researcher` no manifesto de build (SBOM CycloneDX no CI). Reprodutibilidade: `SOURCE_DATE_EPOCH` + `cp -a` (em vez de `COPY --from`, que carimba diretórios com a hora do build) → **dois builds `--no-cache` do mesmo SHA produzem o mesmo image ID** (`sha256:a53f74436c65…`), verificado por `scripts/check_reproducible_build.sh` (passo no CI). | A comparação usa `--provenance=false`: com a atestação padrão, o índice OCI carrega metadados por build (a identidade reproduzível é o manifest da plataforma). Divergência de conteúdo entre builds: 0. |
| A-009 (F-010) | **rollout de teste autorizado; execução pendente** (perfil local pronto) | Perfil declarado em `docs/runtime-profile.md`: user 1000, rootfs RO, `cap_drop ALL`, `no-new-privileges`, init do launcher, tmpfs, `pids_limit`, mounts mínimos (`/app/.env` RO 0600, logs, reports) e política de rede (só endpoint de inferência + retriever). A imagem deixou de precisar de cache de pacotes do host (sem `apt`/`pip` na imagem), o que elimina a justificativa do mount RW `pacman/pkg`. Aplicar ao candidato reconstruído após `DR-DEC-01`. | **Não executada:** aplicar e inspecionar o perfil diretamente no manager responsável pelo ambiente de teste. R-10 mantém amplo o default do broker, então o perfil Research declara seus mounts necessários sem herdar esse default. Registrar imagem/revisão, configuração anterior e rollback; sem janela formal adicional (`DR-DEC-04`). |
| A-010 (F-011) | **verificada** | README documenta a volatilidade: `research_id` e cache de tópicos vivem em memória, expiram pelo TTL e são perdidos ao recriar o container; o erro explícito “Research ID not found or expired. Please run a new research session.” foi preservado e testado. Nenhuma persistência foi adicionada. | — |
| A-011 (F-012, F-013) | **verificada** | `serverInfo.version` deriva da versão do produto (`FastMCP(version=__version__)`); o harness de conformance compara o handshake com a versão de `pyproject.toml` e falha se divergirem. Contagem de caracteres das fontes corrigida: o upstream guarda o corpo em `raw_content`, e o formatador agora lê `raw_content` (com fallback para `content`) — a fonte de fixture com conteúdo conhecido reporta o tamanho real, não zero. | — |
| A-012 (F-014, F-019, F-020, F-021) | **parcial** | Hardening: `apt`/`apt-get`, `pip` e **todos** os binários setuid foram removidos da imagem (verificado: 0 setuid, `no-apt`, `no-pip`). O [scan Trivy](../security/2026-10-28-candidate-scan.md) 0.76.1 com **11 achados** e o [VEX](../security/vex-2026-10-28.json) referem-se à imagem antiga `sha256:afb0df3cc6b67e5bf01ac4bf018f0e6aba680b5a8c0271a8540c8c9e248aa150`; faltam data da DB e SHA de origem. O candidato final anterior `sha256:e91f6a3dd8b8b39053f60b2bc84f63454ee383644cef454459c56dc5eaf29b36` também não está coberto. S2-C03 define o destino do índice; há apenas um draft `servers/deep-research/pblabs.app.yaml`, sem `server.json` nem entrada de catálogo. | **Pendente:** atualizar authlib/dnspython/litellm para versões compatíveis corrigidas; rodar regressões e rebuild reproduzível; escanear o candidato final registrando versão/data da DB, SHA e image ID; gerar VEX para esse ID e assinar como owner (`R-07`). Criar/validar `servers/deep-research/server.json` e revisar o draft `.app.yaml` no índice. Não publicar até o owner decidir corte/release; CVEs herdados seguem a postura por herança. |

**Revalidação `V-*` (2026-10-28, escopo local):**

| Cenário | Estado | Observação |
|---|---|---|
| `V-BUILD` | aprovado | Build local `linux/amd64`, 8 camadas, `User=percival`, entrypoint e labels coerentes, **reprodutível** (dois builds limpos → mesmo image ID). |
| `V-RUN` | aprovado | Falha fechada sem credencial → exit 1; `SIGTERM`/EOF e o limite rígido de pesquisa verificados; sem container órfão no probe. |
| `V-CONFIG` | aprovado (parcial) | Segredo por arquivo, recusas de entrada e `/health` coerente com o registry real; a rotação foi explicitamente dispensada por `R-01`, com risco residual aceito. |
| `V-DATA` | não aplicável | Semântica stateless preservada; volatilidade documentada (A-010). |
| `V-MCP` | aprovado | Handshake real, 5 tools, 1 resource template, `serverInfo.version` = versão do produto, stdout JSON-RPC puro. |
| `V-FUNC` | **parcial** | Caminho feliz do worker e deadline verificados contra fixtures internas; pipeline real do upstream contra fixture de provedor **não** re-executado nesta rodada (A-002). Nenhum provedor real foi chamado. |
| `V-PILOT` | autorizado, não executado | Bill aprovou o piloto complementar Percival agent → Deep Research MCP para fechar S2-DR (`DR-DEC-05`); usar ambiente de teste e a receita dedicada D-05/R-02. |
| `V-REUSE` | princípio aprovado; implementação pendente | Bill aprovou S2-C04 (`DR-DEC-03`); falta criar/adotar a revisão comum e demonstrar a mesma tag/commit em pelo menos dois MCPs. |

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

## 7. Última etapa — atualizar o plano coordenador

- [x] Reler o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md);
  atualizar **S2-DR na seção 3** e acrescentar entrada na **seção 7**, com contagens,
  SHA/evidência, dependências liberadas e aceites locais/externos.
- [x] Preservar outros retornos e indicar impacto nas etapas 2/4/5. Se não houver
  acesso ao checkout IaC, entregar resumo e manter **aguardando sincronização**.
  Concluído exige todos os aceites e retorno; transferência não é correção verificada.
- [ ] Sincronizar a linha S2-DR com a revisão 2.2: decisões `DR-DEC-01..06`,
  contratos/harness aprovados, A-004/A-009 autorizadas para rollout direto de
  teste mas não executadas, A-012 aguardando upgrade/scan/VEX do candidato final,
  e V-PILOT autorizado mas não executado. Não inferir aceite de publicação.

**Retorno ao coordenador (2026-10-28):** o checkout IaC estava acessível;
a linha **S2-DR** da seção 3 e uma entrada na tabela da seção 7 do
[plano coordenador](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
foram atualizadas **preservando os retornos dos demais projetos**.
Contagem naquele retorno: **8 de 12 ações verificadas** (A-001, A-003, A-006,
A-007, A-008, A-010, A-011 e a parcela local de A-012), **2 parciais** (A-002
e A-012), **2 adiadas por dependências de gestores** (A-004 e A-009) e **1
encerrada por decisão explícita de risco** (A-005, `R-01`). O projeto permanecia
parcial; transferências não encerravam as dependências técnicas e a publicação
continuava fora de escopo. As autorizações para o ambiente de teste foram
atualizadas em 2026-10-29; nenhuma execução de manager ou publicação é afirmada
nesta revisão.

**Atualização documental (2026-10-29 / revisão 2.2):** o retorno acima descreve a
sincronização histórica de 2026-10-28. A linha S2-DR do plano coordenador ainda
precisa refletir as decisões do owner e os novos estados registrados nesta revisão;
esse checkout não foi alterado nesta atualização.
