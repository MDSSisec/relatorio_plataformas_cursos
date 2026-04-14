"""Componentes HTML reutilizáveis: tabelas e gráficos de barras."""

from __future__ import annotations

from components.html_utils import esc, fmt_int


def tabela_simples(cabecalhos: list[str], linhas: list[list[str]]) -> str:
    th = "".join(f"<th>{esc(h)}</th>" for h in cabecalhos)
    body = ""
    for row in linhas:
        body += "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>"
    return (
        f'<table class="data"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'
    )


def tabela_contatos_faixa_80(linhas: list[list[str]]) -> str:
    cabecalhos = ["Nome", "E-mail", "Telefone"]
    th = "".join(f"<th>{esc(h)}</th>" for h in cabecalhos)
    body = ""
    for i, row in enumerate(linhas):
        nome = row[0] if len(row) > 0 else "—"
        email = row[1] if len(row) > 1 else "—"
        telefone = row[2] if len(row) > 2 else "—"
        extra_cls = " contatos-80-row-extra" if i >= 3 else ""
        body += (
            f'<tr class="{extra_cls.strip()}">'
            f'<td data-label="Nome">{esc(nome)}</td>'
            f'<td data-label="E-mail">{esc(email)}</td>'
            f'<td data-label="Telefone">{esc(telefone)}</td>'
            "</tr>"
        )
    tabela = (
        f'<table class="data contatos-80"><thead><tr>{th}</tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )
    if len(linhas) <= 3:
        return tabela
    botao = (
        '<button type="button" class="contatos-80-toggle" aria-expanded="false">'
        "Mostrar mais"
        "</button>"
    )
    return tabela + botao


def tabela_cruzada(
    titulo_secao: str,
    linhas_rotulo: list[str],
    colunas: list[str],
    matriz: dict[tuple[str, str], int],
    rotulo_linha: str = "Situação",
) -> str:
    th = f"<th>{esc(rotulo_linha)}</th>" + "".join(
        f"<th>{esc(c)}</th>" for c in colunas
    )
    th += '<th class="num">Total</th>'
    body = ""
    for r in linhas_rotulo:
        tot = sum(matriz.get((r, c), 0) for c in colunas)
        cells = "".join(
            f'<td class="num">{matriz.get((r, c), 0)}</td>' for c in colunas
        )
        body += (
            f'<tr><td>{esc(r)}</td>{cells}<td class="num"><strong>{tot}</strong></td></tr>'
        )
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
        f'<section class="block"><h2>{esc(titulo_secao)}</h2>'
        f'<div class="scroll-x"><table class="data cross">'
        f"<thead><tr>{th}</tr></thead><tbody>{body}</tbody>"
        f"<tfoot><tr>{foot}</tr></tfoot></table></div></section>"
    )


def barras_horizontais(titulo: str, itens: list[tuple[str, int]], cor: str) -> str:
    if not itens:
        return (
            f'<section class="block"><h2>{esc(titulo)}</h2>'
            f'<p class="muted">Sem dados.</p></section>'
        )
    mx = max(n for _, n in itens) or 1
    rows = ""
    for label, n in itens:
        pct = 100.0 * n / mx
        rows += (
            f'<div class="bar-row"><span class="bar-label">{esc(label)}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%;background:{cor}"></div></div>'
            f'<span class="bar-val">{fmt_int(n)}</span></div>'
        )
    return f'<section class="block"><h2>{esc(titulo)}</h2><div class="bars">{rows}</div></section>'


def barras_verticais(titulo: str, itens: list[tuple[str, int]], cor: str) -> str:
    if not itens:
        return (
            f'<section class="block"><h2>{esc(titulo)}</h2>'
            f'<p class="muted">Sem dados.</p></section>'
        )
    mx = max(n for _, n in itens) or 1
    cols = ""
    for label, n in itens:
        pct = 100.0 * n / mx
        cols += (
            '<div class="vbar-col">'
            f'<div class="vbar-val">{fmt_int(n)}</div>'
            f'<div class="vbar-track"><div class="vbar-fill" style="height:{pct:.1f}%;background:{cor}"></div></div>'
            f'<div class="vbar-label">{esc(label)}</div>'
            "</div>"
        )
    return f'<section class="block"><h2>{esc(titulo)}</h2><div class="vbars">{cols}</div></section>'


def rotulo_mes_pt(chave: str) -> str:
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
