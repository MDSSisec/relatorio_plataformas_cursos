"""Montagem do HTML de um painel de relatório (uma aba)."""

from __future__ import annotations

from pathlib import Path

from components.constants import PROGRESSO_COMPLETO
from components.html_map import html_bloco_mapa_visual, html_tabela_ddd
from components.html_utils import esc, fmt_int
from components.html_widgets import (
    barras_verticais,
    rotulo_mes_pt,
    tabela_contatos_faixa_80,
    tabela_cruzada,
    tabela_simples,
)
from components.models import Relatorio


def html_fragmento_relatorio(
    r: Relatorio,
    *,
    exito_layout: bool = False,
    geojson_ufs_path: Path,
) -> str:
    faixas = sorted(r.por_faixa.keys())
    linhas_faixa: list[list[str]] = []
    for f in faixas:
        q = r.por_faixa[f]
        p = (100.0 * q / r.total_pessoas) if r.total_pessoas else 0.0
        linhas_faixa.append([f"{f}%", fmt_int(q), f"{p:.1f}%"])
    linhas_faixa.append(["Total", fmt_int(r.total_pessoas), "100,0%"])

    kpi = f"""
    <div class="kpi-deck">
      <div class="kpis">
        <div class="kpi"><span class="kpi-val">{esc(fmt_int(r.total_pessoas))}</span><span class="kpi-lbl">Pessoas únicas</span></div>
        <div class="kpi"><span class="kpi-val">{esc(fmt_int(r.completaram_curso))}</span><span class="kpi-lbl">Concluíram (≥ {PROGRESSO_COMPLETO:g}%)</span></div>
        <div class="kpi"><span class="kpi-val">{esc(fmt_int(r.nunca_logou))}</span><span class="kpi-lbl">Nunca logou</span></div>
        <div class="kpi"><span class="kpi-val">{esc(fmt_int(r.parados_dias[-1][1] if r.parados_dias else 0))}</span><span class="kpi-lbl">Parados ≥ {r.parados_dias[-1][0] if r.parados_dias else 90} dias</span></div>
      </div>
    </div>
    """

    login_rows = [
        ["Nunca logou (ULTIMO_LOGIN vazio em todas as linhas)", fmt_int(r.nunca_logou)],
        ["Logou e maior progresso = 0%", fmt_int(r.logou_sem_progresso)],
        ["Logou e já tem progresso > 0%", fmt_int(r.logou_com_progresso)],
    ]
    data_rows = [
        ["Sem data válida (login e atividade)", fmt_int(r.sem_data_contato)],
        ["Referência (hoje)", r.hoje.strftime("%d/%m/%Y")],
    ]
    inat_rows = [
        [f"Parados ≥ {d} dias (último login ou atividade)", fmt_int(n)]
        for d, n in r.parados_dias
    ]
    mat_carga_situacao = {
        (carga, situacao): n
        for (situacao, carga), n in r.mat_situacao_carga.items()
    }
    card_carga = (
        tabela_cruzada(
            "Carga horária (h) × situação",
            r.cols_carga,
            r.situacoes,
            mat_carga_situacao,
            rotulo_linha="Turmas",
        )
        if exito_layout
        else tabela_cruzada(
            "Situação × carga horária (h)",
            r.situacoes,
            r.cols_carga,
            r.mat_situacao_carga,
        )
    )
    bloco_carga_inicio = "" if exito_layout else card_carga
    bloco_carga_final = card_carga if exito_layout else ""
    card_situacao_faixa = tabela_cruzada(
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
          <h2>Pessoas na faixa de 80% ({fmt_int(len(r.contatos_faixa_80))})</h2>
          {tabela_contatos_faixa_80(linhas_80)}
        </section>
        """
    bloco_concluintes_recentes = ""
    if exito_layout:
        linhas_concluintes = [list(item) for item in r.concluintes_recentes]
        bloco_concluintes_recentes = f"""
        <section class="block">
          <h2>Últimos 10 concluintes (mais recentes)</h2>
          {tabela_simples(["Nome", "E-mail", "Data"], linhas_concluintes)}
        </section>
        """
    bloco_mapa = (
        ""
        if exito_layout
        else f"""
    <div class="colunas-2">
      {html_bloco_mapa_visual(r, geojson_ufs_path)}
      <div class="coluna-stack">
        {html_tabela_ddd(r)}
      </div>
    </div>
    """
    )

    return f"""
    <header class="cabecalho-relatorio">
      <h1>Relatório de progresso educacional</h1>
      <p class="meta-linha">Arquivo: {esc(r.arquivo_csv)} · Gerado em {esc(r.gerado_em.strftime("%d/%m/%Y %H:%M"))} · Critério de conclusão: ≥ {PROGRESSO_COMPLETO:g}%</p>
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
        {tabela_simples(["Faixa", "Pessoas", "% do total"], linhas_faixa)}
      </section>
      {barras_verticais("Faixas de progresso (visual)", [(f"{f}%", r.por_faixa[f]) for f in faixas], "var(--accent)")}
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
        {tabela_simples(["Indicador", "Pessoas"], login_rows)}
      </section>
      <section class="block">
        <h2>Datas e inatividade</h2>
        {tabela_simples(["Indicador", "Valor"], data_rows + inat_rows)}
      </section>
    </div>

    <div class="colunas-2">
      {barras_verticais("Pessoas por mês do último login", [(rotulo_mes_pt(m), n) for m, n in r.serie_login_mes], "var(--accent2)")}
      {barras_verticais("Pessoas por mês da última atividade", [(rotulo_mes_pt(m), n) for m, n in r.serie_atividade_mes], "var(--warn)")}
    </div>

    {bloco_mapa}
    {bloco_situacao_faixa_final}
    {bloco_carga_final}
    """


def html_sem_csv_origem(rotulo_origem: str, caminho_csv: Path) -> str:
    nome = caminho_csv.name
    return f"""
    <header class="cabecalho-relatorio">
      <h1>Relatório de progresso educacional</h1>
      <p class="meta-linha">Origem: {esc(rotulo_origem)} · CSV esperado: {esc(nome)} · Critério de conclusão: ≥ {PROGRESSO_COMPLETO:g}%</p>
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
      <p class="muted">O arquivo <strong>{esc(nome)}</strong> não foi encontrado na pasta do script.</p>
      <p>Coloque um CSV com o mesmo formato das colunas (NOME, PROGRESSO, SITUACAO, CARGA_HORARIA, ULTIMO_LOGIN, ULTIMO_REGISTRO_DE_ATIVIDADE, TELEFONE) e execute novamente:</p>
      <p><code class="cmd-hint">python3 script.py</code></p>
    </section>
    """
