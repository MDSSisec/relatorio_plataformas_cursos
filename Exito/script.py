#!/usr/bin/env python3
"""Converte XLSX da Exito para CSV padrão e gera o relatório HTML."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from components.exito_xlsx import (  # noqa: E402
    converter_xlsx_exito_para_csv,
    xlsx_mais_recente,
)

BASE_DIR = ROOT
EXITO_DIR = Path(__file__).resolve().parent
SCRIPT_PRINCIPAL = BASE_DIR / "GoKursos" / "script.py"
CSV_DESTINO = EXITO_DIR / "progress_instituto_exito.csv"


def main() -> None:
    caminho_xlsx = xlsx_mais_recente(EXITO_DIR)
    converter_xlsx_exito_para_csv(caminho_xlsx, CSV_DESTINO)
    print(f"CSV da Exito gerado em: {CSV_DESTINO}")
    runpy.run_path(str(SCRIPT_PRINCIPAL), run_name="__main__")


if __name__ == "__main__":
    main()
