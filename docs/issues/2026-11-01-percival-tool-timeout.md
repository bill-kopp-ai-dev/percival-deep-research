# Deep Research expira no timeout do cliente Percival

- **Status:** resolvida no fluxo funcional de pesquisa → contexto/fontes → relatório nos dois agentes em 2026-11-01: Positronic verificado diretamente, Percival reportado pelo owner; ressalvas de proveniência/qualidade do relatório permanecem abertas, sem timeout no reteste
- **Reportado em:** 2026-11-01
- **Severidade proposta:** alta; `research_deep` é o fluxo principal do produto
- **Imagem testada inicialmente:** `sha256:4fd1d8d01b242cafe57603ac2c04bc12e34843b54f7b4bf72a83802d7eaaa61d`
- **Imagem pinada no follow-up reportado:** `sha256:b44a6a6e4fe9a80e44111c77732be1f2154a0744085ded92ed80de58045413aa`
- **Imagem atual Positronic:** `sha256:52dc1bed7a890c04a188eb5f82ca0fa945479c22030a7b615cc7f0c019e83652` (instalação revisão 22, container running, configuração revisão 1)
- **Imagem Percival pinada pelo owner:** `sha256:52dc1bed7a890c04a188eb5f82ca0fa945479c22030a7b615cc7f0c019e83652`; captura mostra `update-image · committed`, running/connected e 5 tools; a pinagem não foi executada por este agente
- **Source revision (OCI label):** `5093cab8bcb349177a0789be59875ec0908f999a`
- **Evidência atual:** captura e E2E Percival fornecidos por Bill nesta sessão; suíte canônica, lint/format, conformance Docker, fixture de cinco tools/cancelamento/deadline e chamadas diretas Positronic previamente verificadas; detalhes abaixo; seções anteriores preservam o histórico

## Confirmação do owner: pin e E2E Percival bem-sucedidos — 2026-11-01

Bill compartilhou a captura de pinagem e o relatório do agente Percival e
confirmou que ambos os testes (Positronic e Percival) foram bem-sucedidos,
solicitando registrar no plano. Esta seção é a evidência canônica desse retorno;
o plano S2-DR a referencia. O relato Percival não foi reexecutado nem inspecionado
independentemente pelo Positronic nesta atualização documental.

### Identidade e estado reportados

- A captura mostra `deep-research` em
  `sha256:52dc1bed7a890c04a188eb5f82ca0fa945479c22030a7b615cc7f0c019e83652`,
  o mesmo image ID validado no Positronic.
- Docker state e gateway intent `running`, MCP connectivity `connected`,
  enabled in gateway `yes`, **5 tools observadas**.
- Atividade recente mostra `update-image` iniciado em 2026-11-01 às
  **21:13:36** e `committed` às **21:13:42**, conforme horário exibido na UI;
  o timezone não aparece na captura.
- A UI informa bridge network, Full host access e 3 variáveis de ambiente.
  Ela não fornece os valores dessas variáveis, mounts detalhados nem uma nova
  prova de perfil hardened; A-009 permanece separado do aceite funcional.

### Sequência real reportada pelo Percival

ID real copiado sem alterações e reutilizado nas quatro chamadas:

```text
b4a68b7b-e9b3-434e-bc0c-c854481085ee
```

| Tool | Resultado reportado | Duração aproximada |
| --- | --- | --- |
| `research_deep` | OK; 9 fontes e 12 URLs em `source_urls`; preview de URLs truncado com `… (+2 more)` | 18,9 s |
| `research_get_context` | OK; 166 429 caracteres, persistidos e lidos localmente para conferir citações; preview truncado | 7,8 s |
| `research_get_sources` | OK; 9 fontes com título, URL e tamanho | 4,0 s |
| `research_write_report` | OK; relatório Markdown retornado antes do timeout | 54,3 s |

Total reportado: **aproximadamente 85,0 s**, quatro chamadas MCP. Não houve
retry, nova pesquisa, cache/resource ou ID de outra chamada. Além das tools,
o relato informa somente cronometragem com `date -u` e leitura/busca local no
arquivo já persistido; o path desse arquivo não foi fornecido. As durações do
Percival são cronometragens reportadas de chamadas, distintas das durações de
worker medidas nos logs Positronic abaixo.

O owner reporta conferência do contraste principal contra a documentação oficial
Python **3.15.2**, com os trechos nas linhas 1028–1065 e 1246–1251 do contexto:
falha não-CancelledError no TaskGroup cancela/aguarda as demais tasks e agrupa
falhas; gather padrão propaga a primeira exceção sem cancelar as outras.
Os casos especiais KeyboardInterrupt/SystemExit também foram identificados.
Esses números de linha pertencem ao contexto persistido do ensaio, não são
âncoras estáveis da página web.

O ensaio Percival não incluiu `research_quick_search`, nem nova leitura do
resource template ou dos prompts; não inferir esses resultados a partir das
quatro chamadas. A busca rápida foi validada diretamente no Positronic, conforme
a seção seguinte.

### Ressalvas preservadas — DR-OBS-01 (aberta)

O sucesso funcional não encerra as limitações de proveniência/qualidade
identificadas pelo owner:

1. Duas URLs Stack Overflow (`/questions/79836234/…` e
   `/questions/42231161/…`) aparecem em `source_urls`, mas não na lista de
   9 fontes recuperadas. Há uma divergência observada entre os conjuntos;
   ainda não foi discriminado se resulta da diferença entre URLs visitadas e
   fontes efetivamente extraídas, de falha de coleta ou de defeito no contrato.
2. O relatório afirma que nenhum resultado/URL Stack Overflow foi retornado,
   contradizendo a lista `source_urls` reportada. A precisão do relatório nesse
   ponto não foi aceita.
3. A URL inglesa `https://docs.python.org/3/library/asyncio-task.html` foi
   citada pelo relatório, mas não consta no getter de fontes desse ensaio.
   Pode ser reconstrução pelo modelo; a proveniência dessa citação permanece
   não confirmada, sem inferir coleta a partir da URL plausível.
4. A afirmação sobre não garantir coleta de falhas hipotéticas após cancelamento
   não foi verificada diretamente. A versão observada foi 3.15.2; introdução de
   TaskGroup em 3.11 não significa que a página consultada fosse da versão 3.11.

**Próximo trabalho de qualidade:** reconciliar a semântica de `source_urls`,
fontes extraídas e contexto e verificar as citações/alegações negativas do
relatório contra os dados daquela sessão. Responsável pelo acompanhamento:
Bill/Positronic, no próximo ciclo de qualidade. Nenhuma causa ou correção foi
declarada comprovada nesta atualização; não é necessário repetir o E2E somente
para registrar seu resultado.

**Aceite registrado:** fluxo principal concluído com sucesso nos dois agentes,
com a mesma candidata local, e ressalvas DR-OBS-01 abertas. Isso encerra a falha
de timeout no cenário testado, não qualifica automaticamente hardening,
publicação, resource/prompts ou precisão integral do conteúdo gerado.

## Aceite funcional real após liberação da cota — 2026-11-01, 21:02–21:08 -03:00

O owner informou que a indisponibilidade de cota provavelmente havia sido
resolvida e autorizou retomar os ciclos. A mesma credencial do mount existente
foi mantida; não foram comprados créditos nem alterada autenticação. O reteste
confirmou que o bloqueio 402 deixou de ocorrer no fluxo exercitado.

### Primeiro E2E real da retomada

Na imagem `7128f9ac…`, foi repetida a mesma pergunta pública em português sobre
`asyncio.TaskGroup` e `asyncio.gather`, com `include_context=false`:

- `research_deep` concluiu com ID
  `a3e45ba2-277f-491e-970f-c8ed77009afe` e **8 fontes**, incluindo a documentação
  oficial Python 3.11.18.
- `research_get_context` e `research_get_sources` retornaram dados desse ID,
  mantendo o prefixo de conteúdo externo não confiável.
- `research_write_report`, com custom prompt em português, concluiu e citou
  a documentação oficial, mas incluiu um bloco auxiliar `<think>` do provider
  antes do relatório.
