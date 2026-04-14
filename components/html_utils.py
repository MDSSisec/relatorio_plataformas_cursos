"""Utilitários para geração de HTML e formatação."""

from __future__ import annotations

import html


def esc(texto: str) -> str:
    return html.escape(texto, quote=True)


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")
