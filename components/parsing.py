"""Parsing de campos do CSV (progresso, datas, DDD)."""

from __future__ import annotations

from datetime import datetime


def parse_progresso(raw: str | None) -> float | None:
    s = (raw or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_data_hora_br(raw: str | None) -> datetime | None:
    s = (raw or "").strip()
    if not s:
        return None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def faixa_dez_porcento(progresso: float) -> int:
    if progresso >= 100:
        return 100
    return int(progresso // 10) * 10


def extrair_ddd(telefone: str | None) -> str | None:
    if not telefone:
        return None
    d = "".join(c for c in telefone if c.isdigit())
    if not d:
        return None
    if d.startswith("55") and len(d) >= 12:
        d = d[2:]
    if len(d) >= 10:
        return d[:2]
    return None