- `research_quick_search` retornou **5 resultados**, incluindo docs.python.org.

Isso confirmou o restabelecimento de inferência e busca, mas motivou corrigir
a saída pública do relatório antes de aceitar a candidata final.

### Correção adicional e imagem

`run_report_worker` agora remove somente envelopes auxiliares `<think>...</think>`
no início da resposta do provider. Blocos literais no corpo/Markdown são
preservados; envelope incompleto ou resposta sem relatório final é erro, não
sucesso. Seis casos de regressão cobrem Markdown simples, prefixo, prefixos
repetidos/case-insensitive, tags literais e respostas incompletas/sem conteúdo.
O harness também simula um prefixo auxiliar e confere que ele não chega à tool.

- Tag: `percival-deep-research:3.0.1-5093cab-f2-6735820b62ca`.
- Image ID: `sha256:52dc1bed7a890c04a188eb5f82ca0fa945479c22030a7b615cc7f0c019e83652`.
- Base de fonte: `5093cab8bcb349177a0789be59875ec0908f999a`, worktree **dirty**.
- SHA-256 do diff no build:
  `6735820b62ca733805076633b60eee616ee26c545407d97c78237993606427bf`.
- Build pelo script canônico com `--worktree-candidate`; linux/amd64, versão
  3.0.1, bases e `uv.lock` preservados. É uma candidata local, não release limpa.
- Pin aplicado pelo CLI Positronic com CAS **21 → 22**; configuração reaplicada,
  revisão **1**, configuration ID `38ecdaa7-d72e-4c30-bea7-63ed450c6e55`.
- Mesmo mount RO e overrides MiniMax documentados na campanha anterior; cinco
  tools descobertas. A imagem anterior permaneceu disponível para rollback.

### E2E real da imagem final — passou

A pergunta foi novamente a mesma, em uma pesquisa nova necessária para testar
a nova encarnação do servidor. ID retornado e reutilizado exatamente em todas
as chamadas de sessão:

```text
a675e787-8bc5-4a3c-9e7e-c34d36a65780
```

| Tool | Evidência observada |
| --- | --- |
| `research_deep` | `Research complete.`, ID válido acima, `source_count: 7`; docs.python.org nas fontes |
| `research_get_context` | Conteúdo não vazio, prefixo `[SECURITY WARNING: ...]`, páginas oficiais Python em português e inglês |
| `research_get_sources` | `source_count: 7`; títulos, URLs e contagens de caracteres; documentação oficial entre as fontes |
| `research_write_report` | Chamada **padrão, sem custom prompt**, retornou relatório Markdown completo com referências, sem prefixo `<think>` |
| `research_quick_search` | Consulta `Python asyncio TaskGroup gather cancellation`, `result_count: 5`, incluindo documentação oficial |

O conteúdo central do relatório correspondeu ao trecho oficial recuperado:
TaskGroup cancela/aguarda tarefas irmãs em falha não-CancelledError; gather
padrão propaga a primeira exceção sem cancelar as outras. O relatório padrão
veio em inglês. Não foi feita auditoria exaustiva de toda a prosa, exemplos ou
metadados bibliográficos gerados; o aceite aqui é funcional do fluxo MCP e
inclui uma conferência do contraste técnico principal, não garantia de toda
afirmação gerada.

Logs content-free da imagem final (UTC; a data local ainda é 2026-11-01):

```text
2026-11-02T00:07:38.574644507Z worker=84b5be41d190 pid=21 operation=research timeout_s=90 started
2026-11-02T00:07:53.360548172Z worker=84b5be41d190 pid=21 operation=research outcome=completed last_stage=complete reaped=True
2026-11-02T00:07:54.632482126Z [crl-cd80a63e] Research complete. ID: a675e787-8bc5-4a3c-9e7e-c34d36a65780
2026-11-02T00:08:04.504925938Z worker=35fa0cbb6ace pid=57 operation=report timeout_s=90 started
2026-11-02T00:08:31.916698020Z worker=35fa0cbb6ace pid=57 operation=report outcome=completed last_stage=complete reaped=True
```

Durações dos workers: pesquisa **14,79 s**, relatório **27,41 s**, ambos abaixo
de 90 s. Não são medidas exatas da latência de transporte inteira. O fallback
Yahoo retornou resultados para subconsultas mesmo com buscas DuckDuckGo vazias;
isso demonstra uso efetivo do fallback, não restauração do backend DuckDuckGo.
`docker inspect` confirmou imagem/labels em
`positronic-mcp-deep-research-6670fb6ccfa3`; `docker top` ao final mostrou somente
init + servidor, sem worker órfão.

### Verificação automatizada da revisão candidata

- Patch pós-sync obrigatório executado; `uv run pytest -q`: **454 passed,
  3 skipped**, cobertura **88,96%** (mínimo 70%). Os três skips continuam sendo
  integrações HTTP com servidor separado; o E2E real acima foi executado pelas
  tools do agente.
- Ruff check/format e `git diff --check`: passaram.
- Conformance da imagem final: initialize + tools/list, cinco tools, UID 1000,
  chave fictícia, passou.
- Pipeline fixture da imagem final, `--mode success --delay 31`: passou,
  **40,105 s** na pesquisa, cinco tools exercitadas, **2** chamadas de
  inferência fictícia, **0** embeddings, **0** workers restantes. Inclui
  regressão de remoção do envelope auxiliar no relatório.
- Sem commit, push ou publicação nesta retomada. O gestor Percival não foi
  alterado. Esta seção da issue foi escrita após o build e não integra seu
  hash de diff; o README já estava atualizado no contexto da imagem.

**Conclusão/continuidade:** problema resolvido no aceite local das cinco tools
no Positronic, com a conta MiniMax e os motores públicos disponíveis neste
ensaio. Não há bloqueio atual nesse aceite. Manter a imagem pinada e executar
novo diagnóstico somente se houver regressão, mudança de credencial/provider
ou nova candidata. Os bloqueios 402 e buscas vazias abaixo são históricos e
foram superados pelos resultados desta seção, não apagados do registro.

## Ciclos de correção autorizados pelo owner — 2026-11-01

O owner autorizou repetir avaliação → correção → build → pinagem no Positronic →
avaliação até o servidor funcionar. Aceite definido: pesquisa real retorna ID
válido, contexto e fontes recuperáveis, relatório gerado do mesmo ID e busca
rápida funcional. **Esse aceite real não foi alcançado**: há dependência externa
de cota MiniMax e os últimos testes de busca pública retornaram vazios.

### Achados e correções

1. O worker isolado não chamava `install_bounded_retrievers`; somente a tool
   rápida aplicava o retriever limitado. A instalação agora ocorre dentro do
   worker antes da pesquisa, com regressão que falha se ele perder a substituição.
2. O cliente Positronic interrompia aos ~60 s sem progresso. O worker agora
   emite notificações MCP a cada 10 s, com segundos decorridos, sem percentual
   fictício ou conteúdo da pesquisa. O deadline interno de 90 s continua rígido.
   Uma regressão usa transporte MCP em memória e confere ausência de tarefa de
   progresso após conclusão; chamadas Positronic reais passaram dos 60 s e
   receberam a resposta interna aos 90 s.
3. DDGS não oferecia resultado utilizável no backend DuckDuckGo nos ensaios.
   O primeiro fallback tentou `bing`, mas a versão instalada marca esse engine
   como desativado e silenciosamente volta a `auto`. Foi substituído por
   `yahoo`, ativo no registry, com validação pré-dispatch contra engines ausentes
   e no máximo dois backends explícitos, cada um com socket timeout de 5 s.
   Os ensaios diretos demonstraram disponibilidade variável: Yahoo produziu
   resultados em um diagnóstico e depois nenhum resultado nas chamadas finais.
   Não há garantia de disponibilidade desses motores públicos.
