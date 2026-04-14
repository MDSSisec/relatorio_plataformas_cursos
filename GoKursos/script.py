#!/usr/bin/env python3
"""Lê o CSV de progresso: pessoas únicas por nome, tabelas cruzadas, datas, DDD, relatório HTML."""

from __future__ import annotations

import csv
import html
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
GOKURSOS_DIR = Path(__file__).resolve().parent
EXITO_DIR = BASE_DIR / "Exito"

CSV_PATH_GOKURSOS = GOKURSOS_DIR / "progress_130426162242.csv"
CSV_PATH_INSTITUTO_EXITO = EXITO_DIR / "progress_instituto_exito.csv"
HTML_PATH = BASE_DIR / "index.html"
# Malhas UF IBGE (GeoJSON ~100KB). Fonte: API malhas IBGE — sem uso de Google Maps ou tiles.
GEOJSON_UFS_PATH = GOKURSOS_DIR / "br_ibge_uf.json"

PROGRESSO_COMPLETO = 100.0
DIAS_SEM_CONTATO = (30, 60, 90)

# DDD (Brasil) → UF — agregação para mapa (fonte: divisão usual ANATEL/IBGE).
DDD_PARA_UF: dict[str, str] = {
    "68": "AC",
    "96": "AP",
    "92": "AM",
    "97": "AM",
    "91": "PA",
    "93": "PA",
    "94": "PA",
    "69": "RO",
    "95": "RR",
    "63": "TO",
    "82": "AL",
    "71": "BA",
    "73": "BA",
    "74": "BA",
    "75": "BA",
    "77": "BA",
    "85": "CE",
    "88": "CE",
    "61": "DF",
    "27": "ES",
    "28": "ES",
    "62": "GO",
    "64": "GO",
    "98": "MA",
    "99": "MA",
    "65": "MT",
    "66": "MT",
    "67": "MS",
    "31": "MG",
    "32": "MG",
    "33": "MG",
    "34": "MG",
    "35": "MG",
    "37": "MG",
    "38": "MG",
    "83": "PB",
    "81": "PE",
    "87": "PE",
    "86": "PI",
    "89": "PI",
    "41": "PR",
    "42": "PR",
    "43": "PR",
    "44": "PR",
    "45": "PR",
    "46": "PR",
    "21": "RJ",
    "22": "RJ",
    "24": "RJ",
    "84": "RN",
    "51": "RS",
    "53": "RS",
    "54": "RS",
    "55": "RS",
    "47": "SC",
    "48": "SC",
    "49": "SC",
    "79": "SE",
    "11": "SP",
    "12": "SP",
    "13": "SP",
    "14": "SP",
    "15": "SP",
    "16": "SP",
    "17": "SP",
    "18": "SP",
    "19": "SP",
}

# Código da UF (IBGE) → sigla (malhas oficiais usam codarea).
CODIGO_IBGE_PARA_SIGLA: dict[str, str] = {
    "11": "RO",
    "12": "AC",
    "13": "AM",
    "14": "RR",
    "15": "PA",
    "16": "AP",
    "17": "TO",
    "21": "MA",
    "22": "PI",
    "23": "CE",
    "24": "RN",
    "25": "PB",
    "26": "PE",
    "27": "AL",
    "28": "SE",
    "29": "BA",
    "31": "MG",
    "32": "ES",
    "33": "RJ",
    "35": "SP",
    "41": "PR",
    "42": "SC",
    "43": "RS",
    "50": "MS",
    "51": "MT",
    "52": "GO",
    "53": "DF",
}

_BOX = {
    "tl": "\u2554",
    "tr": "\u2557",
    "bl": "\u255a",
    "br": "\u255d",
    "h": "\u2550",
    "v": "\u2551",
    "lm": "\u2560",
    "rm": "\u2563",
    "x": "\u2566",
    "y": "\u2569",
}


@dataclass
class AgregadoPessoa:
    max_progresso: float = -1.0
    situacao_no_melhor: str = ""
    carga_no_melhor: str = ""
    max_login: datetime | None = None
    max_atividade: datetime | None = None
    teve_login_preenchido: bool = False
    ddd: str | None = None
    email: str = ""
    telefone_contato: str = ""
    ref_progresso_contato: float = -1.0

    def atualizar_melhor_progresso(
        self, progresso: float, situacao: str, carga: str
    ) -> None:
        sit = (situacao or "").strip() or "(vazio)"
        ch = (carga or "").strip() or "(vazio)"
        if progresso > self.max_progresso:
            self.max_progresso = progresso
            self.situacao_no_melhor = sit
            self.carga_no_melhor = ch
        elif progresso == self.max_progresso and sit == "REPROVADO":
            self.situacao_no_melhor = sit
            self.carga_no_melhor = ch

    def normalizar_progresso(self) -> None:
        if self.max_progresso < 0:
            self.max_progresso = 0.0

    def atualizar_contato(
        self, progresso: float | None, email: str | None, telefone: str | None
    ) -> None:
        em = (email or "").strip()
        tel = (telefone or "").strip()
        if progresso is not None and progresso > self.ref_progresso_contato:
            self.ref_progresso_contato = progresso
            self.email = em
            self.telefone_contato = tel
            return
        if not self.email and em:
            self.email = em
        if not self.telefone_contato and tel:
            self.telefone_contato = tel


@dataclass
class Relatorio:
    """Métricas consolidadas para console e HTML."""

    gerado_em: datetime
    arquivo_csv: str
    hoje: date
    total_pessoas: int
    completaram_curso: int
    linhas_sem_nome: int
    por_faixa: Counter[int]
    situacoes: list[str]
    cols_faixa_pct: list[str]
    cols_carga: list[str]
    mat_situacao_faixa: dict[tuple[str, str], int]
    mat_situacao_carga: dict[tuple[str, str], int]
    nunca_logou: int
    logou_sem_progresso: int
    logou_com_progresso: int
    sem_data_contato: int
    parados_dias: list[tuple[int, int]]
    serie_login_mes: list[tuple[str, int]]
    serie_atividade_mes: list[tuple[str, int]]
    ddd_top: list[tuple[str, int]]
    sem_ddd: int
    por_uf: dict[str, int]
    ddd_nao_mapeado: int
    contatos_faixa_80: list[tuple[str, str, str]]
    concluintes_recentes: list[tuple[str, str, str]]


