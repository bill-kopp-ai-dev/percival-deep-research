# Plano de correção da batelada das tools do Deep Research

- **Data:** 2026-11-14
- **Status:** E0 finalizada com diagnóstico inconclusivo e gate G1 ativo; E1 concluída; E2/E3 bloqueadas
- **Issue de origem:** [`docs/issues/2026-11-14-tools-batch-deep-research.md`](../issues/2026-11-14-tools-batch-deep-research.md)
- **Owner e único aprovador:** Bill Kopp
- **Runtime observado:** Positronic `deep-research` 3.0.1, imagem `sha256:55e0cec23cf185fd753e2023d7f608eb381107d97458eb4294a7c68d9dec8990`, instalação revisão 23, configuração revisão 1
- **Escopo previsto:** diagnóstico, alterações locais, testes e candidato local; rollout de teste pelo manager Positronic somente quando essa etapa for expressamente solicitada
- **Evidência da execução E0–E3:** [seção de execução da issue](../issues/2026-11-14-tools-batch-deep-research.md#execução-de-e0e3-em-2026-11-14)
- **Fora de escopo:** publicação, alteração do manager Percival, mudança de provider/credencial, aumento de timeouts, persistência de sessões e alteração da semântica de `source_urls`

## 1. Resultado pretendido

Encerrar os dois achados sem mascarar a falha intermitente nem enfraquecer o
isolamento de processo e o hardening existentes:

1. **DR-BATCH-01:** identificar pela evidência de runtime a causa das falhas
   genéricas de `research_deep`, reproduzi-la em teste e aplicar a menor correção
   que elimine esse mecanismo. Falhas transitórias legítimas de dependências devem
   permanecer erro sanitizado; não se promete disponibilidade permanente de
   busca, scraping ou inferência externos.
2. **DR-BATCH-02:** toda resposta de `research_quick_search` que contenha
   resultados web deve começar com `UNTRUSTED_CONTENT_HEADER`, preservando
   `result_count`, ordem e conteúdo dos resultados. Erros locais continuam
   começando com `Error:` e não recebem envelope de conteúdo externo.

A issue só poderá ser integralmente encerrada quando ambos os achados tiverem
critérios verificáveis atendidos. Uma correção de DR-BATCH-02 pode ser concluída
de forma independente se a causa de DR-BATCH-01 ainda não estiver demonstrada.

## 2. Princípios de execução e decisões já tomadas

- Não alterar `research_deep` por hipótese: primeiro correlacionar os IDs
  `crl-727bc57b` e `crl-1592f22c` aos logs e a um ramo concreto do código.
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
| E0 | Preservar baseline e recuperar evidência dos dois correlation IDs | acesso read-only ao host/manager | tabela de diagnóstico e identidade exata da imagem |
| E1 | Criar regressão e corrigir DR-BATCH-02 | E0 somente para baseline; não depende da causa de DR-BATCH-01 | quick search envelopado e testes verdes |
| E2 | Classificar DR-BATCH-01 e demonstrar a causa em regressão | E0 | teste que falha no código sem correção |
| E3 | Aplicar a correção mínima de DR-BATCH-01 | E2 | regressão e caminhos vizinhos verdes |
| E4 | Executar verificação local integrada | E1; E3 para fechamento integral | suíte, lint/format e diff limpos |
| E5 | Construir e qualificar um candidato rastreável | E4 | image ID, labels e probes pertinentes |
| E6 | Aplicar no Positronic e executar um smoke real controlado | E5 e solicitação explícita de rollout | mesma imagem pinada, fluxo real e rollback preservado |
| E7 | Atualizar issue/plano e encerrar o escopo concluído | critérios E4–E6 conforme o escopo solicitado | registro canônico sem alegações não verificadas |

E1 pode avançar enquanto E0/E2 estiverem bloqueados. E3 não pode avançar sem E2.

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
| `crl-727bc57b` | não recuperado | não recuperado | não recuperado | não recuperada | não — G1 ativo |
| `crl-1592f22c` | não recuperado | não recuperado | não recuperado | não recuperada | não — G1 ativo |

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
raiz identificada. G1 permanece ativo; novas tentativas de diagnóstico dependem de
acesso read-only ao host ou de logs equivalentes dos mesmos eventos.

**Gate G1 — evidência suficiente:** se os logs não identificarem exceção e ramo,
manter DR-BATCH-01 sem patch e registrar a dependência de observabilidade/acesso.
Não “corrigir” apenas a mensagem genérica nem inferir provider/retriever pela
intermitência.

## 5. E1 — Correção determinística de DR-BATCH-02

### 5.1 Regressões antes do patch

Editar `tests/test_tools_quick_search.py` e, somente se necessário para o
contrato MCP, o teste de transporte correspondente:

- [ ] Em `test_quick_search_sucesso`, exigir
  `result.startswith(UNTRUSTED_CONTENT_HEADER)` além das asserções atuais de
  contagem, ordem e resultados. Esse teste deve falhar na implementação atual.
- [ ] Adicionar resultado com `title`, `href` e `body`, sendo `body` um texto de
  injection benigno de fixture. Confirmar que o texto permanece literalmente como
  dado, que o header aparece exatamente uma vez e que nenhuma sanitização remove
  ou executa o snippet.
- [ ] Em `test_quick_search_sem_resultados`, definir e verificar o contrato de
  envelope para a resposta vazia. A opção preferida é envelopar também esse ramo
  para manter todos os retornos normais da tool uniformes.
- [ ] Manter `test_quick_search_rejeita_injection` e
  `test_quick_search_trata_excecao` começando com `Error:`; acrescentar asserção
  de que erros locais não são apresentados como conteúdo web.
- [ ] Confirmar que métricas, acquire/release do limiter e `result_count` não
  mudam.

### 5.2 Implementação mínima

Em `percival_research/tools/quick_search.py:11-16` e `:59-88`:

- [ ] Importar `wrap_untrusted_content` de `utils`.
- [ ] Envolver `"\n".join(lines)` somente no retorno normal de
  `_do_quick_search`, após a conclusão da busca e da formatação.
- [ ] Não envolver o retorno de `handle_exception`, erros de validação ou erro de
  admissão do rate limiter.
- [ ] Aplicar o envelope uma única vez; não adicionar um segundo prefixo em
  camadas MCP, prompts ou clientes.
- [ ] Preservar o schema `(query) -> str`, os nomes das tools e a estrutura
  `result_count`/`[Result N]` já consumida pelos agentes.

### 5.3 Documentação

- [ ] Atualizar a descrição de `research_quick_search` e o security boundary no
  README para declarar que snippets rápidos também usam o prefixo.
- [ ] Não alterar a versão do produto nem o changelog como se a correção já
  estivesse instalada; qualquer bump/release fica fora deste plano.

**Aceite DR-BATCH-02:** as regressões falham sem o patch e passam com ele; saída
normal começa com o header; erro local continua `Error:`; contagem, ordem e
conteúdo dos resultados permanecem intactos.

## 6. E2/E3 — Causa, regressão e correção de DR-BATCH-01

### 6.1 Converter a evidência em teste

- [ ] Selecionar o arquivo de teste da camada onde a exceção ocorreu:
  `tests/test_tools_deep_research.py` para ramos da tool,
  `tests/test_research_lifecycle.py` para sessão/provider/timeout, ou testes do
  worker/retriever para falhas nessas camadas.
- [ ] Reproduzir a assinatura observada com doubles/fixtures, sem rede e sem
  credenciais reais. Incluir o mesmo estágio e o mesmo tipo de payload/exceção;
  não criar um teste genérico que apenas repita `RuntimeError("boom")`.
- [ ] Verificar que a regressão falha no código anterior e que não cria
  `research_id`, não grava sessão parcial e não deixa worker/tarefa pendente.
- [ ] Se a falha original tiver ocorrido após criação parcial da sessão, verificar
  também eviction/cleanup e ausência de cache aparentemente bem-sucedido.

**Gate G2 — regressão válida:** se o teste passa no código sem patch, ele não
reproduz o defeito e não autoriza a correção. Revisar a fixture até demonstrar a
falha ou devolver o item ao diagnóstico.

### 6.2 Escolher a correção pela causa demonstrada

Aplicar somente o ramo correspondente:

| Evidência | Correção permitida | Correção que não deve ser usada |
| --- | --- | --- |
| worker retorna payload inválido/vazio | corrigir serialização/normalização na origem e testar payload realista | remover `validate_research_data` ou aceitar contexto/fontes vazios |
| worker sai não zero em stage específico | tratar a exceção nesse stage, preservando protocolo sanitizado e deadline | aumentar timeout ou esconder exit não zero |
| retriever/scraper produz inconsistência | ajustar o adaptador/parse afetado com fixture representativa | trocar provider/retriever ou adicionar fan-out sem evidência |
| exceção transitória classificável | tratar somente a operação afetada, com limite e sem repetir pesquisa inteira | retry global automático e multiplicação de chamadas pagas |
| reidratação/registry/extração no pai | corrigir o ramo local e garantir eviction em todos os erros | mover o pipeline de volta para o processo principal |
| configuração inválida efetiva | corrigir pelo manager e manter validação/erro explícito | editar estado do manager ou valores secretos manualmente |

- [ ] Implementar a menor alteração no arquivo dono da causa.
- [ ] Manter `ProviderRejectedError`, timeout e cancelamento nas categorias já
  existentes; não transformar erro permanente em transitório.
- [ ] Se a resposta pública precisar de nova categoria segura, incluir apenas
  informação allowlisted, manter `correlation_id` e avaliar o impacto no contrato
  do consumidor. Não expor a mensagem bruta da exceção.
- [ ] Executar a regressão nova e os testes vizinhos do mesmo caminho. Confirmar
  que o sucesso continua produzindo contexto, fontes e URLs válidos e que getters
  e relatório não sofreram regressão.

**Aceite DR-BATCH-01:** causa e ramo documentados; regressão que reproduz a
falha original falha sem patch e passa com ele; não há sessão/cache parcial nem
worker remanescente; o fluxo feliz e os erros permanentes existentes permanecem
cobertos. O encerramento não deve afirmar que toda falha externa futura foi
eliminada.

## 7. E4 — Verificação local integrada

Executar os testes focados durante o desenvolvimento e a suíte canônica uma vez
na revisão final:

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

- [ ] Se houver `uv sync`, executar antes da suíte
  `uv run python scripts/patch_gpt_researcher.py`; não reexecutar patch/sync sem
  mudança de dependências.
- [ ] Registrar totais de testes/skips, cobertura e qualquer skip novo. Skips HTTP
  preexistentes não substituem o smoke real da etapa E6.
- [ ] Revisar o diff para garantir que somente arquivos relacionados às causas,
  testes e documentação foram alterados.
- [ ] Se apenas DR-BATCH-02 tiver sido corrigida, declarar explicitamente que a
  suíte não fecha DR-BATCH-01.

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
- [ ] Se E3 alterar worker, deadline ou cleanup, executar também os probes
  `timeout` e `cancel` aplicáveis; não repeti-los para uma alteração restrita ao
  envelope de quick search.
- [ ] Não publicar a imagem. Scan/SBOM devem ser produzidos quando exigidos pelo
  fluxo gerenciado ou por mudança de dependências/imagem, não como aceite extra
  para código já validado.

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

Smoke controlado, sem retry automático:

1. Chamar `research_quick_search` com uma consulta pública curta e confirmar
   header, contagem e resultados.
2. Chamar uma única `research_deep` com a consulta original da issue e
   `include_context=false`. Registrar image ID, correlation ID em falha ou
   `research_id` em sucesso.
3. Somente se houver ID real, chamar `research_get_context` e
   `research_get_sources` com exatamente esse ID e, depois,
   `research_write_report` uma vez. Confirmar headers, contagem coerente e
   relatório sem `<think>` auxiliar.
4. Não usar `research://{topic}` como recuperação. Após timeout/erro ambíguo de
   transporte, inspecionar o estado original antes de qualquer nova chamada; após
   erro explícito da aplicação, correlacionar logs antes de repetir.
5. Confirmar cleanup/worker reaped quando houver acesso ao host e ausência de
   novos erros genéricos no intervalo do smoke.

Um smoke real bem-sucedido demonstra o caminho executado, não a eliminação de
toda intermitência externa. O fechamento de DR-BATCH-01 depende principalmente da
causa e da regressão de E2/E3.

## 10. E7 — Fechamento documental e rollback

- [ ] Atualizar a issue com causa(s), arquivos alterados, regressões, comandos e
  resultados, SHA/diff, image ID e evidência do smoke. Vincular este plano em vez
  de duplicar toda a narrativa.
- [ ] Marcar DR-BATCH-02 como resolvido somente após seu aceite. Manter
  DR-BATCH-01 aberto se G1/G2 não tiverem sido satisfeitos.
- [ ] Mover a issue para `docs/issues/closed/` somente após os dois achados serem
  atendidos ou por decisão explícita do operador, deixando claros eventuais
  riscos residuais.
- [ ] Mover este plano para `docs/plans/closed/` quando o escopo executado estiver
  reconciliado, sem declarar etapas não realizadas como concluídas.
- [ ] Se o candidato falhar, restaurar pelo manager a imagem baseline ainda
  disponível, usando a revisão atual, e registrar o resultado. Não editar
  registry/config/audit diretamente e não operar o ambiente Percival.

## 11. Riscos e controles

| Risco | Controle |
| --- | --- |
| Patch de DR-BATCH-01 tratar sintoma errado | gates G1/G2 e correção vinculada à stack/stage |
| Envelope duplicado ou aplicado a erro local | wrap somente no retorno normal e testes de prefixo único/`Error:` |
| Vazamento de segredos/conteúdo em logs e issue | somente IDs, estágios, tipos allowlisted e dados públicos de fixture |
| Retry oculto aumentar custo e trabalho órfão | nenhum retry global; uma chamada real controlada; investigação antes de repetir |
| Regressão de timeout/cancelamento | worker isolado preservado e probes específicos somente se essa camada mudar |
| Evidência atribuída à imagem errada | SHA/diff + OCI labels + image ID registrados no candidato e no smoke |
| Sucesso externo circunstancial confundido com correção | regressão determinística obrigatória e limites declarados no fechamento |
