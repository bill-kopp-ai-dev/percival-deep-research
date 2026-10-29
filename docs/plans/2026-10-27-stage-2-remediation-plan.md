# Stage-2 — Remediação do Percival Deep Research MCP

**Data / revisão:** 2026-10-27 / 1.0 — execução local registrada em 2026-10-28 / 2.0.  
**ID / estado:** S2-DR / executado localmente; **parcial** (8 ações com evidência
local, das quais 2 permanecem parciais; 2 dependem de gestores e 1 foi encerrada
por decisão explícita de risco; publicação e operação de terceiros fora de escopo).
**Checkout executor:** `/home/bill/Projects/percival-deep-research`.  
**Responsável:** executor Research a designar por bill; mudanças de runtime com os owners dos gestores. A rotação da chave de teste foi dispensada por `R-01`.

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

Emissão exclusivamente documental; execução futura local. Preservar 5 tools,
4 prompts, resource template, envelopes de fontes não confiáveis e single-endpoint
inference. Não é o piloto D-01. Não rotacionar credencial, operar conta paga ou
reconciliar containers reais como consequência da criação deste plano.

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
- [x] Decisões do operador de 2026-10-28 aplicáveis a este plano:
  `R-01` encerra a solicitação de rotação da chave de teste; a credencial continua
  como risco residual explicitamente aceito e não deve ser rotacionada nesta
  campanha. `R-02` fixa `mounts=[]` como default do broker; mounts são explícitos
  e acesso total (`null`) exige confirmação e auditoria separadas. `R-03` remove
  o dimensionamento de esforço, custo e prazo. `R-05` centraliza F3 em
  `pblabs-mcp-index`, por imagem publicada, com links nos checkouts. `R-06` adota
  o schema externo versionado de `server.json`, a extensão operacional
  `pblabs.app.yaml` e `pblabs-mcp-index` como destino, sem dependência do Docker
  MCP Catalog. `R-07` exige VEX por CVE associado ao image ID e assinado pelo
  owner, tratando CVEs da imagem base por herança. `R-08` fixa pin aprovado e
  operação em janela única datada. `R-09` define a matriz por transporte,
  método e deadline, permitindo declarar limitações sem obrigar implementação
  geral de cancelamento.
- [x] `R-01` encerra A-005 como rotação; A-004 (reconciliação de runtime) e a
  aplicação do perfil de A-009 continuam dependências operacionais distintas.

## 3. Backlog integral por ação

Todas as ações **não iniciadas**, inclusive as parcelas externas. Prioridades das
ações de origem preservadas; F-017 P1 está agrupado em A-001.

