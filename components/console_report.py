"""Saída formatada no terminal (resumo em caixas Unicode)."""

from __future__ import annotations

from collections import Counter

from components.constants import BOX, PROGRESSO_COMPLETO
from components.html_utils import fmt_int
from components.models import Relatorio


def _imprimir_quadro(titulo: str, linhas: list[tuple[str, str]]) -> None:
    if not linhas:
        return
    h = BOX["h"]
    v = BOX["v"]
    largura_rotulo = max(len(a) for a, _ in linhas)
    largura_valor = max(len(b) for _, b in linhas)
    inner = largura_rotulo + 3 + largura_valor
    topo = h * (inner + 2)

    print(f"{BOX['tl']}{topo}{BOX['tr']}")
    print(f"{v} {titulo:^{inner}} {v}")
    print(f"{BOX['lm']}{topo}{BOX['rm']}")
    for rotulo, valor in linhas:
        linha = f"{rotulo:<{largura_rotulo}}   {valor:>{largura_valor}}"
        print(f"{v} {linha} {v}")
    print(f"{BOX['bl']}{topo}{BOX['br']}")


def _imprimir_tabela_faixas(por_faixa: Counter[int], total_pessoas: int) -> None:
    titulo = "Distribuição por faixa (maior % por nome · intervalos de 10%)"
    faixas = sorted(por_faixa)
    w_faixa, w_qtd, w_pct = 14, 14, 14
    h = BOX["h"]
    v = BOX["v"]
    inner = w_faixa + w_qtd + w_pct + 8
    topo = h * inner

    def lin_sep(left: str, mid: str, right: str) -> str:
        s = h * w_faixa + mid + h * w_qtd + mid + h * w_pct
        return left + s + right

    print()
    print(f"{BOX['tl']}{topo}{BOX['tr']}")
    print(f"{v} {titulo:^{inner - 2}} {v}")
    print(f"{lin_sep(BOX['lm'], BOX['x'], BOX['rm'])}")
    print(
        f"{v} {'Faixa':<{w_faixa}} {v} {'Pessoas':^{w_qtd}} {v} {'% do total':^{w_pct}} {v}"
    )
    print(f"{lin_sep(BOX['lm'], BOX['x'], BOX['rm'])}")
    for faixa in faixas:
        qtd = por_faixa[faixa]
        pct = (100.0 * qtd / total_pessoas) if total_pessoas else 0.0
        label = f"{faixa}%"
        qtd_s = fmt_int(qtd)
        pct_s = f"{pct:.1f}%"
        print(
            f"{v} {label:<{w_faixa}} {v} {qtd_s:^{w_qtd}} {v} {pct_s:^{w_pct}} {v}"
        )
    print(f"{lin_sep(BOX['lm'], BOX['y'], BOX['rm'])}")
    tot_s = fmt_int(total_pessoas)
    print(
        f"{v} {'Total':<{w_faixa}} {v} {tot_s:^{w_qtd}} {v} {'100,0%':^{w_pct}} {v}"
    )
    print(f"{BOX['bl']}{topo}{BOX['br']}")


def _imprimir_cruzada(
    titulo: str,
    linhas: list[str],
    colunas: list[str],
    matriz: dict[tuple[str, str], int],
    total_pessoas: int,
) -> None:
    h = BOX["h"]
    v = BOX["v"]
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
    print(f"{BOX['tl']}{topo}{BOX['tr']}")
    print(f"{v} {titulo:^{bloco}} {v}")
    print(f"{BOX['lm']}{topo}{BOX['rm']}")
    cab = [f"{'Situação':<{w_row}}"] + [f"{c:^{w_col}}" for c in colunas] + [
        f"{'Σ':>{w_tot}}"
    ]
    print(linha_celulas(cab))
    print(f"{BOX['lm']}{topo}{BOX['rm']}")
    grand = 0
    for r in linhas:
        tot_lin = sum(matriz.get((r, c), 0) for c in colunas)
        cels = [f"{r:<{w_row}}"] + [
            f"{matriz.get((r, c), 0):^{w_col}}" for c in colunas
        ] + [f"{tot_lin:>{w_tot}}"]
        print(linha_celulas(cels))
    print(f"{BOX['lm']}{topo}{BOX['rm']}")
    tot_cols: list[str] = [f"{'Total':<{w_row}}"]
    for c in colunas:
        tc = sum(matriz.get((r, c), 0) for r in linhas)
        grand += tc
        tot_cols.append(f"{tc:^{w_col}}")
    tot_cols.append(f"{grand:>{w_tot}}")
    print(linha_celulas(tot_cols))
    print(f"{BOX['bl']}{topo}{BOX['br']}")
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
        [(m, fmt_int(contagem_por_mes[m])) for m in meses],
    )


def imprimir_console(r: Relatorio) -> None:
    resumo: list[tuple[str, str]] = [
        ("Pessoas únicas (por nome)", fmt_int(r.total_pessoas)),
        (
            f"Concluíram o curso (≥ {PROGRESSO_COMPLETO:g}%)",
            fmt_int(r.completaram_curso),
        ),
    ]
    if r.linhas_sem_nome:
        resumo.append(
            ("Linhas ignoradas (sem nome)", fmt_int(r.linhas_sem_nome))
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
                fmt_int(r.nunca_logou),
            ),
            ("Logou e maior progresso = 0%", fmt_int(r.logou_sem_progresso)),
            (
                "Logou e já tem progresso > 0%",
                fmt_int(r.logou_com_progresso),
            ),
        ],
    )

    _imprimir_quadro(
        "Datas (consolidado por pessoa)",
        [
            (
                "Sem nenhuma data válida (login e atividade)",
                fmt_int(r.sem_data_contato),
            ),
            ("Referência para inatividade (hoje)", r.hoje.strftime("%d/%m/%Y")),
        ],
    )

    _imprimir_quadro(
        "Inatividade (último contato = mais recente entre login e atividade)",
        [
            (
                f"Parados: último login ou atividade há ≥ {d} dias",
                fmt_int(n),
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
        [(f"DDD {ddd}", fmt_int(n)) for ddd, n in r.ddd_top]
        + [("Sem DDD válido / sem telefone", fmt_int(r.sem_ddd))],
    )