def _parse_progresso(raw: str | None) -> float | None:
    s = (raw or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_data_hora_br(raw: str | None) -> datetime | None:
    s = (raw or "").strip()
    if not s:
        return None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _faixa_dez_porcento(progresso: float) -> int:
    if progresso >= 100:
        return 100
    return int(progresso // 10) * 10


def _extrair_ddd(telefone: str | None) -> str | None:
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


def analisar(caminho_csv: Path) -> Relatorio:
    hoje = date.today()
    por_nome: dict[str, AgregadoPessoa] = defaultdict(AgregadoPessoa)
    linhas_sem_nome = 0

    campos = (
        "NOME",
        "PROGRESSO",
        "SITUACAO",
        "CARGA_HORARIA",
        "ULTIMO_LOGIN",
        "ULTIMO_REGISTRO_DE_ATIVIDADE",
        "TELEFONE",
    )

    with caminho_csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit("CSV inválido.")
        for c in campos:
            if c not in reader.fieldnames:
                raise SystemExit(f"CSV deve conter a coluna {c}.")

        for row in reader:
            nome = (row.get("NOME") or "").strip()
            if not nome:
                linhas_sem_nome += 1
                continue
            agg = por_nome[nome]
            p = _parse_progresso(row.get("PROGRESSO"))
            agg.atualizar_contato(p, row.get("EMAIL"), row.get("TELEFONE"))
            if p is not None:
                agg.atualizar_melhor_progresso(
                    p,
                    row.get("SITUACAO") or "",
                    row.get("CARGA_HORARIA") or "",
                )
            elif not agg.situacao_no_melhor:
                agg.situacao_no_melhor = (
                    (row.get("SITUACAO") or "").strip() or "(vazio)"
                )
                agg.carga_no_melhor = (
                    (row.get("CARGA_HORARIA") or "").strip() or "(vazio)"
                )
            dt_login = _parse_data_hora_br(row.get("ULTIMO_LOGIN"))
            if dt_login and (agg.max_login is None or dt_login > agg.max_login):
                agg.max_login = dt_login
            if (row.get("ULTIMO_LOGIN") or "").strip():
                agg.teve_login_preenchido = True
            dt_at = _parse_data_hora_br(row.get("ULTIMO_REGISTRO_DE_ATIVIDADE"))
            if dt_at and (agg.max_atividade is None or dt_at > agg.max_atividade):
                agg.max_atividade = dt_at
            ddd = _extrair_ddd(row.get("TELEFONE"))
            if ddd and agg.ddd is None:
                agg.ddd = ddd

    for agg in por_nome.values():
        agg.normalizar_progresso()
        if not agg.situacao_no_melhor:
            agg.situacao_no_melhor = "(vazio)"
        if not agg.carga_no_melhor:
            agg.carga_no_melhor = "(vazio)"

    total = len(por_nome)
    completaram = sum(
        1 for a in por_nome.values() if a.max_progresso >= PROGRESSO_COMPLETO
    )

    por_faixa = Counter(
        _faixa_dez_porcento(a.max_progresso) for a in por_nome.values()
    )
    situacoes = sorted({a.situacao_no_melhor for a in por_nome.values()})
    faixas_ord = sorted(por_faixa.keys())
    cargas_ord = sorted(
        {a.carga_no_melhor for a in por_nome.values()},
        key=lambda x: (x == "(vazio)", x),
    )

    mat_sf: dict[tuple[str, str], int] = defaultdict(int)
    mat_sc: dict[tuple[str, str], int] = defaultdict(int)
    for a in por_nome.values():
        f = _faixa_dez_porcento(a.max_progresso)
        mat_sf[(a.situacao_no_melhor, f"{f}%")] += 1
        mat_sc[(a.situacao_no_melhor, a.carga_no_melhor)] += 1

    cols_f = [f"{f}%" for f in faixas_ord]
    mat_sf_f = {(s, c): mat_sf[(s, c)] for s in situacoes for c in cols_f}
    mat_sc_f = {(s, c): mat_sc[(s, c)] for s in situacoes for c in cargas_ord}

    nunca_logou = sum(1 for a in por_nome.values() if not a.teve_login_preenchido)
    logou_sem_progresso = sum(
        1
        for a in por_nome.values()
        if a.teve_login_preenchido and a.max_progresso <= 0.0
    )
    logou_com_progresso = sum(
        1
        for a in por_nome.values()
        if a.teve_login_preenchido and a.max_progresso > 0.0
    )

    contato_mes_login: Counter[str] = Counter()
    contato_mes_ativ: Counter[str] = Counter()
    sem_data_contato = 0
    for a in por_nome.values():
        datas = [d for d in (a.max_login, a.max_atividade) if d is not None]
        if not datas:
            sem_data_contato += 1
        if a.max_login is not None:
            contato_mes_login[a.max_login.strftime("%Y-%m")] += 1
        if a.max_atividade is not None:
            contato_mes_ativ[a.max_atividade.strftime("%Y-%m")] += 1

    parados: list[tuple[int, int]] = []
    for dias in DIAS_SEM_CONTATO:
        limite_dt = datetime.combine(hoje, datetime.min.time()) - timedelta(days=dias)
        n = 0
        for a in por_nome.values():
            datas = [d for d in (a.max_login, a.max_atividade) if d is not None]
            if not datas:
                continue
            if max(datas) < limite_dt:
                n += 1
        parados.append((dias, n))

    meses_login = sorted(contato_mes_login.keys())[-24:]
    meses_ativ = sorted(contato_mes_ativ.keys())[-24:]
    serie_l = [(m, contato_mes_login[m]) for m in meses_login]
    serie_a = [(m, contato_mes_ativ[m]) for m in meses_ativ]

    por_ddd = Counter(a.ddd for a in por_nome.values() if a.ddd)
    sem_ddd = total - sum(por_ddd.values())
    ddd_top = por_ddd.most_common(30)

    por_uf: Counter[str] = Counter()
    ddd_nao_mapeado = 0
    for ddd, n in por_ddd.items():
        uf = DDD_PARA_UF.get(ddd)
        if uf:
            por_uf[uf] += n
        else:
            ddd_nao_mapeado += n

    contatos_faixa_80: list[tuple[str, str, str]] = []
    for nome, a in sorted(por_nome.items(), key=lambda item: item[0].lower()):
        if _faixa_dez_porcento(a.max_progresso) == 80:
            contatos_faixa_80.append(
                (
                    nome,
                    a.email or "—",
                    a.telefone_contato or "—",
                )
            )

    concluintes_recentes: list[tuple[str, str, str]] = []
    concluintes_base: list[tuple[datetime, str, str]] = []
    for nome, a in por_nome.items():
        if a.max_progresso < PROGRESSO_COMPLETO or a.max_login is None:
            continue
        concluintes_base.append(
            (
                a.max_login,
                nome,
                a.email or "—",
            )
        )
    concluintes_base.sort(key=lambda item: item[0], reverse=True)
    for dt, nome, email in concluintes_base[:10]:
        concluintes_recentes.append((nome, email, dt.strftime("%d/%m/%Y %H:%M")))

    return Relatorio(
        gerado_em=datetime.now(),
        arquivo_csv=caminho_csv.name,
        hoje=hoje,
        total_pessoas=total,
        completaram_curso=completaram,
        linhas_sem_nome=linhas_sem_nome,
        por_faixa=por_faixa,
        situacoes=situacoes,
        cols_faixa_pct=cols_f,
        cols_carga=cargas_ord,
        mat_situacao_faixa=mat_sf_f,
        mat_situacao_carga=mat_sc_f,
        nunca_logou=nunca_logou,
        logou_sem_progresso=logou_sem_progresso,
        logou_com_progresso=logou_com_progresso,
        sem_data_contato=sem_data_contato,
        parados_dias=parados,
        serie_login_mes=serie_l,
        serie_atividade_mes=serie_a,
        ddd_top=ddd_top,
        sem_ddd=sem_ddd,
        por_uf=dict(sorted(por_uf.items())),
        ddd_nao_mapeado=ddd_nao_mapeado,
        contatos_faixa_80=contatos_faixa_80,
        concluintes_recentes=concluintes_recentes,
    )


def _fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _imprimir_quadro(titulo: str, linhas: list[tuple[str, str]]) -> None:
    if not linhas:
        return
    h = _BOX["h"]
    v = _BOX["v"]
    largura_rotulo = max(len(a) for a, _ in linhas)
    largura_valor = max(len(b) for _, b in linhas)
    inner = largura_rotulo + 3 + largura_valor
    topo = h * (inner + 2)

    print(f"{_BOX['tl']}{topo}{_BOX['tr']}")
    print(f"{v} {titulo:^{inner}} {v}")
    print(f"{_BOX['lm']}{topo}{_BOX['rm']}")
    for rotulo, valor in linhas:
        linha = f"{rotulo:<{largura_rotulo}}   {valor:>{largura_valor}}"
        print(f"{v} {linha} {v}")
    print(f"{_BOX['bl']}{topo}{_BOX['br']}")


def _imprimir_tabela_faixas(por_faixa: Counter[int], total_pessoas: int) -> None:
    titulo = "Distribuição por faixa (maior % por nome · intervalos de 10%)"
    faixas = sorted(por_faixa)
    w_faixa, w_qtd, w_pct = 14, 14, 14
    h = _BOX["h"]
    v = _BOX["v"]
    inner = w_faixa + w_qtd + w_pct + 8
    topo = h * inner

    def lin_sep(left: str, mid: str, right: str) -> str:
        s = h * w_faixa + mid + h * w_qtd + mid + h * w_pct
        return left + s + right

    print()
    print(f"{_BOX['tl']}{topo}{_BOX['tr']}")
    print(f"{v} {titulo:^{inner - 2}} {v}")
    print(f"{lin_sep(_BOX['lm'], _BOX['x'], _BOX['rm'])}")
    print(
        f"{v} {'Faixa':<{w_faixa}} {v} {'Pessoas':^{w_qtd}} {v} {'% do total':^{w_pct}} {v}"
    )
    print(f"{lin_sep(_BOX['lm'], _BOX['x'], _BOX['rm'])}")
    for faixa in faixas:
        qtd = por_faixa[faixa]
        pct = (100.0 * qtd / total_pessoas) if total_pessoas else 0.0
        label = f"{faixa}%"
        qtd_s = _fmt_int(qtd)
        pct_s = f"{pct:.1f}%"
        print(
            f"{v} {label:<{w_faixa}} {v} {qtd_s:^{w_qtd}} {v} {pct_s:^{w_pct}} {v}"
        )
    print(f"{lin_sep(_BOX['lm'], _BOX['y'], _BOX['rm'])}")
    tot_s = _fmt_int(total_pessoas)
    print(
        f"{v} {'Total':<{w_faixa}} {v} {tot_s:^{w_qtd}} {v} {'100,0%':^{w_pct}} {v}"
    )
    print(f"{_BOX['bl']}{topo}{_BOX['br']}")


def _imprimir_cruzada(
    titulo: str,
    linhas: list[str],
    colunas: list[str],
    matriz: dict[tuple[str, str], int],
    total_pessoas: int,
) -> None:
    h = _BOX["h"]
    v = _BOX["v"]
    w_row = max(len("Situação"), max(len(r) for r in linhas)) + 1
    w_col = max(
        6,
        max(len(c) for c in colunas),
        max(
            (len(str(matriz.get((r, c), 0))) for r in linhas for c in colunas),
            default=4,
        ),
    )
    w_tot = max(5, len(str(total_pessoas)))
    bloco = w_row + (w_col + 3) * len(colunas) + w_tot + 4
    topo = h * bloco

    def linha_celulas(cels: list[str]) -> str:
        return f"{v} " + f" {v} ".join(cels) + f" {v}"

    print()
    print(f"{_BOX['tl']}{topo}{_BOX['tr']}")
    print(f"{v} {titulo:^{bloco}} {v}")
    print(f"{_BOX['lm']}{topo}{_BOX['rm']}")
    cab = [f"{'Situação':<{w_row}}"] + [f"{c:^{w_col}}" for c in colunas] + [f"{'Σ':>{w_tot}}"]
    print(linha_celulas(cab))
    print(f"{_BOX['lm']}{topo}{_BOX['rm']}")
    grand = 0
    for r in linhas:
        tot_lin = sum(matriz.get((r, c), 0) for c in colunas)
        cels = [f"{r:<{w_row}}"] + [f"{matriz.get((r, c), 0):^{w_col}}" for c in colunas] + [f"{tot_lin:>{w_tot}}"]
        print(linha_celulas(cels))
    print(f"{_BOX['lm']}{topo}{_BOX['rm']}")
    tot_cols: list[str] = [f"{'Total':<{w_row}}"]
    for c in colunas:
        tc = sum(matriz.get((r, c), 0) for r in linhas)
        grand += tc
        tot_cols.append(f"{tc:^{w_col}}")
    tot_cols.append(f"{grand:>{w_tot}}")
    print(linha_celulas(tot_cols))
    print(f"{_BOX['bl']}{topo}{_BOX['br']}")
    if grand != total_pessoas:
        print(
            f"  (Nota: soma da matriz = {grand}; pessoas únicas = {total_pessoas}.)"
        )


def _imprimir_serie_mensal(
    titulo: str, contagem_por_mes: Counter[str], limite: int = 24
) -> None:
    meses = sorted(contagem_por_mes.keys())[-limite:]
    if not meses:
        print(f"\n{titulo}: (sem datas válidas)")
        return
    print()
    _imprimir_quadro(
        titulo,
        [(m, _fmt_int(contagem_por_mes[m])) for m in meses],
    )


def imprimir_console(r: Relatorio) -> None:
    resumo: list[tuple[str, str]] = [
        ("Pessoas únicas (por nome)", _fmt_int(r.total_pessoas)),
        (
            f"Concluíram o curso (≥ {PROGRESSO_COMPLETO:g}%)",
            _fmt_int(r.completaram_curso),
        ),
    ]
    if r.linhas_sem_nome:
        resumo.append(
            ("Linhas ignoradas (sem nome)", _fmt_int(r.linhas_sem_nome))
        )

    _imprimir_quadro("Resumo", resumo)
    _imprimir_tabela_faixas(r.por_faixa, r.total_pessoas)

    _imprimir_cruzada(
        "Cruzada: situação (no maior progresso) × faixa de progresso",
        r.situacoes,
        r.cols_faixa_pct,
        r.mat_situacao_faixa,
        r.total_pessoas,
    )
    _imprimir_cruzada(
        "Cruzada: situação (no maior progresso) × carga horária (h)",
        r.situacoes,
        r.cols_carga,
        r.mat_situacao_carga,
        r.total_pessoas,
    )

    _imprimir_quadro(
        "Login × progresso (pessoas únicas)",
        [
            (
                "Nunca logou (campo ULTIMO_LOGIN vazio em todas as linhas)",
                _fmt_int(r.nunca_logou),
            ),
            ("Logou e maior progresso = 0%", _fmt_int(r.logou_sem_progresso)),
            (
                "Logou e já tem progresso > 0%",
                _fmt_int(r.logou_com_progresso),
            ),
        ],
    )

    _imprimir_quadro(
        "Datas (consolidado por pessoa)",
        [
            (
                "Sem nenhuma data válida (login e atividade)",
                _fmt_int(r.sem_data_contato),
            ),
            ("Referência para inatividade (hoje)", r.hoje.strftime("%d/%m/%Y")),
        ],
    )

    _imprimir_quadro(
        "Inatividade (último contato = mais recente entre login e atividade)",
        [
            (
                f"Parados: último login ou atividade há ≥ {d} dias",
                _fmt_int(n),
            )
            for d, n in r.parados_dias
        ],
    )

    cont_login = Counter(dict(r.serie_login_mes))
    cont_ativ = Counter(dict(r.serie_atividade_mes))
    _imprimir_serie_mensal(
        "Pessoas por mês do último login (uma pessoa no mês do seu login mais recente)",
        cont_login,
    )
    _imprimir_serie_mensal(
        "Pessoas por mês da última atividade (uma pessoa no mês da atividade mais recente)",
        cont_ativ,
    )

    print()
    _imprimir_quadro(
        "Telefone — DDD (primeiros dígitos após normalizar, 1ª ocorrência válida por pessoa)",
        [(f"DDD {ddd}", _fmt_int(n)) for ddd, n in r.ddd_top]
        + [("Sem DDD válido / sem telefone", _fmt_int(r.sem_ddd))],
    )


def _esc(c: str) -> str:
    return html.escape(c, quote=True)


def _tabela_simples(cabecalhos: list[str], linhas: list[list[str]]) -> str:
    th = "".join(f"<th>{_esc(h)}</th>" for h in cabecalhos)
    body = ""
    for row in linhas:
        body += "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>"
    return f'<table class="data"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


def _tabela_cruzada(
    titulo_secao: str,
    linhas_rotulo: list[str],
    colunas: list[str],
    matriz: dict[tuple[str, str], int],
    rotulo_linha: str = "Situação",
) -> str:
    th = f"<th>{_esc(rotulo_linha)}</th>" + "".join(
        f"<th>{_esc(c)}</th>" for c in colunas
    )
    th += '<th class="num">Total</th>'
    body = ""
    for r in linhas_rotulo:
        tot = sum(matriz.get((r, c), 0) for c in colunas)
        cells = "".join(
            f'<td class="num">{matriz.get((r, c), 0)}</td>' for c in colunas
        )
        body += f'<tr><td>{_esc(r)}</td>{cells}<td class="num"><strong>{tot}</strong></td></tr>'
    tot_cols = []
    grand = 0
    for c in colunas:
        tc = sum(matriz.get((rr, c), 0) for rr in linhas_rotulo)
        grand += tc
        tot_cols.append(tc)
    foot = "<td><strong>Total</strong></td>"
    foot += "".join(f'<td class="num"><strong>{v}</strong></td>' for v in tot_cols)
    foot += f'<td class="num"><strong>{grand}</strong></td>'
    return (
        f'<section class="block"><h2>{_esc(titulo_secao)}</h2>'
        f'<div class="scroll-x"><table class="data cross">'
        f"<thead><tr>{th}</tr></thead><tbody>{body}</tbody>"
        f"<tfoot><tr>{foot}</tr></tfoot></table></div></section>"
    )


def _iter_exterior_rings(geometry: dict) -> list[list[tuple[float, float]]]:
    """Anéis exteriores de Polygon / MultiPolygon (GeoJSON)."""
    t = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return []
    rings: list[list[tuple[float, float]]] = []
    if t == "Polygon":
        rings.append([(float(lon), float(lat)) for lon, lat in coords[0]])
    elif t == "MultiPolygon":
        for poly in coords:
            rings.append([(float(lon), float(lat)) for lon, lat in poly[0]])
    return rings


def _expand_bbox_ring(
    bbox: tuple[float, float, float, float],
    ring: list[tuple[float, float]],
) -> tuple[float, float, float, float]:
    min_lon, min_lat, max_lon, max_lat = bbox
    for lon, lat in ring:
        min_lon = min(min_lon, lon)
        max_lon = max(max_lon, lon)
        min_lat = min(min_lat, lat)
        max_lat = max(max_lat, lat)
    return (min_lon, min_lat, max_lon, max_lat)


def _cor_choropleth(n: int, nmax: int) -> str:
    """Cor mais forte quanto maior n (fundo escuro do relatório)."""
    if nmax <= 0:
        t = 0.0
    else:
        t = min(1.0, max(0.0, n / nmax))
    r = int(40 + t * 95)
    g = int(55 + t * 155)
    b = int(85 + t * 215)
    return f"#{r:02x}{g:02x}{b:02x}"


def _proj_xy(
    lon: float,
    lat: float,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    w: float,
    h: float,
) -> tuple[float, float]:
    den_x = max(max_lon - min_lon, 1e-9)
    den_y = max(max_lat - min_lat, 1e-9)
    x = (lon - min_lon) / den_x * w
    y = (max_lat - lat) / den_y * h
    return round(x, 2), round(y, 2)


def _area_anel_lonlat(ring: list[tuple[float, float]]) -> float:
    pts = list(ring)
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    n = len(pts)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        j = (i + 1) % n
        s += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
    return s * 0.5


def _maior_anel(rings: list[list[tuple[float, float]]]) -> list[tuple[float, float]] | None:
    cand = [r for r in rings if len(r) >= 3]
    if not cand:
        return None
    best = cand[0]
    ba = abs(_area_anel_lonlat(best))
    for r in cand[1:]:
        a = abs(_area_anel_lonlat(r))
        if a > ba:
            ba = a
            best = r
    return best


def _centroide_anel_lonlat(ring: list[tuple[float, float]]) -> tuple[float, float]:
    pts = list(ring)
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    n = len(pts)
    if n == 0:
        return (0.0, 0.0)
    if n < 3:
        return (pts[0][0], pts[0][1])
    a = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        j = (i + 1) % n
        cross = pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
        a += cross
        cx += (pts[i][0] + pts[j][0]) * cross
        cy += (pts[i][1] + pts[j][1]) * cross
    a *= 0.5
    if abs(a) < 1e-14:
        return (
            sum(p[0] for p in pts) / n,
            sum(p[1] for p in pts) / n,
        )
    return (cx / (6 * a), cy / (6 * a))


def _ring_para_path_d(
    ring: list[tuple[float, float]],
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    w: float,
    h: float,
) -> str:
    parts: list[str] = []
    first = True
    for lon, lat in ring:
        x, y = _proj_xy(lon, lat, min_lon, min_lat, max_lon, max_lat, w, h)
        if first:
            parts.append(f"M{x} {y}")
            first = False
        else:
            parts.append(f"L{x} {y}")
    parts.append("Z")
    return " ".join(parts)


def _gerar_svg_mapa_brasil(por_uf: dict[str, int], caminho: Path) -> str | None:
    """SVG estático (choropleth por UF). Sem APIs; usa GeoJSON local."""
    if not caminho.is_file():
        return None
    try:
        with caminho.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    feats = data.get("features") or []
    if not feats:
        return None

    nmax = max(por_uf.values(), default=0)
    if nmax <= 0:
        nmax = 1

    min_lon, min_lat = 180.0, 90.0
    max_lon, max_lat = -180.0, -90.0
    feature_rings: list[tuple[str, list[list[tuple[float, float]]]]] = []

    for feat in feats:
        props = feat.get("properties") or {}
        cod = str(props.get("codarea", "")).strip()
        sigla = CODIGO_IBGE_PARA_SIGLA.get(cod)
        geom = feat.get("geometry")
        if not sigla or not geom:
            continue
        rings = _iter_exterior_rings(geom)
        if not rings:
            continue
        for ring in rings:
            if len(ring) >= 3:
                min_lon, min_lat, max_lon, max_lat = _expand_bbox_ring(
                    (min_lon, min_lat, max_lon, max_lat), ring
                )
        feature_rings.append((sigla, rings))

    if max_lon <= min_lon or max_lat <= min_lat:
        return None

    svg_w, svg_h = 560.0, 620.0
    paths_html: list[str] = []
    for sigla, rings in feature_rings:
        d_join = " ".join(
            _ring_para_path_d(r, min_lon, min_lat, max_lon, max_lat, svg_w, svg_h)
            for r in rings
            if len(r) >= 3
        )
        if not d_join.strip():
            continue
        n = por_uf.get(sigla, 0)
        fill = _cor_choropleth(n, nmax)
        title = f"{sigla}: {_fmt_int(n)} pessoas"
        paths_html.append(
            f'<path fill="{fill}" stroke="#0f1419" stroke-width="0.65" '
            f'd="{html.escape(d_join, quote=False)}" data-uf="{html.escape(sigla)}">'
            f"<title>{html.escape(title)}</title></path>"
        )

    if not paths_html:
        return None

    rotulos: list[str] = []
    for sigla, rings in feature_rings:
        maior = _maior_anel(rings)
        if not maior:
            continue
        lon_c, lat_c = _centroide_anel_lonlat(maior)
        x_c, y_c = _proj_xy(
            lon_c, lat_c, min_lon, min_lat, max_lon, max_lat, svg_w, svg_h
        )
        x_c = round(x_c, 2)
        y_c = round(y_c, 2)
        n = por_uf.get(sigla, 0)
        txt_n = _fmt_int(n)
        y1 = round(y_c - 6, 2)
        y2 = round(y_c + 8, 2)
        rotulos.append(
            f'<g class="uf-rotulo" data-uf="{html.escape(sigla)}">'
            f'<text x="{x_c}" y="{y1}" text-anchor="middle" '
            f'class="map-uf-sigla">{html.escape(sigla)}</text>'
            f'<text x="{x_c}" y="{y2}" text-anchor="middle" '
            f'class="map-uf-n">{html.escape(txt_n)}</text>'
            f"</g>"
        )

    paths_block = "\n    ".join(paths_html)
    rotulos_block = "\n    ".join(rotulos)
    return (
        f'<svg class="mapa-svg" viewBox="0 0 {svg_w} {svg_h}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Mapa do Brasil por UF (densidade aproximada por DDD)">'
        f'\n  <g class="mapa-estados">{paths_block}\n  </g>'
        f'\n  <g class="mapa-rotulos">{rotulos_block}\n  </g>\n</svg>'
    )


def _html_bloco_mapa_visual(r: Relatorio) -> str:
    """Coluna esquerda: apenas mapa + legenda (SVG estático)."""
    svg = _gerar_svg_mapa_brasil(r.por_uf, GEOJSON_UFS_PATH)
    extra = ""
    if r.ddd_nao_mapeado:
        extra = (
            f"<p class=\"muted map-foot\">DDD sem correspondência na tabela de UFs: "
            f"<strong>{_fmt_int(r.ddd_nao_mapeado)}</strong> pessoas (não entram no mapa).</p>"
        )
    if svg is None:
        mapa_bloco = (
            f'<p class="muted">Não foi possível gerar o mapa. Coloque o arquivo '
            f"<code>br_ibge_uf.json</code> na pasta do script (GeoJSON das UFs do IBGE). "
            f"Baixe em: <code>https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
            f"?formato=application/vnd.geo+json&intrarregiao=UF&qualidade=minima</code></p>"
        )
    else:
        mapa_bloco = (
            f'<div class="mapa-estatico-wrap">{svg}</div>'
            '<div class="mapa-legenda">'
            '<span class="muted">Menos pessoas</span>'
            '<div class="legenda-gradiente" role="presentation"></div>'
            '<span class="muted">Mais pessoas</span>'
            "</div>"
        )
    return f"""
    <section class="block">
      <h2>Mapa por estado (UF)</h2>
      <p class="muted">Imagem vetorial (SVG): cada estado conforme o DDD (aproximação). <strong>Cor mais forte = mais pessoas.</strong> Sem mapas online.</p>
      {mapa_bloco}
      {extra}
    </section>
    """


def _html_tabela_ddd(r: Relatorio) -> str:
    linhas: list[list[str]] = []
    for ddd, n in r.ddd_top:
        uf = DDD_PARA_UF.get(ddd)
        linhas.append([f"DDD {ddd}", uf if uf else "—", _fmt_int(n)])
    linhas.append(["Sem DDD válido / sem telefone", "—", _fmt_int(r.sem_ddd)])
    return f"""
    <section class="block">
      <h2>Tabela DDD (detalhe)</h2>
      {_tabela_simples(["Região (DDD)", "UF", "Pessoas"], linhas)}
    </section>
    """


def _barras_horizontais(
    titulo: str, itens: list[tuple[str, int]], cor: str
) -> str:
    if not itens:
        return f'<section class="block"><h2>{_esc(titulo)}</h2><p class="muted">Sem dados.</p></section>'
    mx = max(n for _, n in itens) or 1
    rows = ""
    for label, n in itens:
        pct = 100.0 * n / mx
        rows += (
            f'<div class="bar-row"><span class="bar-label">{_esc(label)}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%;background:{cor}"></div></div>'
            f'<span class="bar-val">{_fmt_int(n)}</span></div>'
        )
    return f'<section class="block"><h2>{_esc(titulo)}</h2><div class="bars">{rows}</div></section>'


def _barras_verticais(
    titulo: str, itens: list[tuple[str, int]], cor: str
) -> str:
    if not itens:
        return f'<section class="block"><h2>{_esc(titulo)}</h2><p class="muted">Sem dados.</p></section>'
    mx = max(n for _, n in itens) or 1
    cols = ""
    for label, n in itens:
        pct = 100.0 * n / mx
        cols += (
            '<div class="vbar-col">'
            f'<div class="vbar-val">{_fmt_int(n)}</div>'
            f'<div class="vbar-track"><div class="vbar-fill" style="height:{pct:.1f}%;background:{cor}"></div></div>'
            f'<div class="vbar-label">{_esc(label)}</div>'
            "</div>"
        )
    return f'<section class="block"><h2>{_esc(titulo)}</h2><div class="vbars">{cols}</div></section>'


def _rotulo_mes_pt(chave: str) -> str:
    meses = {
        "01": "jan",
        "02": "fev",
        "03": "mar",
        "04": "abr",
        "05": "mai",
        "06": "jun",
        "07": "jul",
        "08": "ago",
        "09": "set",
        "10": "out",
        "11": "nov",
        "12": "dez",
    }
    s = (chave or "").strip()
    if len(s) == 7 and s[4] == "-":
        ano, mes = s.split("-", 1)
        if ano.isdigit() and mes in meses:
            return f"{meses[mes]}/{ano}"
    return s


def _html_fragmento_relatorio(r: Relatorio, *, exito_layout: bool = False) -> str:
    faixas = sorted(r.por_faixa.keys())
    linhas_faixa: list[list[str]] = []
    for f in faixas:
        q = r.por_faixa[f]
        p = (100.0 * q / r.total_pessoas) if r.total_pessoas else 0.0
        linhas_faixa.append([f"{f}%", _fmt_int(q), f"{p:.1f}%"])
    linhas_faixa.append(["Total", _fmt_int(r.total_pessoas), "100,0%"])

    kpi = f"""
    <div class="kpi-deck">
      <div class="kpis">
        <div class="kpi"><span class="kpi-val">{_esc(_fmt_int(r.total_pessoas))}</span><span class="kpi-lbl">Pessoas únicas</span></div>
        <div class="kpi"><span class="kpi-val">{_esc(_fmt_int(r.completaram_curso))}</span><span class="kpi-lbl">Concluíram (≥ {PROGRESSO_COMPLETO:g}%)</span></div>
        <div class="kpi"><span class="kpi-val">{_esc(_fmt_int(r.nunca_logou))}</span><span class="kpi-lbl">Nunca logou</span></div>
        <div class="kpi"><span class="kpi-val">{_esc(_fmt_int(r.parados_dias[-1][1] if r.parados_dias else 0))}</span><span class="kpi-lbl">Parados ≥ {r.parados_dias[-1][0] if r.parados_dias else 90} dias</span></div>
      </div>
    </div>
    """

    login_rows = [
        ["Nunca logou (ULTIMO_LOGIN vazio em todas as linhas)", _fmt_int(r.nunca_logou)],
        ["Logou e maior progresso = 0%", _fmt_int(r.logou_sem_progresso)],
        ["Logou e já tem progresso > 0%", _fmt_int(r.logou_com_progresso)],
    ]
    data_rows = [
        ["Sem data válida (login e atividade)", _fmt_int(r.sem_data_contato)],
        ["Referência (hoje)", r.hoje.strftime("%d/%m/%Y")],
    ]
    inat_rows = [
        [f"Parados ≥ {d} dias (último login ou atividade)", _fmt_int(n)]
        for d, n in r.parados_dias
    ]
    mat_carga_situacao = {
        (carga, situacao): n
        for (situacao, carga), n in r.mat_situacao_carga.items()
    }
    card_carga = (
        _tabela_cruzada(
            "Carga horária (h) × situação",
            r.cols_carga,
            r.situacoes,
            mat_carga_situacao,
            rotulo_linha="Turmas",
        )
        if exito_layout
        else _tabela_cruzada(
            "Situação × carga horária (h)",
            r.situacoes,
            r.cols_carga,
            r.mat_situacao_carga,
        )
    )
    bloco_carga_inicio = "" if exito_layout else card_carga
    bloco_carga_final = card_carga if exito_layout else ""
    card_situacao_faixa = _tabela_cruzada(
        "Situação × faixa de progresso",
        r.situacoes,
        r.cols_faixa_pct,
        r.mat_situacao_faixa,
    )
    bloco_situacao_faixa_inicio = "" if exito_layout else card_situacao_faixa
    bloco_situacao_faixa_final = card_situacao_faixa if exito_layout else ""
    bloco_contatos_faixa_80 = ""
    if not exito_layout:
        linhas_80 = [list(item) for item in r.contatos_faixa_80]
        bloco_contatos_faixa_80 = f"""
        <section class="block">
          <h2>Pessoas na faixa de 80% ({_fmt_int(len(r.contatos_faixa_80))})</h2>
          {_tabela_simples(["Nome", "E-mail", "Telefone"], linhas_80)}
        </section>
        """
    bloco_concluintes_recentes = ""
    if exito_layout:
        linhas_concluintes = [list(item) for item in r.concluintes_recentes]
        bloco_concluintes_recentes = f"""
        <section class="block">
          <h2>Últimos 10 concluintes (mais recentes)</h2>
          {_tabela_simples(["Nome", "E-mail", "Data"], linhas_concluintes)}
        </section>
        """
    bloco_mapa = (
        ""
        if exito_layout
        else f"""
    <div class="colunas-2">
      {_html_bloco_mapa_visual(r)}
      <div class="coluna-stack">
        {_html_tabela_ddd(r)}
      </div>
    </div>
    """
    )

    return f"""
    <header class="cabecalho-relatorio">
      <h1>Relatório de progresso educacional</h1>
      <p class="meta-linha">Arquivo: {_esc(r.arquivo_csv)} · Gerado em {_esc(r.gerado_em.strftime("%d/%m/%Y %H:%M"))} · Critério de conclusão: ≥ {PROGRESSO_COMPLETO:g}%</p>
      <h2 class="titulo-notas">Notas metodológicas</h2>
      <ul class="lista-notas">
        <li>Uma pessoa = um nome único no CSV; várias linhas do mesmo nome são consolidadas.</li>
        <li>Situação e carga horária vêm do registro com maior progresso (empate: prioriza REPROVADO).</li>
        <li>Séries mensais: cada pessoa conta uma vez, no mês do seu último login ou da última atividade registrada.</li>
        <li>Parados: sem contato (login ou atividade) há pelo menos N dias, entre quem tem pelo menos uma data válida.</li>
        <li>Mapa: figura estática (SVG) a partir do GeoJSON de UFs; cores por volume (DDD → UF). Sem Google Maps nem outros mapas interativos online.</li>
      </ul>
    </header>

    {kpi}

    <div class="colunas-2">
      <section class="block">
        <h2>Distribuição por faixa de progresso (10%)</h2>
        {_tabela_simples(["Faixa", "Pessoas", "% do total"], linhas_faixa)}
      </section>
      {_barras_verticais("Faixas de progresso (visual)", [(f"{f}%", r.por_faixa[f]) for f in faixas], "var(--accent)")}
    </div>

    {bloco_contatos_faixa_80}
    {bloco_concluintes_recentes}

    <div class="colunas-2">
      {bloco_situacao_faixa_inicio}
      {bloco_carga_inicio}
    </div>

    <div class="colunas-2">
      <section class="block">
        <h2>Login × progresso</h2>
        {_tabela_simples(["Indicador", "Pessoas"], login_rows)}
      </section>
      <section class="block">
        <h2>Datas e inatividade</h2>
        {_tabela_simples(["Indicador", "Valor"], data_rows + inat_rows)}
      </section>
    </div>

    <div class="colunas-2">
      {_barras_verticais("Pessoas por mês do último login", [(_rotulo_mes_pt(m), n) for m, n in r.serie_login_mes], "var(--accent2)")}
      {_barras_verticais("Pessoas por mês da última atividade", [(_rotulo_mes_pt(m), n) for m, n in r.serie_atividade_mes], "var(--warn)")}
    </div>

    {bloco_mapa}
    {bloco_situacao_faixa_final}
    {bloco_carga_final}
    """


def _html_sem_csv_origem(rotulo_origem: str, caminho_csv: Path) -> str:
    nome = caminho_csv.name
    return f"""
    <header class="cabecalho-relatorio">
      <h1>Relatório de progresso educacional</h1>
      <p class="meta-linha">Origem: {_esc(rotulo_origem)} · CSV esperado: {_esc(nome)} · Critério de conclusão: ≥ {PROGRESSO_COMPLETO:g}%</p>
      <h2 class="titulo-notas">Notas metodológicas</h2>
      <ul class="lista-notas">
        <li>Uma pessoa = um nome único no CSV; várias linhas do mesmo nome são consolidadas.</li>
        <li>Situação e carga horária vêm do registro com maior progresso (empate: prioriza REPROVADO).</li>
        <li>Séries mensais: cada pessoa conta uma vez, no mês do seu último login ou da última atividade registrada.</li>
        <li>Parados: sem contato (login ou atividade) há pelo menos N dias, entre quem tem pelo menos uma data válida.</li>
        <li>Mapa: figura estática (SVG) a partir do GeoJSON de UFs; cores por volume (DDD → UF). Sem Google Maps nem outros mapas interativos online.</li>
      </ul>
    </header>
    <section class="block">
      <h2>Sem dados para esta origem</h2>
      <p class="muted">O arquivo <strong>{_esc(nome)}</strong> não foi encontrado na pasta do script.</p>
      <p>Coloque um CSV com o mesmo formato das colunas (NOME, PROGRESSO, SITUACAO, CARGA_HORARIA, ULTIMO_LOGIN, ULTIMO_REGISTRO_DE_ATIVIDADE, TELEFONE) e execute novamente:</p>
      <p><code class="cmd-hint">python3 script.py</code></p>
    </section>
    """


def escrever_html_abas(
    abas: list[tuple[str, str, Relatorio | None, Path]],
    destino: Path,
) -> None:
    """Gera HTML com abas. Cada item: (id_slug, rótulo exibido, relatório ou None, path do CSV esperado)."""
    botoes = []
    paineis = []
    for i, (slug, label, rel, csv_esperado) in enumerate(abas):
        panel_id = f"panel-{slug}"
        sel = "true" if i == 0 else "false"
        botoes.append(
            f'<button type="button" class="tab-btn" role="tab" id="tab-{slug}" '
            f'aria-controls="{panel_id}" aria-selected="{sel}" data-panel="{slug}">{_esc(label)}</button>'
        )
        active = " is-active" if i == 0 else ""
        inner = (
            _html_fragmento_relatorio(rel, exito_layout=(slug == "instituto-exito"))
            if rel is not None
            else _html_sem_csv_origem(label, csv_esperado)
        )
        paineis.append(
            f'<div class="tab-panel{active}" role="tabpanel" id="{panel_id}" '
            f'aria-labelledby="tab-{slug}" tabindex="0">{inner}</div>'
        )

    tabs_html = '<div class="tab-bar" role="tablist">' + "".join(botoes) + "</div>"
    panels_html = "".join(paineis)

    doc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Relatório de progresso — GoKursos / Instituto Exito</title>
  <style>
    :root {{
      --bg: #0f1419;
      --card: #1a2332;
      --panel: #141c28;
      --border: #2d3a4d;
      --text: #e7eef8;
      --muted: #8b9cb3;
      --accent: #3d8bfd;
      --accent2: #22c55e;
      --warn: #f59e0b;
      --shadow-card: 0 4px 22px rgba(0, 0, 0, 0.32);
      --tab-bg: #1f2937;
      --tab-text: #e7eef8;
      --tab-hover-bg: #273449;
      --tab-border: #3b4a61;
      --tab-active-ring: #3d8bfd;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --bg: #f3f6fb;
        --card: #ffffff;
        --panel: #f8fafc;
        --border: #d6deea;
        --text: #0f172a;
        --muted: #475569;
        --accent: #2563eb;
        --accent2: #16a34a;
        --warn: #d97706;
        --shadow-card: 0 4px 18px rgba(15, 23, 42, 0.08);
        --tab-bg: #ffffff;
        --tab-text: #111827;
        --tab-hover-bg: #f8fafc;
        --tab-border: #cbd5e1;
        --tab-active-ring: #2563eb;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    .wrap {{
      width: 100%;
      max-width: 100%;
      margin: 0;
      padding: 1.5rem clamp(1rem, 2.5vw, 2.75rem) 3rem;
    }}
    .cabecalho-relatorio {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.35rem 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: var(--shadow-card);
    }}
    .cabecalho-relatorio h1 {{
      font-size: clamp(1.35rem, 2.5vw, 1.85rem);
      font-weight: 650;
      margin: 0 0 0.65rem;
      letter-spacing: -0.02em;
    }}
    .cabecalho-relatorio .meta-linha {{
      color: var(--muted);
      font-size: 0.9rem;
      margin: 0 0 1.25rem;
      padding-bottom: 1.15rem;
      border-bottom: 1px solid var(--border);
      line-height: 1.55;
    }}
    .cabecalho-relatorio .titulo-notas {{
      font-size: 1.05rem;
      font-weight: 600;
      margin: 0 0 0.75rem;
      color: var(--text);
    }}
    .cabecalho-relatorio .lista-notas {{
      margin: 0;
      padding-left: 1.15rem;
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.55;
    }}
    .cabecalho-relatorio .lista-notas li {{
      margin-bottom: 0.5rem;
    }}
    .cabecalho-relatorio .lista-notas li:last-child {{
      margin-bottom: 0;
    }}
    .kpi-deck {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.25rem 1.35rem;
      margin-bottom: 1.5rem;
      box-shadow: var(--shadow-card);
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
      margin: 0;
    }}
    @media (min-width: 900px) {{
      .kpis {{ grid-template-columns: repeat(4, 1fr); }}
    }}
    .kpi {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1.1rem 1.2rem;
    }}
    .kpi-val {{ display: block; font-size: 1.65rem; font-weight: 700; color: var(--accent); }}
    .kpi-lbl {{ font-size: 0.82rem; color: var(--muted); }}
    .block {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.2rem 1.35rem 1.35rem;
      margin-bottom: 2.5rem;
      box-shadow: var(--shadow-card);
    }}
    .block h2 {{
      font-size: 1.15rem;
      font-weight: 600;
      margin: 0 0 1rem;
      color: var(--text);
      padding-bottom: 0.55rem;
      border-bottom: 1px solid var(--border);
    }}
    .scroll-x {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
    table.data {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
      background: var(--panel);
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid var(--border);
    }}
    table.data th, table.data td {{
      padding: 0.55rem 0.75rem;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}
    table.data thead th {{
      background: #243044;
      font-weight: 600;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }}
    table.data tbody tr:hover {{ background: rgba(61, 139, 253, 0.06); }}
    table.data tfoot td {{ background: #1e2838; font-weight: 600; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    /* Todas as linhas de conteúdo em duas colunas no desktop; uma coluna no mobile */
    .colunas-2 {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 1.35rem clamp(1rem, 2vw, 2rem);
      margin-bottom: 1.5rem;
      align-items: stretch;
    }}
    .colunas-2 > .block,
    .colunas-2 > .coluna-stack {{
      margin-bottom: 0;
      min-width: 0;
    }}
    .coluna-stack {{
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      min-width: 0;
    }}
    .coluna-stack > .block {{
      margin-bottom: 0;
    }}
    @media (min-width: 768px) {{
      .colunas-2 {{ grid-template-columns: 1fr 1fr; }}
    }}
    .bars {{ display: flex; flex-direction: column; gap: 0.45rem; }}
    .bar-row {{
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) auto;
      align-items: center;
      gap: 0.5rem 0.65rem;
      font-size: 0.88rem;
    }}
    .bar-label {{ color: var(--muted); }}
    .bar-track {{
      height: 10px;
      background: #243044;
      border-radius: 6px;
      overflow: hidden;
    }}
    .bar-fill {{ height: 100%; border-radius: 6px; min-width: 2px; }}
    .bar-val {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .vbars {{
      display: flex;
      gap: 0.8rem;
      align-items: end;
      width: 100%;
      min-height: 460px;
      overflow-x: auto;
      padding: 0.25rem 0.15rem 0.35rem;
    }}
    .vbar-col {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.45rem;
      flex: 1 0 78px;
      min-width: 78px;
    }}
    .vbar-val {{
      font-size: 1rem;
      font-weight: 700;
      color: var(--text);
      font-variant-numeric: tabular-nums;
      text-align: center;
      line-height: 1.1;
    }}
    .vbar-track {{
      width: 100%;
      max-width: 100%;
      height: 380px;
      background: color-mix(in srgb, var(--muted) 22%, transparent);
      border-radius: 8px;
      border: 1px solid var(--border);
      display: flex;
      align-items: end;
      overflow: hidden;
    }}
    .vbar-fill {{
      width: 100%;
      border-radius: 6px 6px 0 0;
      min-height: 2px;
      box-shadow: 0 -1px 0 rgba(255, 255, 255, 0.15) inset;
    }}
    .vbar-label {{
      font-size: 0.78rem;
      color: var(--text);
      text-align: center;
      line-height: 1.1;
      font-variant-numeric: tabular-nums;
    }}
    .muted {{ color: var(--muted); }}
    .mapa-estatico-wrap {{
      max-width: 100%;
      background: var(--panel);
      border-radius: 10px;
      border: 1px solid var(--border);
      padding: 0.65rem;
      margin-bottom: 0.35rem;
    }}
    .mapa-svg {{
      display: block;
      width: 100%;
      height: auto;
      max-height: 640px;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    }}
    .mapa-svg .map-uf-sigla {{
      font-size: 11px;
      font-weight: 700;
      fill: #ffffff;
      stroke: #0f1419;
      stroke-width: 0.5px;
      paint-order: stroke fill;
    }}
    .mapa-svg .map-uf-n {{
      font-size: 9.5px;
      font-weight: 600;
      fill: #e7eef8;
      stroke: #0f1419;
      stroke-width: 0.4px;
      paint-order: stroke fill;
    }}
    .mapa-legenda {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
      margin: 0.5rem 0 0;
      font-size: 0.82rem;
    }}
    .legenda-gradiente {{
      flex: 1;
      min-width: 80px;
      height: 10px;
      border-radius: 5px;
      background: linear-gradient(90deg, #283757 0%, #87d2e6 100%);
    }}
    .map-foot {{ font-size: 0.82rem; margin: 0.35rem 0 1rem; }}
    .subh {{
      font-size: 1rem;
      font-weight: 600;
      margin: 1.5rem 0 0.65rem;
      color: var(--text);
    }}
    .tab-bar {{
      display: flex;
      justify-content: center;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 1.35rem;
      padding: 0.35rem;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: var(--shadow-card);
    }}
    .tab-btn {{
      appearance: none;
      font: inherit;
      cursor: pointer;
      border: 1px solid var(--tab-border);
      background: var(--tab-bg);
      color: var(--tab-text);
      min-width: 240px;
      padding: 0.95rem 1.5rem;
      border-radius: 8px;
      font-weight: 600;
      font-size: 1.2rem;
      text-align: center;
      transition: background 0.15s, color 0.15s, border-color 0.15s;
    }}
    .tab-btn:hover {{
      color: var(--tab-text);
      border-color: var(--accent);
      background: var(--tab-hover-bg);
    }}
    .tab-btn[aria-selected="true"] {{
      background: var(--tab-bg);
      color: var(--tab-text);
      border-color: var(--accent);
      box-shadow: inset 0 0 0 2px var(--tab-active-ring);
    }}
    .tab-panel {{
      display: none;
    }}
    .tab-panel.is-active {{
      display: block;
    }}
    .cmd-hint {{
      display: inline-block;
      background: var(--panel);
      border: 1px solid var(--border);
      padding: 0.35rem 0.65rem;
      border-radius: 6px;
      font-size: 0.9rem;
    }}
    @media print {{
      body {{ background: #fff; color: #111; }}
      .cabecalho-relatorio, .kpi-deck, .block {{
        box-shadow: none;
        background: #fff;
        border-color: #ccc;
      }}
      .kpi, table.data, .bar-track, .vbar-track {{ border-color: #ccc; }}
      .kpi-val {{ color: #06c; }}
      .colunas-2 {{ grid-template-columns: 1fr; }}
      .cabecalho-relatorio {{ grid-template-columns: 1fr; }}
      .tab-bar {{ display: none; }}
      .tab-panel {{ display: block !important; }}
      .tab-panel + .tab-panel {{ page-break-before: always; }}
    }}
    @media (prefers-color-scheme: light) {{
      table.data thead th {{ background: #e5e7eb; }}
      table.data tbody tr:hover {{ background: #f1f5f9; }}
      table.data tfoot td {{ background: #e2e8f0; }}
      table.data th, table.data td {{ border-bottom: 1px solid #d1d5db; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    {tabs_html}
    {panels_html}
  </div>
  <script>
  (function () {{
    var tabs = document.querySelectorAll(".tab-bar [role=tab]");
    var panels = document.querySelectorAll(".tab-panel");
    function show(slug) {{
      tabs.forEach(function (btn) {{
        var on = btn.getAttribute("data-panel") === slug;
        btn.setAttribute("aria-selected", on ? "true" : "false");
      }});
      panels.forEach(function (p) {{
        p.classList.toggle("is-active", p.id === "panel-" + slug);
      }});
    }}
    tabs.forEach(function (btn) {{
      btn.addEventListener("click", function () {{
        show(btn.getAttribute("data-panel"));
      }});
    }});
  }})();
  </script>
</body>
</html>
"""

    destino.write_text(doc, encoding="utf-8")


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
    )
    print()
    print(f"Relatório HTML salvo em: {HTML_PATH}")


if __name__ == "__main__":
    main()
