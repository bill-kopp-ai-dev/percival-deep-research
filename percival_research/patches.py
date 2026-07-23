"""Monkey-patch isolado para o ContextCompressor do gpt-researcher."""

import inspect

import gpt_researcher.context.compression as comp
from loguru import logger

_PATCHED_ATTR = "async_get_context"
_IS_PATCHED = False


async def _bypass_compressor_completely(
    self, query: str, max_results: int = 5, cost_callback=None
) -> str:
    """Zero-latency override: disables semantic embeddings network requests.

    Robusto contra (audits acumulada):
      - `self.documents = None` (algumas combinações de Retrievers).
      - `metadata = None` em objects LangChain.
      - `page_content = None` em objects LangChain.
      - doc com valor `None` (não deve virar string literal "None" no output).
      - doc sendo `str` pura (evita aspas extras no output).
      - doc sendo `dict` no formato de retriever (BraveSearch/Serper).
..."""
    docs_text = []
    docs = self.documents if self.documents is not None else []
    if not isinstance(docs, (list, tuple)):
        docs = list(docs)
    for i, d in enumerate(docs):
        if i >= max_results * 15:
            break
        # Audit rodada 3: pular None explícito (em vez de virar "None").
        if d is None:
            continue
        # Audit rodada 3: str pura deve entrar como string crua, sem aspas.
        if isinstance(d, str):
            docs_text.append(f"\n{d}\n")
            continue
        if isinstance(d, dict):
            source = d.get("href") or d.get("url", "") or ""
            title = d.get("title", "") or ""
            content = (
                d.get("body")
                or d.get("raw_content")
                or d.get("content")
                or ""
            )
        else:
            meta = getattr(d, "metadata", None) or {}
            source = meta.get("source", "") or ""
            title = meta.get("title", "") or ""
            content = getattr(d, "page_content", None) or str(d)
        docs_text.append(f"Source: {source}\nTitle: {title}\nContent: {content}\n")
    return "\n".join(docs_text)


def apply_compressor_patch() -> bool:
    """Aplica o monkey-patch com guarda.

    Retorna:
        `True` se aplicado (incluindo patches idempotentes), `False` se a
        classe não existe mais ou a assinatura do método mudou.

    Idempotência:
        Re-aplicar não derruba e não duplica side-effects. Útil para
        reloads em testes/imports múltiplos.
    """
    global _IS_PATCHED
    if _IS_PATCHED:
        return True

    try:
        original = comp.ContextCompressor.async_get_context
    except AttributeError as exc:
        logger.warning(f"Compressor patch skipped (ContextCompressor missing): {exc}")
        return False

    expected_params = {"self", "query", "max_results", "cost_callback"}
    try:
        actual_params = set(inspect.signature(original).parameters)
    except (TypeError, ValueError) as exc:
        logger.warning(
            f"Compressor patch skipped (cannot inspect signature): {exc}"
        )
        return False

    if actual_params != expected_params:
        logger.warning(
            "Compressor patch skipped (async_get_context signature changed: "
            f"expected {sorted(expected_params)}, got {sorted(actual_params)})"
        )
        return False

    try:
        comp.ContextCompressor.async_get_context = _bypass_compressor_completely
        _IS_PATCHED = True
        logger.info("Compressor patch applied successfully")
        return True
    except (AttributeError, TypeError) as exc:
        logger.warning(
            f"Compressor patch skipped (incompatible gpt-researcher version): {exc}"
        )
        return False