"""Modelos de dados do relatório."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime


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