| Ação | Achados / P | Trabalho e áreas previstas | Dependências / dono externo | Aceite verificável |
|---|---|---|---|---|
| A-001 | F-001, F-017 / P1 | Falhar com exit não zero sem credencial e alinhar Python/dependências entre Dockerfile, CI e suíte | Decisão da versão alvo pelo produto | Startup sem credencial falha; suíte roda contra combinação realmente embarcada e CI a verifica; se alvo mudar, registrar em vez de exigir 0.15.1 histórica |
| A-002 | F-002, F-015 / P1 | Pré-popular cache tiktoken identificado na imagem; declarar/fixar mapa LiteLLM e destinos de rede | Política de rede com owner; S2-C01 | `research_deep` completo contra fixture interna sem Internet e sem cache externo; import não precisa de download oculto ou exceção explicitamente decidida |
| A-003 | F-003 / P1 | Investigar timeout/cancelamento em `tools/deep_research.py` e camada upstream; aplicar limite efetivo e limpar tarefas | Contrato de duração e hipótese discriminada | Limite 2 s contra pipeline 6 s devolve timeout em menos de 3 s, tarefas liberadas e sem “Research complete”; teste também o fluxo normal. Cancelamento MCP é declarado na matriz comum por transporte/método/deadline (`R-09`), podendo registrar limitação explícita |
| A-004 | F-004 / P1 | Preparar candidato rastreável e solicitar reconciliação de imagens/estado de cada gestor | S2-NB A-007; S2-AP-X01; `R-08`; operação aprovada pelos owners | Runtime mostra revisão do candidato com pin aprovado; operação em janela única datada e autorizada; saved/observed/connectivity coerentes e datados |
| A-005 | F-005 / P1 | Preservar a entrega por arquivo e registrar o risco residual da credencial de teste, sem executar rotação nesta campanha | Decisão explícita `R-01`; S2-NB-X01 somente para o contrato de entrega | **Rotação encerrada por decisão de risco:** não revogar a chave nem emitir substituta agora; manter o risco aceito explícito e não expor seu valor. A configuração por arquivo continua documentada, mas não é requisito para fechar a rotação |
| A-006 | F-006, F-016, F-018 / P2 | Alinhar `/health` ao registry real/suporte declarado, validar `INFERENCE_LLM` e remover código inerte ou declarar dependências | Versão decidida A-001 | Retriever suportado saudável; LLM malformado reflete configuração inválida/degraded; sem imports de pacote só transitivo; docs sincronizados |
| A-007 | F-007 / P2 | Ativar cobertura no comando canônico/CI e corrigir documentação | Política de teste existente >=70% | `uv run pytest -q` mede e aplica limiar 70%; prova de que queda abaixo falha; suíte normal verde |
| A-008 | F-008, F-009 / P2 | Condicionar/eliminar patch gpt-researcher por versão; registrar divergência em manifesto/SBOM; normalizar metadados/timestamps de build | A-001 | Dois builds limpos sem cache, entradas/builder identificados, image IDs iguais conforme aceite de origem; conteúdo/SBOM/patch coerentes; divergência medida permanece aberta se não resolvida |
| A-009 | F-010 / P2 | Declarar perfil RO/cap-drop/NNP/init e mounts mínimos explícitos; solicitar aplicação pelos gestores | S2-NB-X01 e S2-AP-X01; exceções com owner; etapa 5 IaC; `R-02` e `R-08` | Runtime do owner inspecionado com postura compatível; default sem bind (`mounts=[]`), sem `null` implícito, cache host não montado RW sem justificativa; operação em janela única datada e autorizada; sem alterar gestores pelo checkout MCP |
| A-010 | F-011 / P2 | Documentar volatilidade de research_id/cache de tópicos e efeito de recriação | Limitação stateless por design | README/contrato explicam expiração; sessão válida antes e erro explícito após recriação; não adicionar persistência por suposição |
| A-011 | F-012, F-013 / P3 | Derivar versão do produto em serverInfo e corrigir contagem de caracteres das fontes | Contrato preservado e versão do candidato | Handshake igual à versão do pacote (3.0.1 apenas se continuar vigente); fonte fixture com conteúdo conhecido não reporta zero incorretamente |
| A-012 | F-014, F-019, F-020, F-021 / P3 | Remover apt/setuid desnecessários; versionar harness; atualizar segurança/scan; metadata `server.json` e extensão PBLabs conforme `R-06`; gate VEX conforme `R-07` | S2-C03; recomendação S2-C04 pendente de aceite; CI e etapas 2/4 IaC | Inventário sem residuais incompatíveis, smoke verde; manifest conforme schema externo e destino `pblabs-mcp-index`; scan do candidato/DB atual e VEX por CVE associado ao image ID e assinado pelo owner; CVEs da imagem base tratados por herança |

Não copiar credencial de configuração para relatório/log. `R-01` encerra a
rotação como decisão explícita de risco; reescrever config ou reduzir mode não
revogaria a chave e não é solicitado. O risco residual permanece registrado.
F-019 é evidência positiva de reuso: preservar e vincular sua versão, não “corrigir
um bug”. Scan sem findings não justifica inventar CVEs/declarações VEX.

## 4. Lotes e handoffs

1. **DR-1:** A-001 define a combinação entregue/testada; A-002/A-003 corrigem
   rede e duração. A-004 é encaminhada aos owners para reconciliação autorizada;
   A-005 está encerrada por `R-01` e não deve gerar solicitação de rotação.
   Não executar alterações unilaterais em runtime ou credenciais.
2. **DR-2:** A-006/A-007/A-008/A-010/A-011; mudança de versão upstream requer
   revalidar timeout, retrievers, patch e formato público, não apenas imports.
3. **DR-3:** A-009/A-012 e parcela externa A-004, com contratos revisados,
   candidato/CI e operação autorizada. A-005 não exige rotação por `R-01`.
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
  timeout real medido; `V-DATA` stateless e volatilidade explícita. Para
  cancelamento MCP, documentar suporte/limitação conforme `R-09`; não se exige
  implementar cancelamento em todos os métodos.
- [ ] Se S2-C04 for aprovada, registrar revisão versionada e adoção em pelo
  menos dois MCPs; a recomendação ainda aguarda aceite do operador.
  `V-PILOT`, streaming/cancelamento MCP e provedores reais só com ensaio próprio;
  timeout interno não prova cancelamento end-to-end do protocolo.
