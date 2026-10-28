# Stage-2 — Remediação do Percival Deep Research MCP

**Data / revisão:** 2026-10-27 / 1.0.  
**ID / estado:** S2-DR / planejado; execução não iniciada.  
**Checkout executor:** `/home/bill/Projects/percival-deep-research`.  
**Responsável:** executor Research a designar por bill; mudanças dos gestores e rotação com seus owners.

## 1. Objetivo, fontes e limites

Tratar integralmente os 21 registros da **seção 6** do
[relatório Deep Research](../../../positronic-bean-IaC/docs/reports/2026-10-27-percival-deep-research-iac-readiness-report.md#6-achados-issues-e-inconsistências),
incluindo a observação positiva F-019, as limitações por design e as falhas ainda
hipotéticas. Seções 7 e 9 fornecem 12 ações (5 P1, 5 P2, 2 P3), sem P0.
Baseline e HEAD na emissão: `defc9434487be4db7dbc13003db1709047297471`.
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

- [ ] Ler instruções/README/CI atuais; registrar SHA/worktree, Python, lock e versão
  efetivamente embarcada de `gpt-researcher`. Decidir versão alvo antes de alterar
  patch, health ou pipeline. Não fixar automaticamente 0.15.1 por ser o baseline.
- [ ] Usar inferência/retrievers simulados e rede interna controlada. “Sem egress”
  nesta prova significa sem saída à Internet, **com acesso à fixture de provedor**;
  não promete pesquisa real sem acesso aos provedores configurados.
- [ ] Medir cancelamento antes de escolher correção de timeout; a hipótese de
  `CancelledError` absorvido não prova qual mecanismo o corrigirá.
- [ ] Owner decide rede/custo e prazo por lote (D-06). D-04 permanece com o owner
  do broker; D-05 bloqueia ensaio integrado que exija receita ainda não decidida.

## 3. Backlog integral por ação

Todas as ações **não iniciadas**, inclusive as parcelas externas. Prioridades das
ações de origem preservadas; F-017 P1 está agrupado em A-001.

| Ação | Achados / P | Trabalho e áreas previstas | Dependências / dono externo | Aceite verificável |
|---|---|---|---|---|
| A-001 | F-001, F-017 / P1 | Falhar com exit não zero sem credencial e alinhar Python/dependências entre Dockerfile, CI e suíte | Decisão da versão alvo pelo produto | Startup sem credencial falha; suíte roda contra combinação realmente embarcada e CI a verifica; se alvo mudar, registrar em vez de exigir 0.15.1 histórica |
| A-002 | F-002, F-015 / P1 | Pré-popular cache tiktoken identificado na imagem; declarar/fixar mapa LiteLLM e destinos de rede | Política de rede com owner; S2-C01 | `research_deep` completo contra fixture interna sem Internet e sem cache externo; import não precisa de download oculto ou exceção explicitamente decidida |
| A-003 | F-003 / P1 | Investigar timeout/cancelamento em `tools/deep_research.py` e camada upstream; aplicar limite efetivo e limpar tarefas | Contrato de duração e hipótese discriminada | Limite 2 s contra pipeline 6 s devolve timeout em menos de 3 s, tarefas liberadas e sem “Research complete”; teste também o fluxo normal |
| A-004 | F-004 / P1 | Preparar candidato rastreável e solicitar reconciliação de imagens/estado de cada gestor | S2-NB A-007; S2-AP-X01; operação aprovada pelos owners | Runtime mostra revisão do candidato aprovado, não necessariamente SHA antigo da auditoria; saved/observed/connectivity coerentes e datados |
| A-005 | F-005 / P1 | Especificar entrega por arquivo e receber migração/rotação do owner do broker | D-04; S2-NB-X01 e A-005 Percival | Chave anterior revogada, nova por referência/arquivo RO, literal ausente da config e projeções; config 0600 e backups tratados; evidência sem valor de segredo |
| A-006 | F-006, F-016, F-018 / P2 | Alinhar `/health` ao registry real/suporte declarado, validar `INFERENCE_LLM` e remover código inerte ou declarar dependências | Versão decidida A-001 | Retriever suportado saudável; LLM malformado reflete configuração inválida/degraded; sem imports de pacote só transitivo; docs sincronizados |
| A-007 | F-007 / P2 | Ativar cobertura no comando canônico/CI e corrigir documentação | Política de teste existente >=70% | `uv run pytest -q` mede e aplica limiar 70%; prova de que queda abaixo falha; suíte normal verde |
| A-008 | F-008, F-009 / P2 | Condicionar/eliminar patch gpt-researcher por versão; registrar divergência em manifesto/SBOM; normalizar metadados/timestamps de build | A-001 | Dois builds limpos sem cache, entradas/builder identificados, image IDs iguais conforme aceite de origem; conteúdo/SBOM/patch coerentes; divergência medida permanece aberta se não resolvida |
| A-009 | F-010 / P2 | Declarar perfil RO/cap-drop/NNP/init e mounts mínimos; solicitar aplicação pelos gestores | S2-NB-X01 e S2-AP-X01; exceções com owner; etapa 5 IaC | Runtime do owner inspecionado com postura compatível; cache host não montado RW sem justificativa; sem alterar gestores pelo checkout MCP |
| A-010 | F-011 / P2 | Documentar volatilidade de research_id/cache de tópicos e efeito de recriação | Limitação stateless por design | README/contrato explicam expiração; sessão válida antes e erro explícito após recriação; não adicionar persistência por suposição |
| A-011 | F-012, F-013 / P3 | Derivar versão do produto em serverInfo e corrigir contagem de caracteres das fontes | Contrato preservado e versão do candidato | Handshake igual à versão do pacote (3.0.1 apenas se continuar vigente); fonte fixture com conteúdo conhecido não reporta zero incorretamente |
| A-012 | F-014, F-019, F-020, F-021 / P3 | Remover apt/setuid desnecessários; versionar harness; atualizar segurança/scan; metadados sem placeholder, server.json e decisão VEX | S2-C03/C04; CI e etapas 2/4 IaC | Inventário sem residuais incompatíveis, smoke verde; harness versionado/reutilizável; nota e scan do candidato/DB atual; metadata válida e VEX específico quando aplicável |

Não copiar credencial de configuração para relatório/log. Reescrever config ou
reduzir mode **não** revoga chave exposta; A-005 só fecha com retorno da rotação.
F-019 é evidência positiva de reuso: preservar e vincular sua versão, não “corrigir
um bug”. Scan sem findings não justifica inventar CVEs/declarações VEX.

## 4. Lotes e handoffs

1. **DR-1:** A-001 define a combinação entregue/testada; A-002/A-003 corrigem
   rede e duração. A-004/A-005 são solicitadas imediatamente aos owners, em paralelo,
   sem execução unilateral no runtime ou na credencial.
2. **DR-2:** A-006/A-007/A-008/A-010/A-011; mudança de versão upstream requer
   revalidar timeout, retrievers, patch e formato público, não apenas imports.
3. **DR-3:** A-009/A-012 e parcelas externas A-004/A-005, com contratos revisados,
   candidato/CI e operação autorizada. Publicação e catálogo aguardam etapas 2/4;
   lifecycle completo é etapa 5 IaC.

Riscos: timeout externo pode deixar trabalho órfão; alteração de dependência muda
retrievers/patch; hardening pode exigir paths temporários explícitos. Medir e
registrar alternativas com o owner. Sem prazo/orçamento fechado nesta emissão.

## 5. Qualificação futura no projeto

- [ ] Regressões dos achados e `uv run pytest -q` (cobertura ativada em A-007);
  lint/format **check** conforme CI. Nenhuma medição histórica vira resultado atual.
- [ ] Build canônico identificado e suíte com Python/gpt-researcher da imagem.
  Handshake/tools/call e pipeline completo usando mocks de inferência/retriever.
- [ ] Repetir `V-BUILD`/`V-RUN`/`V-CONFIG`/`V-MCP`/`V-FUNC`, signals/EOF e
  timeout real medido; `V-DATA` stateless e volatilidade explícita.
- [ ] `V-REUSE` tem revisão versionada e adoção em pelo menos dois MCPs (S2-C04).
  `V-PILOT`, streaming/cancelamento MCP e provedores reais só com ensaio próprio;
  timeout interno não prova cancelamento end-to-end do protocolo.
- [ ] A-004/A-005/A-009 recebem evidências dos gestores corretos; publicação,
  CI remoto e smoke real não são inferidos da fixture local.

Aceite local distinto de qualificação externa. Se houver rotação, publicação ou
reconciliação pendente, o resultado é parcial/bloqueado, nunca solução integral.

## 6. Penúltima etapa — documentar execução neste plano

- [ ] Atualizar por ação: mudança, owner/data, SHA inicial/final, ambiente/versões,
  comandos/resultados, evidências sanitizadas locais e decisões pendentes.
- [ ] Registrar revalidação `V-*` e limites; acrescentar retorno à seção 9 do
  relatório IaC quando autorizado, preservando sua coleta original.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| Pendente | A-001–A-012 | A registrar | Nenhuma execução nesta emissão | Não iniciada |

## 7. Última etapa — atualizar o plano coordenador

- [ ] Reler o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md);
  atualizar **S2-DR na seção 3** e acrescentar entrada na **seção 7**, com contagens,
  SHA/evidência, dependências liberadas e aceites locais/externos.
- [ ] Preservar outros retornos e indicar impacto nas etapas 2/4/5. Se não houver
  acesso ao checkout IaC, entregar resumo e manter **aguardando sincronização**.
  Concluído exige todos os aceites e retorno; transferência não é correção verificada.
