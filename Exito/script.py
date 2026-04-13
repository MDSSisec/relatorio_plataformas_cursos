#!/usr/bin/env python3
"""Atalho para gerar o index compartilhado a partir da estrutura atual."""

from __future__ import annotations

import runpy
from pathlib import Path


SCRIPT_PRINCIPAL = Path(__file__).resolve().parent.parent / "GoKursos" / "script.py"


def main() -> None:
    runpy.run_path(str(SCRIPT_PRINCIPAL), run_name="__main__")


if __name__ == "__main__":
    main()
