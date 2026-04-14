#!/usr/bin/env python3
"""Lê o CSV de progresso e gera o relatório HTML (abas GoKursos / Instituto Exito)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from components import analisar, escrever_html_abas, imprimir_console  # noqa: E402

BASE_DIR = ROOT
GOKURSOS_DIR = Path(__file__).resolve().parent
EXITO_DIR = BASE_DIR / "Exito"

CSV_PATH_GOKURSOS = GOKURSOS_DIR / "progress_130426162242.csv"
CSV_PATH_INSTITUTO_EXITO = EXITO_DIR / "progress_instituto_exito.csv"
HTML_PATH = BASE_DIR / "index.html"
GEOJSON_UFS_PATH = GOKURSOS_DIR / "br_ibge_uf.json"


def main() -> None:
    r_gok = analisar(CSV_PATH_GOKURSOS)
    imprimir_console(r_gok)
    r_ie = (
        analisar(CSV_PATH_INSTITUTO_EXITO)
        if CSV_PATH_INSTITUTO_EXITO.exists()
        else None
    )
    escrever_html_abas(
        [
            ("gokursos", "GoKursos", r_gok, CSV_PATH_GOKURSOS),
            ("instituto-exito", "Instituto Exito", r_ie, CSV_PATH_INSTITUTO_EXITO),
        ],
        HTML_PATH,
        geojson_ufs_path=GEOJSON_UFS_PATH,
    )
    print()
    print(f"Relatório HTML salvo em: {HTML_PATH}")


if __name__ == "__main__":
    main()