- [ ] A-004/A-005/A-009 recebem evidências dos gestores corretos; publicação,
  CI remoto e smoke real não são inferidos da fixture local.

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
| A-003 (F-003) | **verificada** | O pipeline passou a rodar em processo isolado (`percival_research/research_worker.py`, cliente em `research_worker_client.py`); o pai aplica `PERCIVAL_RESEARCH_TIMEOUT_S` como limite rígido e mata o worker. Ensaio com upstream lento (`scripts/timeout_probe.py`, limite 2 s): resposta **“Error: Research exceeded the 2s internal limit” em 2,03 s**, sem “Research complete”, container encerrando com exit 0. O mesmo limite vale para o resource `research://{topic}`. Regressões: worker morto/recolhido, payload inválido rejeitado, caminho feliz do worker. | Cancelamento end-to-end do protocolo MCP (`notifications/cancelled`) continua não exercitado (E-042 herdado). |
| A-004 (F-004) | **pendente de gestores/janela autorizada** | Candidato rastreável pronto: imagem `percival-deep-research:stage2-candidate` com `org.opencontainers.image.revision` e labels de proveniência; `scripts/write_docker_ci_manifest.py` registra commit, image ID, digest, bases fixadas e lock. O pedido de reconciliação (imagem/estado de cada gestor) está descrito em `docs/runtime-profile.md`. | **Não executada:** nenhuma mutação de runtime de terceiros. Reconciliação continua com S2-NB A-007 / S2-AP-X01; pin e janela única datada dependem de aprovação operacional (`R-08`). |
| A-005 (F-005) | **encerrada por decisão explícita de risco (`R-01`)** | Formato de entrega por arquivo permanece especificado (`docs/runtime-profile.md`: `/app/.env` RO, host 0600, nunca valor literal no ambiente) e a leitura do arquivo foi verificada localmente. | A rotação não será executada nesta campanha: o operador aceitou manter a chave descartável de teste porque outros serviços dependem dela. O risco residual continua registrado; esta decisão não equivale a revogação ou correção técnica. |
| A-006 (F-006, F-016, F-018) | **verificada** | `/health` valida o retriever contra o registry real do `gpt-researcher` embarcado e detecta as variáveis de ambiente obrigatórias lendo o módulo upstream: `RETRIEVER=searx` com `SEARX_URL` → **200 healthy**; sem `SEARX_URL` → **503 degraded** (antes: sempre 503 para `searx`). `INFERENCE_LLM` malformado → `degraded`. Código inerte: `percival_research/retrievers/duckduckgo.py` passou a usar o pacote declarado `ddgs` (o `duckduckgo_search` não declarado saiu) e `httpx` passou a ser dependência declarada; o registry local ficou documentado como camada de extensão, fora do `/health`. | `/health` não valida reachability do provedor nem validade das credenciais — limitação declarada no README. |
| A-007 (F-007) | **verificada** | `addopts` do pytest passa a medir cobertura (`--cov=server --cov=utils --cov=config --cov=llm_bridge --cov=percival_research --cov-report=term-missing`) com `fail_under=70`: `uv run pytest -q` reporta **89,35 %** e falha quando o piso não é atingido (prova local: `--cov-fail-under=99` → exit 1; passo equivalente no CI). Documentação sincronizada (README, AGENTS, PROJECT). | — |
| A-008 (F-008, F-009) | **verificada** | Patch condicionado à versão: `scripts/patch_gpt_researcher.py` só aplica em 0.16.0, é no-op quando a versão não precisa e **recusa** versões desconhecidas. Divergência declarada em proveniência: labels `io.percival.gpt-researcher.version` / `.patch` e campo `gpt_researcher` no manifesto de build (SBOM CycloneDX no CI). Reprodutibilidade: `SOURCE_DATE_EPOCH` + `cp -a` (em vez de `COPY --from`, que carimba diretórios com a hora do build) → **dois builds `--no-cache` do mesmo SHA produzem o mesmo image ID** (`sha256:a53f74436c65…`), verificado por `scripts/check_reproducible_build.sh` (passo no CI). | A comparação usa `--provenance=false`: com a atestação padrão, o índice OCI carrega metadados por build (a identidade reproduzível é o manifest da plataforma). Divergência de conteúdo entre builds: 0. |
| A-009 (F-010) | **pendente de gestores/janela autorizada** (parcela local pronta) | Perfil declarado em `docs/runtime-profile.md`: user 1000, rootfs RO, `cap_drop ALL`, `no-new-privileges`, init do launcher, tmpfs, `pids_limit`, mounts mínimos (`/app/.env` RO 0600, logs, reports) e política de rede (só endpoint de inferência + retriever). A imagem deixou de precisar de cache de pacotes do host (sem `apt`/`pip` na imagem), o que elimina a justificativa do mount RW `pacman/pkg`. | **Não executada:** a aplicação do perfil nos gestores depende de S2-NB-X01/S2-AP-X01; o default do broker está decidido como `mounts=[]`, com `null` somente em operação separada, confirmada e auditada (`R-02`). Qualquer alteração de runtime exige janela autorizada (`R-08`); nenhuma alteração foi feita em gestores a partir deste checkout. |
| A-010 (F-011) | **verificada** | README documenta a volatilidade: `research_id` e cache de tópicos vivem em memória, expiram pelo TTL e são perdidos ao recriar o container; o erro explícito “Research ID not found or expired. Please run a new research session.” foi preservado e testado. Nenhuma persistência foi adicionada. | — |
| A-011 (F-012, F-013) | **verificada** | `serverInfo.version` deriva da versão do produto (`FastMCP(version=__version__)`); o harness de conformance compara o handshake com a versão de `pyproject.toml` e falha se divergirem. Contagem de caracteres das fontes corrigida: o upstream guarda o corpo em `raw_content`, e o formatador agora lê `raw_content` (com fallback para `content`) — a fonte de fixture com conteúdo conhecido reporta o tamanho real, não zero. | — |
| A-012 (F-014, F-019, F-020, F-021) | **parcial** | Hardening: `apt`/`apt-get`, `pip` e **todos** os binários setuid foram removidos da imagem (verificado: 0 setuid, `no-apt`, `no-pip`). Harness versionado e reutilizável; F-019 permanece evidência positiva de reuso. Segurança: scan Trivy 0.76.1 do candidato com **11 achados** (1 CRITICAL, 5 HIGH, 4 MEDIUM, 1 LOW em authlib/dnspython/litellm), nota e VEX específicos do candidato; CI falha se o Trivy reportar algo fora do VEX. `docker/server.json` usa imagem OCI e transporte stdio; a extensão operacional e o destino `pblabs-mcp-index` seguem `R-06`. | **Pendente:** vincular cada VEX ao image ID e obter assinatura do owner conforme `R-07`; placeholders de commit/digest resolvidos no release (imagem ainda não publicada). CVEs herdados da imagem base seguem a postura por herança. O upgrade de authlib/dnspython/litellm permanece aberto; publicação/catálogo aguardam as etapas 2/4. |

