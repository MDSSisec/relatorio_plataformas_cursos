#!/usr/bin/env python3
"""Converte XLSX da Exito para CSV padrão e gera o relatório HTML."""

from __future__ import annotations

import csv
import runpy
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


BASE_DIR = Path(__file__).resolve().parent.parent
EXITO_DIR = Path(__file__).resolve().parent
SCRIPT_PRINCIPAL = BASE_DIR / "GoKursos" / "script.py"
CSV_DESTINO = EXITO_DIR / "progress_instituto_exito.csv"
COLUNAS_DESTINO = [
    "NOME",
    "EMAIL",
    "PROGRESSO",
    "SITUACAO",
    "CARGA_HORARIA",
    "ULTIMO_LOGIN",
    "ULTIMO_REGISTRO_DE_ATIVIDADE",
    "TELEFONE",
]

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _col_index(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha()).upper()
    if not letters:
        return -1
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _normalizar_header(txt: str) -> str:
    return " ".join((txt or "").strip().upper().split())


def _ler_xlsx_primeira_aba(caminho_xlsx: Path) -> list[list[str]]:
    with ZipFile(caminho_xlsx) as zf:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sst_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sst_root.findall("m:si", NS):
                txt = "".join(t.text or "" for t in si.findall(".//m:t", NS))
                shared_strings.append(txt)

        sheet_root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows_xml = sheet_root.findall(".//m:sheetData/m:row", NS)

        rows: list[list[str]] = []
        for row_xml in rows_xml:
            values_by_index: dict[int, str] = {}
            for cell in row_xml.findall("m:c", NS):
                ref = cell.get("r", "")
                idx = _col_index(ref)
                if idx < 0:
                    continue
                v = cell.find("m:v", NS)
                if v is None or v.text is None:
                    values_by_index[idx] = ""
                    continue
                raw = v.text
                if cell.get("t") == "s":
                    if raw.isdigit():
                        i = int(raw)
                        values_by_index[idx] = (
                            shared_strings[i] if 0 <= i < len(shared_strings) else raw
                        )
                    else:
                        values_by_index[idx] = raw
                else:
                    values_by_index[idx] = raw

            if not values_by_index:
                continue
            max_idx = max(values_by_index)
            row_vals = [values_by_index.get(i, "") for i in range(max_idx + 1)]
            rows.append(row_vals)
    return rows


def _parse_pct(raw: str) -> float:
    s = (raw or "").strip().replace("%", "").replace(",", ".")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _converter_xlsx_exito_para_csv(caminho_xlsx: Path, caminho_csv: Path) -> None:
    rows = _ler_xlsx_primeira_aba(caminho_xlsx)
    if not rows:
        raise SystemExit(f"Planilha vazia: {caminho_xlsx}")

    header = rows[0]
    idx = {_normalizar_header(h): i for i, h in enumerate(header)}
    obrig = ["ALUNO", "PROGRESSO", "CURSO", "DATA DE INÍCIO", "DATA DE CONCLUSÃO"]
    faltantes = [c for c in obrig if c not in idx]
    if faltantes:
        raise SystemExit(
            "Planilha da Exito sem colunas esperadas: " + ", ".join(faltantes)
        )

    with caminho_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_DESTINO)
        w.writeheader()

        for row in rows[1:]:
            def g(col: str) -> str:
                i = idx[col]
                return row[i].strip() if i < len(row) and row[i] is not None else ""

            def g_opt(col: str) -> str:
                i = idx.get(col)
                if i is None:
                    return ""
                return row[i].strip() if i < len(row) and row[i] is not None else ""

            nome = g("ALUNO")
            if not nome:
                continue
            progresso_num = _parse_pct(g("PROGRESSO"))
            situacao = "CONCLUIDO" if progresso_num >= 100.0 else "EM_ANDAMENTO"
            data_inicio = g("DATA DE INÍCIO")
            data_conclusao = g("DATA DE CONCLUSÃO")
            ultimo_login = data_conclusao or data_inicio
            ultima_atividade = data_conclusao or data_inicio

            w.writerow(
                {
                    "NOME": nome,
                    "EMAIL": g_opt("E-MAIL"),
                    "PROGRESSO": f"{progresso_num:.2f}".rstrip("0").rstrip("."),
                    "SITUACAO": situacao,
                    "CARGA_HORARIA": g("CURSO"),
                    "ULTIMO_LOGIN": ultimo_login,
                    "ULTIMO_REGISTRO_DE_ATIVIDADE": ultima_atividade,
                    "TELEFONE": "",
                }
            )


def _xlsx_mais_recente() -> Path:
    arquivos = sorted(EXITO_DIR.glob("*.xlsx"), key=lambda p: p.stat().st_mtime)
    if not arquivos:
        raise SystemExit(f"Nenhum .xlsx encontrado em {EXITO_DIR}")
    return arquivos[-1]


def main() -> None:
    caminho_xlsx = _xlsx_mais_recente()
    _converter_xlsx_exito_para_csv(caminho_xlsx, CSV_DESTINO)
    print(f"CSV da Exito gerado em: {CSV_DESTINO}")
    runpy.run_path(str(SCRIPT_PRINCIPAL), run_name="__main__")


if __name__ == "__main__":
    main()