4. Diagnóstico da configuração carregada com `runtime_env` mostrou endpoint
   MiniMax com modelo default `gpt-4o-mini`, e base URL terminando em
   `/v1/text/chatcompletion_v2`. O SDK acrescentava `/chat/completions`; uma
   chamada sem retries recebeu 404 em 1,47 s. Foi configurado explicitamente
   `MiniMax-M2.7` e a base compatível `https://api.minimax.io/v1` via gestor.
   Referência verificada em 2026-11-01:
   [documentação oficial MiniMax OpenAI SDK](https://platform.minimax.io/docs/api-reference/text-openai-api).
5. O upstream repetia falhas permanentes até dez vezes na completion e ainda
   fazia retries/fallback no planner, mascarando 404/402 como timeout. O patch
   obrigatório de `gpt-researcher==0.16.0` agora faz essas camadas propagarem
   400/401/402/403/404/405/413/422 sem retry. Erros transitórios não receberam
   essa regra. O worker transmite somente status allowlisted; as tools retornam
   erro MCP sanitizado com correlation ID e preservam sessão em falha de relatório.
6. Logs do worker mantêm marcadores/contagens/durações e tipo de exceção
   allowlisted; stderr upstream, prompts, respostas e credenciais continuam
   privados. `outcome=failed` distingue saída não-zero de processo concluído.

### Imagens e avaliações por ciclo

Todas as imagens são candidatas locais `linux/amd64`, versão 3.0.1, base
`5093cab8bcb349177a0789be59875ec0908f999a` com alterações não commitadas,
construídas pelo builder canônico Nanobot com `--worktree-candidate`. Não são
releases limpas nem imagens publicadas. Lock `uv.lock` preservado:
`940ec7e4cc2429598b8e4ed4a7ba377124a998bde7f837baa919018dce5f04d0`.

| Ciclo | Image ID | SHA-256 do diff no build | Resultado real Positronic |
| --- | --- | --- | --- |
| 1 | `sha256:7700cece3deca774e21eb31328575e6d015ca14d1940502326cb900c362cbb21` | `6c0d4980d3b9c39ea9e0d1837265abc5e557cd942cb53950dd510d8adf81a356` | Quick search retornou 5 resultados; deep falhou em ~10,41 s, `crl-4d905eee`, worker `718fa52df98e`, stage `search_engine`. A descoberta de `bing` desativado invalida a interpretação de que aquele sucesso provava fallback limitado. |
| 2 | `sha256:27388cb208c0bb06c504c18d6beb0b8db7c8643ba03b10eee6ad00c9d2f434f4` | `d1ceaf6416622fea58452e066cd7d0f0a2fbbd8c9353d3270d0762e259481c20` | Deep recebeu timeout interno 90 s, `crl-c558ae8e`; após corrigir somente modelo, ainda 90 s, `crl-bb4e4f4c`. Diagnóstico posterior confirmou base URL errada e depois cota esgotada na URL correta. |
| 3, pin final | `sha256:7128f9ac45ff876290e424e6f4986bf561b04a0f4e14866f9fc30e9acbcf492c` | `6e4753d66bf88f402de9adaad4c8096182d91967bea159065b90fea8a37f6d89` | Deep retornou erro HTTP 402 explícito, `crl-dbc25113`, sem pesquisa válida, worker 9,26 s, recolhido. Dois testes rápidos (`asyncio TaskGroup cancellation`, `asyncio TaskGroup`) retornaram `result_count: 0`. |

As durações acima são dos timestamps do worker, não medições exatas de toda a
latência MCP. A pergunta de deep foi a mesma pergunta pública em português
sobre TaskGroup/gather em todos os ciclos. Nenhuma chamada real produziu ID;
getters/relatório reais não foram executados sem ID. A autorização iterativa
substituiu a restrição de chamada única da campanha anterior; cada tentativa
acima foi uma avaliação intencional, não retry oculto do agente.

### Bloqueio externo confirmado

Com o endpoint compatível e a credencial já montada, chamada direta sem retry
retornou HTTP 402, mensagem do provider (sem segredo):

```text
The Token Plan usage limit has been reached. To avoid interruption, please upgrade your plan or buy credits and turn on auto consumption. (2067)
```

A tool Positronic, na imagem final, agora retorna:

```text
Error: Inference provider rejected request (HTTP 402: provider quota or billing limit reached). (correlation_id=crl-dbc25113)
```

Não foram comprados créditos, habilitada cobrança automática, trocada credencial
ou consumido outro provider. Isso exige disponibilidade externa da conta; não
é corrigível por timeout. A busca pública vazia também impede afirmar que o
backend live está validado. Se persistir após a liberação da cota, avaliar um
retriever suportado com disponibilidade estável, sem aceitar pesquisa vazia como
sucesso.

### Verificação da candidata final

- `uv run pytest -q`: **448 passed, 3 skipped**, cobertura **88,60%** (mínimo
  70%). Os skips são integrações que exigem servidor HTTP separado, não testes
  real-provider aprovados. O patch pós-sync foi executado antes da suíte.
- Ruff check/format e `git diff --check`: passaram.
- `docker-ci-conformance.py`: initialize/tools-list passou nas três imagens,
  com as cinco tools, UID 1000 e credencial fictícia, sem rede externa.
- `pipeline_probe.py --mode success --delay 31`, imagem final: **passou**,
  pesquisa em **39,778 s**, ID real da fixture usado em contexto/fontes/relatório,
  quick search também exercitada, cache recuperado, **2 chamadas de inferência
  fictícia**, **0 embeddings**, **0 workers restantes**, cinco tools exercitadas.
  Usa o código do broker/wrappers em fixture descartável, não modifica instalação
  Percival. É evidência sintética, não aceite da conta/provider real.
- `pipeline_probe.py --mode cancel`, imagem final: **passou**, 5,974 s até
  cancelamento observado, 1 chamada fictícia, 0 embeddings e 0 workers restantes.
- `timeout_probe.py --timeout 2 --max-elapsed 3 --upstream-delay 30`: **passou**,
  erro interno em **2,034 s**, exit 0. Um ensaio anterior usou timeout 3 com
  orçamento total também 3 s e falhou a asserção em 3,038 s; isso não foi
  reportado como pass. O segundo usa o orçamento padrão documentado (2+1 s).
- A primeira invocação da pipeline pela venv Deep Research falhou antes do
  ensaio por faltar `tzlocal` do Nanobot. Foi repetida na venv de testes Percival
  já existente (`runtime/tmp/opencode/.venv-percival`), que passou. Nenhuma
  dependência de produção foi alterada para acomodar o harness.
- Runtime final: `positronic-mcp-deep-research-05eafd6b1b93`, imagem/labels
  conferidos por inspect, apenas init + servidor em `docker top` após os testes.

### Estado gerenciado e continuidade

Pin final Positronic: revisão de instalação **21**, configuration ID
`421529fa-2172-4372-b39e-e15040dbfcd3`, config revisão **1**, global/ativado,
rede bridge, mesmo mount read-only em `/app/.env`, cinco tools permitidas.
Overrides públicos via `mcp server configure`:

```text
INFERENCE_LLM=minimax:MiniMax-M2.7
INFERENCE_BASE_URL=https://api.minimax.io/v1
OPENAI_BASE_URL=https://api.minimax.io/v1
```

Os pins/configurações anteriores foram lidos antes de cada mutação; os image
IDs anteriores foram preservados para rollback. A documentação README e esta
issue foram atualizadas depois do build final; o label de diff identifica o
estado exato no momento do build, não o diff documental subsequente. Não houve
commit, push, publicação ou mutação do gestor Percival nesta campanha.

**Próxima ação do owner:** liberar a cota do Token Plan ou fornecer uma
configuração de inferência autorizada e disponível. Depois, retomar na imagem
final, repetir pesquisa pública → contexto/fontes → relatório com o mesmo ID e
confirmar resultados da busca rápida. Manter o aceite real aberto até esse
fluxo passar; a fixture não o substitui.

## Deploy e teste direto no Positronic — 2026-11-01

### Reteste Percival reportado pelo owner

Após o pin de `a6efc34d…`, o owner reportou uma única chamada real, sem retry,
que retornou:

```text
Error: Research exceeded the 90s internal limit (correlation_id=crl-a61d351c). Try a more specific query or increase PERCIVAL_RESEARCH_TIMEOUT_S.
```

Houve mensagem de erro entregue ao cliente, mas não resultado de pesquisa nem
`research_id`; o relato de "sem corpo de resposta" não significa ausência de
qualquer resposta de transporte neste caso. A duração de cerca de 90 s foi
inferida da mensagem, sem medição instrumental do cliente. Getters/relatório não
foram executados. Esse episódio é distinto do bloqueio anterior de 175 s sem
resposta; os logs do correlation ID acima não foram coletados nesta atualização.

### Deploy Positronic solicitado pelo owner

Foi atualizada a instalação **global do Positronic**, sem usar o manager
Percival nem editar estado gerenciado à mão. CLI utilizado:
`/home/bill/.local/bin/positronic-server-cli mcp server`.

- Antes: servidor `deep-research`, revisão 17, imagem `b9ef1cb0…`, configuração
  com allowlist somente `research_quick_search`.
- `update-image` com revisão esperada 17 aplicou
  `sha256:a6efc34dc869af732e1d5af7df537037b67170821837473c95465e444e505ec5`,
  avançando para revisão 18, configuration ID
  `658d29b7-2ef0-4be2-ac84-1419e8121998`.
- Configuração reaplicada pelo gestor (nova config revisão 1): rede `bridge`,
  mesmo arquivo de credenciais já existente montado em `/app/.env` read-only e
  allowlist das cinco tools públicas. Credenciais não foram lidas nem expostas.
- `discover` retornou as cinco tools. O container
  `positronic-mcp-deep-research-904546b35ba4` foi confirmado `running`, com o
  image ID novo e OCI revision `5093cab8bcb349177a0789be59875ec0908f999a`.
  O container Percival também continuava no mesmo image ID; nenhuma mutação foi
  feita no manager Percival nesta campanha.
- Rollback: imagem anterior `sha256:b9ef1cb0c577b2e38ee4a42d73a55df3aaa5642cf9446116f933a672d086d835`
  confirmada disponível antes da alteração; configuração anterior descrita acima.

### Chamada direta única e evidência de execução

A tool `research_deep` do agente Positronic foi chamada uma única vez com a
mesma pergunta pública sobre `asyncio.TaskGroup`/`asyncio.gather` e
`include_context=false`. Resultado completo do cliente:

```text
MCP error -32001: Request timed out
```

Não houve `research_id`; nenhum retry, busca alternativa, getter ou relatório
foi executado. Timestamps externos anteriores/posteriores à chamada delimitam
uma janela de 68,83 s (inclui overhead das ferramentas). Os timestamps do worker
mostram **59,90 s entre início e cancelamento**; não confundir essa medida com
tempo exato de transporte da chamada:

```text
2026-11-01T22:32:24.704843552Z worker=de4c2db68ce9 pid=21 operation=research timeout_s=90 started
2026-11-01T22:33:24.599173768Z worker=de4c2db68ce9 pid=21 operation=research outcome=cancelled last_stage=search reaped=True
```

O timeout do cliente Positronic interrompeu esta execução antes do deadline
interno de 90 s. O processo filho foi recolhido (`reaped=True`); a última etapa
instrumentada foi `search`, não conclusão/sucesso. Isso localiza a execução no
caminho de busca, mas não identifica motor, subconsulta, espera de rede ou
chamada ao modelo específica como causa raiz. A instrumentação traduz eventos
upstream em marcadores e não mede isoladamente cada operação.

**Próximo passo:** inspecionar e alinhar o timeout efetivo de chamada do cliente
Positronic com o deadline interno antes de autorizar outro ensaio; investigar
busca usando o estado/diagnóstico já obtido. Aumentar o timeout não é evidência
de correção do gargalo observado no Percival aos 90 s. O deploy Positronic está
concluído; o aceite funcional E2E permanece aberto.

## Falha E2E e sintomas amplos do broker — relato do owner, 2026-11-01

### Resultado do teste solicitado

O owner realizou uma única chamada de `research_deep` com a consulta pública
especificada, sem retry e sem busca alternativa. O cliente expirou após **175,12
s**, sem receber corpo HTTP/MCP:

```text
[175.12s] EXCEPTION TimeoutError: timed out
```

Não houve resposta HTTP, corpo nem `research_id`. Conforme o procedimento do
ensaio, `research_get_context`, `research_get_sources` e `research_write_report`
não foram chamados; não houve recuperação por cache/recurso. Portanto, nenhuma
conclusão sobre o conteúdo pesquisado ou a imagem Deep Research pode ser tirada
deste ensaio. O owner relata uma única chamada de pesquisa, cujo eventual estado
interno não pôde ser observado.

### Sintomas de transporte relatados

O diagnóstico read-only do owner reporta, no mesmo ambiente:

| Rota/ação | Resultado reportado |
|---|---|
| `POST /v1/health` | HTTP 200 em 0,10 s |
| `POST /v1/status` | timeout após 10–12 s |
| `POST /v1/observe` com source válido | timeout após 20 s |
| `POST /mcp/notes` — `initialize` | timeout após 25 s |
| `POST /mcp/deep-research` — `initialize` | timeout após 25 s |
| tool `notes_get_status` | cliente MCP expirou em 30 s |
| `POST /mcp/deep-research` — `research_deep` | cliente expirou em 175,12 s, sem corpo |

Esses resultados sugerem que o incidente não está limitado ao pipeline de
pesquisa Deep Research: o problema também afeta operações do broker e um segundo
servidor MCP. A comparação só localiza a falha na camada comum se os endpoints
`notes` e `deep-research` forem servidos pela mesma instância do broker e as
medições pertencerem ao mesmo intervalo operacional; isso ainda precisa ser
correlacionado por timestamp, processo e request ID.

O owner reporta ainda: `deep-research` ativo/`running`, cinco tools configuradas,
imagem `1863c62b…`, configuração global na revisão `34`, servidor na revisão `6`,
sem `pendingTransitions`; hashes de `config.json`/`audit.jsonl`, contagem de
linhas e backups permaneceram iguais durante a coleta. Se corretos, esses dados
indicam que o diagnóstico não fez mutações de manager além da chamada MCP
solicitada. O ambiente de diagnóstico não tinha Docker CLI nem socket disponível,
limitando a inspeção de processos e logs.

### Análise do lock: hipótese plausível, mas não demonstrada

Inspeção estática do `nanobot/nanobot/mcp_docker/broker.py` (commit `52304783`)
confirma que `/v1/status` (`action("status")`) só verifica `_STORE` sob o lock
global `_LOCK`; essa rota não chama Docker. Porém, não é correto concluir que uma
chamada MCP longa, por si só, retém esse lock:

- `tools/call` passa por `_admit_mcp_request`, que adquire o lock **por servidor**
  e o mantém durante `_exchange`; a operação pode esperar por `docker attach`/
  resposta stdio e bloquear chamadas ao mesmo servidor, mas não mantém `_LOCK`
  global durante essa espera normal.
- O broker marca `transport_uncertain` sob `_LOCK` se o cancelamento/limpeza do
  transporte falha. Isso é uma seção curta; a flag não prova que `_LOCK` ficou
  preso.
- Há, contudo, caminho de contenção global verificável no código: `action()` entra
  em `_LOCK` para localizar/registrar estado; `recover` executa `_remove`,
  `_spawn` e `_discover` antes de sair dessa seção. Esses caminhos fazem I/O de
  Docker e descoberta MCP, podendo atrasar `/v1/status` e outras leituras globais
  se a operação ficar lenta. `install` também pode chamar `_inspect` dentro da
  seção inicial. Ainda não há evidência de que `recover`/`install` estava em
  execução durante os timeouts reportados.
- `/v1/observe` pode esperar pelo lock **por servidor** enquanto executa inspeção
  e descoberta; esse timeout, isoladamente, é compatível com contenção por
  `tools/call` ou outra operação do mesmo servidor. Não identifica a causa do
  timeout de `/v1/status`.
- `/v1/health` responder rapidamente não exonera as rotas acima: é uma operação
  diferente e não consulta `_STORE`/Docker da mesma forma.
- O source local inspecionado define deadline de 150 s para `tools/call` e
  limpeza/cancelamento terminal limitado a 5 s, mas o image ID/revisão do broker
  efetivamente ativo durante o ensaio não foi reportado. Se esse código e esses
  limites estavam ativos, os 175,12 s sem resposta excedem o envelope nominal;
  isso aumenta a prioridade de verificar drift de imagem/configuração, execução
  fora do caminho MCP esperado ou bloqueio na camada HTTP/handler. Não basta,
  isoladamente, para escolher entre essas hipóteses.

Conclusão provisória: **há evidência de indisponibilidade ampla no caminho do
broker e uma hipótese de contenção global que merece prioridade**, mas não há
base para atribuir o incidente especificamente à chamada de 175 s ou afirmar
que `docker attach` reteve `_LOCK`. Outras possibilidades ainda abertas incluem
uma operação de manager que segura `_LOCK`, saturação/threads presas no processo,
falha do transporte HTTP/proxy, ou timeouts em diferentes camadas. O estado
`transport_uncertain` é por servidor e não explica sozinho os sintomas de
`notes` e `/v1/status`.

### Próximo diagnóstico discriminante

1. Preservar a evidência antes de qualquer restart: recolher stack dump/thread
   dump do processo broker (se disponível), logs do broker/manager e estado dos
   containers sem novas chamadas `research_deep` ou operações de escrita.
2. Correlacionar timestamps e IDs entre o cliente, gateway, broker e containers;
   confirmar se `notes` e Deep Research usam o mesmo broker e se havia uma ação
   `recover`/`install` durante `/v1/status`.
3. Distinguir bloqueio global de bloqueio por servidor: confirmar se `/v1/status`
   fica preso ao adquirir `_LOCK`, enquanto MCP/observe ficam presos em
   `server.lock`; identificar a thread que possui o lock e a pilha que a mantém.
4. Reconciliar, read-only, image IDs e revisões efetivos do broker/gateway/MCP
   contra o inventário reportado. O inventário alegado de seis `update-image` no
   dia (três falhos) é contexto operacional a verificar, não prova causal.
5. Só depois de localizar/registrar o estado bloqueado, decidir por fluxo
   suportado se restart/recovery é necessário. Não executar restart, replay ou
   nova pesquisa como tentativa diagnóstica cega.
6. Após restaurar o transporte e entender a causa, executar um novo E2E único
   autorizado, sem retry: exigir ID real antes de getters/relatório e parar se a
   chamada não o devolver.

**Estado:** nenhuma ação de manager/restart foi executada nesta atualização. A
pesquisa funcional não passou; a causa e a necessidade de recuperação do broker
permanecem pendentes de evidência de runtime.

## Verificação da imagem após reboot — 2026-11-01

Leitura local read-only confirmou que o digest mostrado na captura e em execução
é `sha256:1863c62b1f4a7420c191e315dd1a9fad1d4c9b4de0c762490aa369ee30585196`.
O container `percival-mcp-deep-research` estava `Up 34 minutes`; a imagem tem a
tag `percival-deep-research:3.0.1-4336da9-f2-006494f75dbd`, foi criada em
`2026-11-01 17:30:19 -03:00` e seu OCI label registra source revision
`4336da90821567cfb36ace8b0225654f8f9fdf47` e source diff
`006494f75dbdfd1d687aaa95a1ab422eb3de889fb81dc36c72b3f484aefd2c6f`.

No inventário local, esse digest é o mais novo entre as imagens
`percival-deep-research` disponíveis. Porém, o `main` local e `origin/main` estão
em `5093cab8bcb349177a0789be59875ec0908f999a`, descendente da revisão `4336da9`;
o commit `5093cab` altera código de runtime do worker, cliente e tools de pesquisa.
Assim, **a imagem da captura é a imagem local mais recente e está rodando, mas
não foi construída da revisão mais recente do repositório**. Não verifiquei um
registry remoto nem se existe imagem mais nova fora deste inventário local. Esta
verificação foi somente leitura: não houve build, repin, restart ou chamada de
pesquisa.

### Candidato construído para reteste — 2026-11-01

Após recomendação de testar as mudanças publicadas antes de novo E2E, foi
construída localmente, sem pin/restart/publicação, a revisão limpa `5093cab8`:

- Tag: `percival-deep-research:3.0.1-5093cab`.
- Image ID para pin: `sha256:a6efc34dc869af732e1d5af7df537037b67170821837473c95465e444e505ec5`.
- OCI revision: `5093cab8bcb349177a0789be59875ec0908f999a`; plataforma
  `linux/amd64`; build `worktree=clean`.
- Smoke stdio com `--network=none`, configuração fictícia
  `INFERENCE_API_KEY=fixture-not-a-secret`, UID 1000: `initialize` e `tools/list`
  passaram; foram listadas as 5 tools esperadas. A primeira tentativa sem env
  falhou antes do handshake porque o servidor exige configuração de inference
  no startup; não foi usada credencial real nem feita chamada a provider.
- Após o build, `percival-mcp-deep-research` continuava executando o ID antigo
  `1863c62b…`; nenhum manager action/pin foi realizado. O E2E `research_deep`
  com o novo candidato e validação dos getters/relatório ainda está pendente.

O digest acima é o novo candidato local baseado no `main` publicado, adequado
para o owner pinar para o ensaio controlado. O smoke comprova somente o contrato
stdio de startup/listagem; não comprova acesso ao retriever, inference nem o
pipeline de pesquisa profunda.

### Pin do candidato confirmado visualmente pelo owner — 2026-11-01

As capturas fornecidas pelo owner mostram o estado anterior em
`sha256:1863c62b…` e, após `update-image`, o candidato
`sha256:a6efc34dc869af732e1d5af7df537037b67170821837473c95465e444e505ec5`.
Na captura posterior, o histórico mostra `update-image · committed` às 19:23:13
e o cartão informa Docker `running`, MCP `connected`, gateway intent `running`,
tool activation `yes` e cinco tools observadas. Isso sustenta que o pin foi
aceito e o servidor está conectado/listável na UI. As capturas são evidência
fornecida pelo owner; não houve leitura independente do runtime nesta sessão.

O estado conectado e as cinco tools observadas não comprovam a execução de
`research_deep`. O teste E2E real de pesquisa, com a regra de chamada única/sem
retry e getters/relatório somente se houver um `research_id` real, continua
pendente.

## Follow-up reportado pelo owner — 2026-11-01

O owner informa que o servidor MCP `deep-research` ainda não está funcionando
corretamente e referencia um resultado de testes do agente Percival. O campo
com esse resultado foi recebido vazio (`""`). Portanto, este follow-up confirma
uma nova observação operacional do owner, mas não fornece uma reprodução técnica
do sintoma.

Não estão disponíveis para este ensaio: nome da tool chamada, argumentos
sanitizados, erro/resposta MCP, duração até a falha, horário/correlation ID,
`research_id`, logs correlacionados, imagem efetivamente usada nem deadlines
efetivos do cliente, gateway, broker e servidor. Não é possível concluir se a
falha atual é a repetição do timeout anterior de 30 s, uma configuração não
aplicada, um timeout em outra camada ou um erro interno/provedor durante a
pesquisa. Essas são hipóteses a discriminar, não causas confirmadas.

### Diagnóstico necessário no próximo ensaio

1. Antes da chamada, registrar em modo read-only os image IDs/revisões ativos
   do gateway, broker e Deep Research, o transporte e os limites efetivos de
   cada camada. Registrar nomes/valores de configuração não sensíveis; nunca
   incluir API keys, conteúdo privado ou argumentos que exponham segredos.
2. Fazer uma única chamada controlada de `research_deep`, sem retry automático,
   anotando timestamp, duração, tool, argumento de pesquisa sanitizado e corpo
   completo da resposta MCP ou erro. Correlacionar com logs do gateway, broker,
   servidor e worker pelo mesmo intervalo/ID de requisição.
3. Se a resposta contiver um `research_id` real, usar exatamente esse ID em
   `research_get_context` e `research_get_sources`, e então em
   `research_write_report`; registrar corpos e resultados. Não usar ID sintético.
4. Se a chamada expirar ou falhar sem ID real, parar o fluxo: não repetir a
   pesquisa nem acionar `research://{topic}` como tentativa de recuperação, pois
   isso pode iniciar trabalho novo. Inspecionar o estado/logs do worker e
   localizar a camada que encerrou a chamada antes de outro ensaio.
5. Vincular a conclusão ao image ID e à configuração efetivamente observados;
   sucesso de handshake, listagem de tools ou busca rápida não comprova o
   pipeline de pesquisa profunda.

Até que essa evidência seja anexada, manter severidade proposta alta e a issue
aberta; não atribuir a falha à imagem atual nem declarar o timeout corrigido.

## Investigação após a atualização do pin — 2026-11-01

### Estado do gesto de pinagem

As capturas do owner mostram o aviso da WebUI “Operation accepted, but the
current state could not be verified. Refresh before another mutation.” O aviso
indica falha de verificação pós-mutação, não prova rollback nem sucesso. A
reconciliação read-only seguinte encontrou:

- Config Percival: revisão global `33`, servidor `deep-research` revisão `5`,
  `active=true`, `state=running`, origem
  `sha256:e857dc0fb8d940dcad2044d0bad19e60c3b920e953d4121ee966ca275eafc7d5`.
- Journal de transição `update-image`: estado `committed`, revisão `33`; o
  backup pre-update foi criado pelo gestor.
- Container Percival ativo: mesmo image ID, running, revisão `4336da9`.
- Log do gateway: hot reload completou com 10 capacidades conectadas.
- Core aplicado depois: gateway `sha256:378c0369…` e broker
  `sha256:a12eb844…`, ambos healthy; `nanobot mcp-docker doctor` passou.

Conclusão: a mutação foi confirmada, apesar do aviso de estado pós-mutação.
Não repetir pin às cegas; a fonte de verdade é a configuração/journal do gestor,
confirmada contra o container.

### Reprodução funcional real

Pelo `MCPProvider` do gateway atualizado e sem retry, foi feita uma única
chamada com consulta pública à documentação oficial de Python sobre
cancelamento de tasks asyncio. O cliente recebeu erro MCP (`is_error=true`),
sem `research_id`:

```text
Error: Research exceeded the 90s internal limit
(correlation_id=crl-2c0518ad).
```

O log de worker correlacionado estabelece que a execução começou às
`2026-11-01T20:19:58.016Z`, terminou exatamente após 90 s e tinha
`last_stage=search`, com processo filho reaped. Não há `Research complete` nem
ID real; getters/relatório não foram chamados. Essa foi a única pesquisa real
desta campanha até este ponto; nenhum retry foi executado.

### Causa técnica encontrada e correção

Config ativa confirmada no MCP: `RETRIEVER=duckduckgo`. O retriever upstream
`gpt_researcher.retrievers.duckduckgo.Duckduckgo.search` instancia `DDGS()` sem
opções e chama `text()` sem `backend`. Em `ddgs` 9.x, isso seleciona `auto`:
vários motores únicos concorrem em batches com waits; futures ainda pendentes
são aguardadas pelo fechamento do `ThreadPoolExecutor`. O timeout de rede
individual de 5 s, portanto, não limita por si só a duração total desta busca.
O worker não conseguiu sair da fase de busca antes do limite rígido de 90 s.
O request real confirma a falha no limite, e a rota automática sem backend
fixo é verificável na dependência instalada; o log não discrimina qual motor
ou subconsulta específica ficou pendente.

Correção local: `percival_research/retrievers/bounded_duckduckgo.py` substitui
somente a classe DuckDuckGo do `GPTResearcher` por um adaptador próprio que
usa `DDGS(timeout=5)` e o único backend `duckduckgo`, sem fan-out/fallback.
A resposta mantém a normalização `{href, body, title}` e aceita apenas URLs
HTTP(S). Marcadores de etapa/resultados do retriever são content-free. O
adaptador é instalado no worker isolado e na ferramenta `research_quick_search`;
continua aplicada a regra de isolamento do processo e cleanup do worker.

### Evidência da candidata

- Nova imagem local: `percival-deep-research:3.0.1-4336da9-f2-006494f75dbd`,
  image ID/RepoDigest
  `sha256:1863c62b1f4a7420c191e315dd1a9fad1d4c9b4de0c762490aa369ee30585196`,
  source revision `4336da90821567cfb36ace8b0225654f8f9fdf47`, diff SHA-256
  `006494f75dbdfd1d687aaa95a1ab422eb3de889fb81dc36c72b3f484aefd2c6f`.
- `uv run --no-sync pytest -q`: **443 passed, 3 skipped, cobertura 88,65%**.
  Ruff check e format check passaram.
- Regressões focadas: seleção real da classe upstream `Duckduckgo` substituída
  por `BoundedDuckduckgo`; adapter passa `timeout=5` e `backend="duckduckgo"`,
  normaliza links/snippets e propaga timeout sem segundo backend. A suíte não
  consulta a rede externa.
- Probe cross-repo com gateway/broker reais e provedor fixture local, imagem
  `1863c62b…`: **success** completou em 48,113 s com 2 completions fixture,
  getters, relatório e cache no mesmo fluxo/ID; **timeout** 3,077 s, erro MCP
  interno e nenhum worker remanescente; **cancel** 14,435 s, nenhum worker
  remanescente e chamada de verificação posterior passou. Os três modos
  registaram 0 chamadas de embeddings do worker.
- Conformance stdio da imagem: initialize + `tools/list` (5 tools) passou;
  UID 1000 preservado.
- Probe cross-repo usou `RETRIEVER=searx` ligado a fixture local; portanto
  valida o MCP/worker, os timeouts e o pipeline ponta-a-ponta sem credenciais,
  mas não simula resposta real da rede DuckDuckGo. O caminho DDG é coberto pelas
  regressões determinísticas de seleção/backend; a chamada real após pin é o
  gate que ainda falta para validar disponibilidade do upstream nesse ambiente.
- Trivy 0.76.1, DB local `2026-11-01T13:02:34Z`: **0 findings** na nova
  imagem Deep Research. Gateway manteve 397 findings (4 Critical, 80 High),
  broker 177 (46 High), idênticos aos image IDs ativos anteriores, sem novos
  IDs/pacotes/severidades na comparação. Esses findings core seguem sem
  adjudicação e não são gate para instalar localmente a candidata, mas nenhum
  core image foi publicado.

### Pendências de aceite

1. A pinagem foi realizada manualmente pelo operador; inventário read-only em
   2026-11-02 confirmou configuração e container no image ID
   `sha256:1863c62b1f4a7420c191e315dd1a9fad1d4c9b4de0c762490aa369ee30585196`.
2. Investigar o erro persistente da WebUI de status; não interpretar `MCP
   connected` isoladamente como prova da pesquisa funcional.
3. Executar uma única nova pesquisa real autorizada, sem retry. Se vier ID
   válido, getters, relatório e cache com esse ID; registrar também os novos
   marcadores de busca do worker. Se não vier ID, parar e usar `last_stage` e
   o resultado do backend para discriminar; não repetir antes de fechar o
   diagnóstico da camada.

A issue permanece aberta. A sonda local valida o pipeline MCP/worker; somente a
nova chamada real com a candidata instalada pode comprovar o acesso efetivo ao
retriever DDG no ambiente Percival.

## Problema observado

### Investigação da latência da lista Docker MCP — 2026-11-02

O follow-up no broker de `/home/bill/Projects/nanobot` adiciona uma observação
read-only por servidor com TTL de 10 s, compartilhada entre polls concorrentes
sob o lock do servidor e invalidada antes de qualquer ação gerenciada. Foi
adicionado teste com quatro observações simultâneas: uma descoberta é executada,
os quatro callers recebem estado conectado e snapshots retornados não permitem
mutar o cache.

Validação local executada em ambiente temporário, sem alterar o `.venv` do
checkout: `pytest -q tests/mcp_docker` passou (**127 passed**, 5 warnings de
serialização Pydantic preexistentes); regressões de ciclo de vida passaram
(**4 passed**); `basedpyright nanobot/mcp_docker` passou (0 errors, warnings ou
notes); `ruff check` e `git diff --check` passaram. `ruff format --check` não
passou porque o formatter instalado propõe reformatar extensivamente o arquivo
inteiro `broker.py` e o teste; nenhuma reformatagem foi aplicada.

Isso prova a deduplicação no broker sob concorrência simulada, não o tempo do
endpoint WebUI em runtime. A imagem foi instalada e a medição autenticada de
`/api/settings/mcp-docker/list` com polls concorrentes continua pendente. A
pinagem Deep Research e o ensaio funcional real também continuam pendentes.

### Gateway e broker candidatos instalados para validação — 2026-11-02

Por solicitação explícita do operador, foram construídas imagens locais
`linux/amd64` da revisão `093da161b443c7cf756cf13f29633967baf62c09`, com o
diff atual do worktree identificado por SHA-256
`3bc42dbc3d4a27211b87b2ef5f0ae0ebf29475c12d7e3d148a121953b3313f9c`:

- Gateway: tag `percival-gateway:0.1.0-093da16-f2-3bc42dbc3d4a`, image ID
  `sha256:d96a060e2c24b53a5765323ae4df142d89a2823e47ca23b3d764af92054fb9fa`.
- Broker: tag `percival-mcp-broker:0.1.0-093da16-f2-3bc42dbc3d4a`, image ID
  `sha256:eb5ce9ef51ed9117fc0b2efe262dc8acbbd85eeff03ff3ff7bef6f437783bb81`.

Ambos foram aplicados pelo Compose dono do core, sem build/pull durante a
recriação. A leitura read-only posterior confirmou os dois IDs nos containers;
gateway health respondeu HTTP 200 e broker reportou `running/healthy`. O
container e a referência configurada do servidor `deep-research` continuam em
`sha256:e857dc0fb8d940dcad2044d0bad19e60c3b920e953d4121ee966ca275eafc7d5`;
nenhum pin ou configuração MCP foi alterado. Estes checks de processo/health
não equivalem a `initialize`/`tools/list`, medição autenticada da rota WebUI ou
ensaio de `research_deep`.

Após o operador realizar a pinagem de Deep Research, novo inventário read-only
em 2026-11-02 confirmou o container `percival-mcp-deep-research` e a referência
configurada em `sha256:1863c62b1f4a7420c191e315dd1a9fad1d4c9b4de0c762490aa369ee30585196`
(revisão `4336da90821567cfb36ace8b0225654f8f9fdf47`, diff
`006494f75dbdfd1d687aaa95a1ab422eb3de889fb81dc36c72b3f484aefd2c6f`). O mesmo
inventário confirmou que os containers ativos continuam usando exatamente os
candidatos gateway `sha256:d96a060e2c24b53a5765323ae4df142d89a2823e47ca23b3d764af92054fb9fa`
e broker
`sha256:eb5ce9ef51ed9117fc0b2efe262dc8acbbd85eeff03ff3ff7bef6f437783bb81`;
ambos são revisão `093da161b443c7cf756cf13f29633967baf62c09`, diff
`3bc42dbc3d4a27211b87b2ef5f0ae0ebf29475c12d7e3d148a121953b3313f9c`, em
estado `running/healthy`. As três referências foram reconciliadas contra os
containers e coincidem com os candidatos locais.

Nas capturas fornecidas pelo operador, a WebUI ainda mostra “Could not load
Docker MCP status”/“Data outdated; refresh failed”, embora a imagem
Deep Research no cartão permaneça `e857dc0f…` (estado visual possivelmente
desatualizado). A captura de logs mostra três respostas HTTP 200 para
`/api/settings/mcp-docker/list` com duração de 6.583, 5.439 e 4.997 ms; há
alerta de latência, mas essas linhas não mostram falha HTTP. A medição autenticada
do endpoint após a atualização atual e a causa do estado de erro na UI ainda
precisam ser discriminadas. O operador reporta que o erro persiste após a
pinagem; a pesquisa real sem retry permanece por executar.

### Campanha de correção autorizada — 2026-11-01

Bill autorizou implementar o plano e um ensaio real no Percival de teste com as
credenciais já configuradas: uma pesquisa pública restrita, sem retry automático,
seguida de getters/relatório se houver ID válido. Não autoriza publicação.

Inspeção read-only recuperou uma resposta JSON-RPC emitida pela imagem `feecce7c…`
em `2026-11-01T18:56:00.327925898Z`, request ID `5`, `isError:false`:

```text
Error: Research exceeded the 90s internal limit (correlation_id=crl-0455f2c1). Try a more specific query or increase PERCIVAL_RESEARCH_TIMEOUT_S.
```

Isso comprova um timeout interno posterior ao episódio de 30 s, não a etapa que
consumiu o orçamento nem a entrega dessa resposta ao operador. O worker não aplica
o compressor patch aplicado pelo processo servidor; a contribuição desse defeito
ao timeout ainda precisa de reprodução. O pai só limpa o worker em TimeoutError;
cancelamento externo, dedup Futures e replay de chamadas após perda de transporte
também precisam de regressões. A geração de relatório não tem deadline interno.

Plano executável (evidência final será registrada aqui, sem duplicar trackers):

1. Regressões para inicialização do filho, erro MCP, cancelamento, dedup e replay.
2. Corrigir inicialização/protocolo/cleanup do worker; diagnóstico sanitizado;
   preservar hardening e recusar sucesso vazio. Isolar e limitar relatório.
3. Corrigir retry ambíguo, cancelamento e deadline desde admissão no broker;
   correlacionar IDs e evitar contaminação da próxima chamada.
4. Suíte canônica Deep Research (cobertura >=70%), Ruff/format check; testes
   Percival afetados, Ruff/BasedPyright e integração determinística real.
5. Builds locais por identidade, probes/scan, rollback e atualização pelo owner
   correto; nenhum hand-edit de estado gerenciado.
6. Uma pesquisa real autorizada, getters/relatório/cache com mesmo ID; fechar
   somente com evidência completa para as imagens testadas.

Estado da campanha: implementação iniciada; os itens acima ainda não são resultados.

No ensaio integrado pelo agente Percival, `research_deep` terminou com a mensagem
do cliente MCP:

```text
(MCP tool call timed out after 30s)
```

Não houve corpo MCP nem `research_id`. Por isso não foi possível confirmar a
conclusão da pesquisa, recuperar contexto/fontes com um ID válido ou gerar o
relatório. O agente reportou que `research_quick_search` funcionou em duas
chamadas e retornou zero resultados em uma terceira; isso valida apenas o caminho
de busca rápida, não o pipeline de síntese profunda.

Chamadas posteriores a `research_get_context` e `research_get_sources` usaram um
ID sintético e receberam `Research ID not found or expired`; essas respostas não
validam o caminho com uma sessão de pesquisa real. `research_write_report` não
foi executada por falta de ID válido.

## Diagnóstico confirmado

- Percival cria a configuração MCP para servidores gerenciados em
  `nanobot/agent/tools/mcp.py`; sem override, `MCPServerConfig` aplica o padrão
  `tool_timeout=30` segundos definido em `nanobot/config/schema.py`.
- O gateway ativo também usa `httpx.Timeout(30.0, connect=10.0)` para
  Streamable HTTP. O broker ativo (`percival-mcp-broker:0.1.0-1fa2813`) espera
  apenas 18 s por resposta stdio.
- O código Deep Research define `PERCIVAL_RESEARCH_TIMEOUT_S=90` segundos como
  timeout interno padrão em `config.py`; a configuração efetiva no container
  durante o ensaio não foi lida.
- O prompt do servidor descreve pesquisa profunda de 30–120 s. O relatório do
  owner confirma que o cliente cortou aos 30 s sem resposta nem ID. A pinagem só
  da imagem MCP não altera os limites do gateway e broker; por isso o ensaio após
  pinagem de `b44a…` continuou a falhar. O estado final do worker não foi
  observado; o broker não expõe `/metrics`/`/health` nesse caminho.
- O probe local anterior configurou deliberadamente timeout interno de 2 segundos;
  ele valida o caminho de timeout do servidor, mas não o limite observado pelo
  agente Percival.

## Impacto

O agente está conectado e as tools são listadas, mas a funcionalidade central de
pesquisa profunda permanece não comprovada. Sem `research_id`, as tools de leitura
da sessão e a geração de relatório não puderam ser testadas de ponta a ponta.

## Correção multicamada preparada nos candidatos

- Gateway: `DEEP_RESEARCH_TOOL_TIMEOUT_SECONDS=180` exclusivamente para o MCP
  `deep-research`; os demais MCPs preservam 30 s. HTTPX recebe 190 s, evitando
  que o timeout de leitura fique abaixo do timeout do wrapper.
- Broker: `tools/call` e `resources/read` têm deadline total de 150 s incluindo
  attach/handshake; os métodos curtos preservam 18 s. Assim, o limite do broker
  cobre a duração reportada pelo servidor (até 120 s), sem deixar a chamada sem
  deadline.
- Broker descobre/pagina `resources/templates/list` e encaminha `resources/read`
  apenas para URI estática descoberta ou URI que corresponda a template simples
  anunciado. O gateway registra cada template como tool read-only derivada.
- `research://{topic}` pode iniciar pesquisa se o cache não tiver o tópico. No
  reteste, não usar como retry após timeout; após sucesso, usar `research_id`
  real para getters/relatório e só ler o template para tópico já em cache.
- O teste anterior usou gateway e broker antigos, pois somente a imagem MCP
  Deep Research foi pinada. Por ordem posterior do owner, os dois serviços core
  agora foram atualizados em Compose para os candidatos abaixo; nenhuma chamada
  de pesquisa foi executada durante esta atualização.

## Evidência dos candidatos locais — follow-up 2026-11-01

- Deep Research: `percival-deep-research:3.0.1-09c3903-f2-8e267db4bd7f`, image
  ID `sha256:feecce7c7575da94a6673cbb30440ee17a74164999c35086641f7096ce305629`,
  revisão-base `09c3903944ae52584c350647f4900b78fc0ea262`, diff SHA-256
  `8e267db4bd7f914a6d4060a52af085f17bad9ac23228b3fc2bfc14ff8f3bde79`.
- Gateway Percival ativo: `percival-gateway:0.1.0-26cad20-f2-7de42eb44f4e`,
  image ID `sha256:ba98f612aabbfe0c2a7d9454a55ace2e2f01827a6f713eac1bc2eb285d115b79`.
- Broker Percival ativo: `percival-mcp-broker:0.1.0-26cad20-f2-7de42eb44f4e`,
  image ID `sha256:5f449a092238634323ea735937e6ea0cec85b81f8a38318cbf9eb7599b7ddf0f`.
  Gateway/broker source revision base `26cad20fab23931f537028148f54e27cfbc4c60a`,
  diff SHA-256 `7de42eb44f4e7677331f9119d49625e184f0e274616b221b63e6430846be80a`.
- Testes locais após o refinamento de leitura bounded: **272 passed** nos testes
  de MCP/broker/template/timeout; Ruff nos arquivos alterados passou; BasedPyright
  dos módulos gateway/broker passou com 0 errors/warnings. Suíte Nanobot completa
  antes desse refinamento: **8.795 passed, 61 skipped, 7 failed** no ambiente de
  QA (seis por dependências opcionais ausentes; uma
  falha de read timeout no teste remoto passou isolada). Deep Research passou
  conformance stdio (5 tools, UID 1000) e timeout probe sintético de 2 s
  (`2.257 s`, erro explícito, exit 0).
- Trivy 0.76.1 vulnerability scan, DB `2026-11-01T13:02:34Z`: Deep Research
  teve **0 vulnerability findings**.
  Gateway candidato teve mesmos 397 findings brutos da imagem ativa (4 Critical,
  80 High, 127 Medium, 172 Low, 14 Unknown); broker teve os mesmos 177 da imagem
  ativa (46 High, 62 Medium, 61 Low, 8 Unknown). Nenhum identificador/pacote/
  versão/severidade foi adicionado ou removido; os findings não foram
  adjudicados nem recebem VEX implícito.
- Atualização Compose executada após a confirmação do owner: gateway ativo agora
  é `sha256:ba98f612aabbfe0c2a7d9454a55ace2e2f01827a6f713eac1bc2eb285d115b79`
  (revision `26cad20`, diff `7de42eb44f4e…`); broker ativo é
  `sha256:5f449a092238634323ea735937e6ea0cec85b81f8a38318cbf9eb7599b7ddf0f`
  (mesma revision/diff). Ambos aparecem `healthy` em `docker ps`/inspect e a
  configuração Compose resolve exatamente para essas tags. Rollback permanece
  disponível: IDs antigos continuam locais e a configuração Compose anterior
  permanece no override AgentMail já ativo. A configuração aplicada também usa
  `/home/bill/.positronic/runtime/tmp/opencode/percival-timeout-fix.override.yml`;
  para rollback, reexecutar os mesmos Compose files sem esse override, voltando
  aos tags gateway `e4630dc` e broker `1fa2813`.
- Smoke MCP read-only, executado pelo gateway atualizado contra Deep Research
  atualmente pinado em `b44a…`: handshake/`tools/list` conectaram; os cinco tools
  e quatro prompts foram registrados; `resources/templates/list` produziu um
  wrapper read-only `research://{topic}` no registro do agente (10 capacidades
  registradas ao todo). Inspeção read-only registrou timeout efetivo de 180 s
  para `research_deep` e para o wrapper template. Não houve `tools/call`,
  `resources/read` ou provider call.

## Critérios de aceite

- Limites efetivos do cliente e do servidor registrados sem conteúdo de segredos.
- HTTPX, broker e wrapper têm limites ordenados acima do limite efetivo do servidor.
- `resources/templates/list` lista o template anunciado e um `resources/read`
  correspondente passa; URI não anunciada é recusada antes do upstream.
- A chamada de pesquisa profunda retorna resposta MCP completa com `research_id`
  válido antes do timeout do cliente.
- Contexto e fontes são recuperados para o ID real; o relatório é gerado para a
  mesma sessão e inclui fontes identificáveis e limitações.
- O timeout/cancelamento não deixa worker órfão nem causa repetição silenciosa da
  pesquisa.
- O resultado é registrado para o image ID testado; nenhuma conclusão é estendida
  a outra imagem ou revisão.

## Limites e itens relacionados

- Gateway/broker foram atualizados via Compose e o owner pinou manualmente
  `sha256:feecce7c7575da94a6673cbb30440ee17a74164999c35086641f7096ce305629`
  pela UI; `docker ps` read-only confirma o MCP em execução. Nenhum valor de
  env/credencial, mount ou perfil de segurança foi alterado por essa atualização.
- **Pendência para fechar:** executar uma chamada `research_deep` sem retry. O
  aceite exige validar o corpo (não apenas HTTP
  `200`/`isError:false`), capturar um `research_id` real e usar esse mesmo ID
  para getters e relatório.
- O gateway ainda reporta findings Trivy não adjudicados, embora o conjunto seja
  idêntico ao da imagem ativa; sem promoção/publicação até triagem/VEX do owner.
- O relatório do owner também observa plaintext `INFERENCE_API_KEY` no config,
  `allowRemoteAdmin:true` e mounts host RW amplos. Nenhum segredo foi copiado e
  nenhuma configuração foi alterada; aplicar o perfil restrito é pendência A-009
  separada.
- A configuração de runtime observada no manager ainda indica **Full host access**;
  esta issue não altera nem aprova esse perfil. A reconciliação do perfil restrito
  continua acompanhada por A-009 no plano S2-DR.