**Revalidação `V-*` (2026-10-28, escopo local):**

| Cenário | Estado | Observação |
|---|---|---|
| `V-BUILD` | aprovado | Build local `linux/amd64`, 8 camadas, `User=percival`, entrypoint e labels coerentes, **reprodutível** (dois builds limpos → mesmo image ID). |
| `V-RUN` | aprovado | Falha fechada sem credencial → exit 1; `SIGTERM`/EOF e o limite rígido de pesquisa verificados; sem container órfão no probe. |
| `V-CONFIG` | aprovado (parcial) | Segredo por arquivo, recusas de entrada e `/health` coerente com o registry real; a rotação foi explicitamente dispensada por `R-01`, com risco residual aceito. |
| `V-DATA` | não aplicável | Semântica stateless preservada; volatilidade documentada (A-010). |
| `V-MCP` | aprovado | Handshake real, 5 tools, 1 resource template, `serverInfo.version` = versão do produto, stdout JSON-RPC puro. |
| `V-FUNC` | **parcial** | Caminho feliz do worker e deadline verificados contra fixtures internas; pipeline real do upstream contra fixture de provedor **não** re-executado nesta rodada (A-002). Nenhum provedor real foi chamado. |
| `V-PILOT` | não avaliado | Requer agente e credencial real; não faz parte desta campanha. |
| `V-REUSE` | aprovado (candidato) | Harness versionado no produto, reusável pelos demais MCPs do lote; a recomendação de harness comum S2-C04 continua pendente de aceite. |

**Limites desta execução:** nenhuma chamada a provedor real; nenhuma mutação
de runtime ou de credencial de terceiros; a imagem candidata não foi publicada
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

**Retorno ao coordenador (2026-10-28):** o checkout IaC estava acessível;
a linha **S2-DR** da seção 3 e uma entrada na tabela da seção 7 do
[plano coordenador](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
foram atualizadas **preservando os retornos dos demais projetos**.
Contagem: **8 de 12 ações verificadas** (A-001, A-003, A-006, A-007, A-008, A-010,
A-011 e a parcela local de A-012), **2 parciais** (A-002 e A-012), **2 adiadas
por dependências de gestores** (A-004 e A-009) e **1 encerrada por decisão
explícita de risco** (A-005, `R-01`). O projeto permanece **parcial**:
transferências não encerram as dependências técnicas e a publicação continua
fora de escopo.
