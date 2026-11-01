# Deep Research expira no timeout do cliente Percival

- **Status:** candidata Deep Research `1863c62b…` pinada e confirmada em runtime em 2026-11-02; erro da WebUI/status continua reportado; pesquisa real ainda pendente
- **Reportado em:** 2026-11-01
- **Severidade proposta:** alta; `research_deep` é o fluxo principal do produto
- **Imagem testada inicialmente:** `sha256:4fd1d8d01b242cafe57603ac2c04bc12e34843b54f7b4bf72a83802d7eaaa61d`
- **Imagem pinada no follow-up reportado:** `sha256:b44a6a6e4fe9a80e44111c77732be1f2154a0744085ded92ed80de58045413aa`
- **Imagem atual pinada:** `sha256:feecce7c7575da94a6673cbb30440ee17a74164999c35086641f7096ce305629` (container confirmado running)
- **Source revision (OCI label):** `09c3903944ae52584c350647f4900b78fc0ea262`
- **Evidência:** relatório do owner; imagem MCP atual conferida read-only em `docker ps`; limites do gateway/broker confirmados no código das imagens ativas

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
