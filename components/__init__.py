"""Componentes reutilizáveis: análise, HTML e conversão Exito."""

from __future__ import annotations

from components.analytics import analisar
from components.constants import PROGRESSO_COMPLETO
from components.console_report import imprimir_console
from components.exito_xlsx import (
    COLUNAS_DESTINO,
    converter_xlsx_exito_para_csv,
    xlsx_mais_recente,
)
from components.html_document import escrever_html_abas
from components.models import AgregadoPessoa, Relatorio

__all__ = [
    "AgregadoPessoa",
    "COLUNAS_DESTINO",
    "PROGRESSO_COMPLETO",
    "Relatorio",
    "analisar",
    "converter_xlsx_exito_para_csv",
    "escrever_html_abas",
    "imprimir_console",
    "xlsx_mais_recente",
]
