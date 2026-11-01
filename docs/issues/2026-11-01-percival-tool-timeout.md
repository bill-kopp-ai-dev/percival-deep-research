# Deep Research expira no timeout do cliente Percival

- **Status:** gateway, broker e candidata Deep Research atualizados/pinados no runtime de teste; V-PILOT funcional pendente
- **Reportado em:** 2026-11-01
- **Severidade proposta:** alta; `research_deep` é o fluxo principal do produto
- **Imagem testada inicialmente:** `sha256:4fd1d8d01b242cafe57603ac2c04bc12e34843b54f7b4bf72a83802d7eaaa61d`
- **Imagem pinada no follow-up reportado:** `sha256:b44a6a6e4fe9a80e44111c77732be1f2154a0744085ded92ed80de58045413aa`
- **Imagem atual pinada:** `sha256:feecce7c7575da94a6673cbb30440ee17a74164999c35086641f7096ce305629` (container confirmado running)
- **Source revision (OCI label):** `09c3903944ae52584c350647f4900b78fc0ea262`
- **Evidência:** relatório do owner; imagem MCP atual conferida read-only em `docker ps`; limites do gateway/broker confirmados no código das imagens ativas

## Problema observado

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
