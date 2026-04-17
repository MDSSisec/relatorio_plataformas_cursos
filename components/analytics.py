"""Agregação do CSV e construção do objeto Relatorio."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from components.constants import (
    DIAS_SEM_CONTATO,
    DDD_PARA_UF,
    PROGRESSO_COMPLETO,
)
from components.models import AgregadoPessoa, Relatorio
from components.parsing import (
    extrair_ddd,
    faixa_dez_porcento,
    parse_data_hora_br,
    parse_progresso,
)

EXITO_TELEFONES_POR_NOME: dict[str, str] = {
    "luciene vaneide ramos lavôr": "(93) 9 9210-3330",
    "gabriel rodrigues da silva": "(61) 9 8140-3614",
    "josé fábio teixeira barbosa": "(85) 9 9636-4167",
    "ruan vidal silva": "(55) 9 9732-0101",
    "tayane pacheco nascimento": "(92) 9 9321-3433",
    "bruna de souza martins": "(21) 9 8098-4722",
    "alana alberta de matos": "(62) 9 9299-1397",
    "isaias costa neves": "(83) 9 9954-2558",
    "laura silva": "(64) 9 9662-3042",
    "samantha sthefany nunes da silva": "(92) 9 8604-0625",
}


def _nome_chave(nome: str) -> str:
    return " ".join((nome or "").strip().lower().split())


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
            p = parse_progresso(row.get("PROGRESSO"))
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
            dt_login = parse_data_hora_br(row.get("ULTIMO_LOGIN"))
            if dt_login and (agg.max_login is None or dt_login > agg.max_login):
                agg.max_login = dt_login
            if (row.get("ULTIMO_LOGIN") or "").strip():
                agg.teve_login_preenchido = True
            dt_at = parse_data_hora_br(row.get("ULTIMO_REGISTRO_DE_ATIVIDADE"))
            if dt_at and (agg.max_atividade is None or dt_at > agg.max_atividade):
                agg.max_atividade = dt_at
            ddd = extrair_ddd(row.get("TELEFONE"))
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
        faixa_dez_porcento(a.max_progresso) for a in por_nome.values()
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
        f = faixa_dez_porcento(a.max_progresso)
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
        if faixa_dez_porcento(a.max_progresso) == 80:
            contatos_faixa_80.append(
                (
                    nome,
                    a.email or "—",
                    a.telefone_contato or "—",
                )
            )

    concluintes_recentes: list[tuple[str, str, str, str]] = []
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
        telefone = EXITO_TELEFONES_POR_NOME.get(_nome_chave(nome), "—")
        concluintes_recentes.append(
            (nome, email, telefone, dt.strftime("%d/%m/%Y %H:%M"))
        )

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
