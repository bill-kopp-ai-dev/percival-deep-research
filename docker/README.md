# Percival Deep Research — MCP server

Multi-source web research and report generation, exposed as an MCP server.
Optimized for the [Nanobot](https://github.com/HKUDS/nanobot) agent ecosystem
and compatible with [OpenCode](https://github.com/anomalyco/opencode) and the
[Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/).

## What it does

Five tools and one resource cover the full research workflow:

- `research_deep` — multi-source deep research, returns a curated summary
  plus a `research_id` for follow-up reads.
- `research_quick_search` — fast single-query web search.
- `research_get_context` — fetch the full research context for a `research_id`.
- `research_get_sources` — fetch the source list (URLs, titles, snippets).
- `research_write_report` — write a long-form report for a `research_id`.

Plus four prompts (`research_query`, `research_quick_brief`,
`research_synthesis`, `research_health_diagnose`) and the
`research://{topic}` resource.

## Quickstart

```bash
docker run -i --rm \
  -e INFERENCE_API_KEY=<your-key> \
  -e INFERENCE_LLM=openai:gpt-4o-mini \
  mcp/percival-deep-research
```

The container speaks stdio by default, so it can be plugged into any MCP
client (Nanobot, OpenCode, Claude Desktop, Docker MCP gateway).

For HTTP/SSE mode, publish only on loopback unless a separately reviewed
reverse proxy and access controls are in place:

```bash
docker run -d --rm \
  -p 127.0.0.1:8000:8000 \
  -e MCP_TRANSPORT=sse \
  -e MCP_HOST=0.0.0.0 \
  -e INFERENCE_API_KEY=<your-key> \
  -e INFERENCE_LLM=openai:gpt-4o-mini \
  mcp/percival-deep-research
```

The Dockerfile has no transport-agnostic healthcheck. The Compose HTTP
profile checks `GET /health`; responses 200 (`healthy`) and 503 (`degraded`)
both indicate that the HTTP process is serving. Stdio readiness is verified
with MCP `initialize` and `tools/list`, not an HTTP probe.

## Configuration

All configuration is via environment variables. See
[`server.py`](https://github.com/bill-kopp-ai-dev/percival.OS/blob/main/percival-deep-research/server.py)
for the full list. The most common:

| Var | Default | Notes |
|---|---|---|
| `INFERENCE_API_KEY` | (required) | API key for the inference endpoint. |
| `INFERENCE_BASE_URL` | auto-detected | OpenAI-compatible URL. Provider is auto-detected from host. |
| `INFERENCE_LLM` | `openai:gpt-4o-mini` | `provider:model` format. |
| `RETRIEVER` | `duckduckgo` | `duckduckgo` (no key) or `brave` (needs `BRAVE_API_KEY`). |
| `MCP_TRANSPORT` | `stdio` | `stdio`, `sse`, or `streamable-http`. |
| `LOG_LEVEL` | `INFO` | Standard log levels. |

## License

MIT — see
[`LICENSE`](https://github.com/bill-kopp-ai-dev/percival.OS/blob/main/LICENSE).
