# Relatório de Progresso Educacional (GoKursos + Instituto Exito)

Projeto em Python para consolidar dados de progresso educacional e gerar um relatório HTML único com abas por origem de dados:

- `GoKursos`
- `Instituto Exito`

O resultado final é um painel visual em `index.html`, com tabelas, cruzamentos, gráficos e cards analíticos voltados para acompanhamento operacional.

---

## Visão Geral

Este repositório foi construído para transformar bases brutas de progresso em uma visualização executiva e navegável.

### Principais entregas

- Consolidação por pessoa (nome único)
- Distribuição por faixas de progresso (0% a 100%)
- Cruzamentos de situação vs progresso e situação vs carga/curso
- Métricas de login, atividade e inatividade
- Séries mensais (último login e última atividade)
- Blocos específicos por negócio:
  - **GoKursos:** card com pessoas na faixa de 80% (com expansão por botão)
  - **Instituto Exito:** card com os 10 concluintes mais recentes

---

## Arquitetura do Projeto

```text
python02/
├── components/                           # Módulos reutilizáveis (ver tabela abaixo)
│   ├── __init__.py
│   ├── analytics.py
│   ├── constants.py
│   ├── console_report.py
│   ├── exito_xlsx.py
│   ├── html_document.py
│   ├── html_fragment.py
│   ├── html_map.py
│   ├── html_utils.py
│   ├── html_widgets.py
│   ├── models.py
│   ├── parsing.py
│   └── report.css                        # Tema e layout do relatório HTML
├── GoKursos/
│   ├── script.py                         # Ponto de entrada: caminhos + chamadas ao pacote components
│   ├── progress_130426162242.csv       # Base GoKursos
│   └── br_ibge_uf.json                   # GeoJSON de UFs (opcional para mapa)
├── Exito/
│   ├── script.py                         # Conversor XLSX → CSV e disparo do script GoKursos
│   ├── *.xlsx                            # Planilhas de origem Exito
│   └── progress_instituto_exito.csv      # CSV normalizado gerado automaticamente
└── index.html                            # Relatório final (gerado)
```

---

## Pacote `components/`

A lógica de negócio, HTML e conversão da Exito ficam no diretório `components/`, importado pela raiz do repositório (`sys.path` é ajustado em `GoKursos/script.py` e `Exito/script.py`). O arquivo `components/__init__.py` reexporta a API principal para uso direto (`from components import analisar, ...`).

| Módulo | Função |
|--------|--------|
| `constants.py` | `PROGRESSO_COMPLETO`, `DIAS_SEM_CONTATO`, `DDD_PARA_UF`, `CODIGO_IBGE_PARA_SIGLA`, `BOX` (Unicode do console) |
| `models.py` | `AgregadoPessoa`, `Relatorio` |
| `parsing.py` | `parse_progresso`, `parse_data_hora_br`, `faixa_dez_porcento`, `extrair_ddd` |
| `analytics.py` | `analisar(path)` — lê o CSV, agrega por pessoa e devolve `Relatorio` |
| `console_report.py` | `imprimir_console` — resumo e tabelas no terminal |
| `html_utils.py` | `esc`, `fmt_int` |
| `html_widgets.py` | Tabelas e barras: `tabela_simples`, `tabela_cruzada`, `tabela_contatos_faixa_80`, `barras_horizontais`, `barras_verticais`, `rotulo_mes_pt` |
| `html_map.py` | Mapa SVG (choropleth) e blocos `html_bloco_mapa_visual`, `html_tabela_ddd` |
| `html_fragment.py` | `html_fragmento_relatorio`, `html_sem_csv_origem` — corpo HTML de cada aba |
| `html_document.py` | `escrever_html_abas(..., geojson_ufs_path=...)` — documento completo, abas e script; lê `report.css` do disco |
| `exito_xlsx.py` | Conversão Exito: `COLUNAS_DESTINO`, `converter_xlsx_exito_para_csv`, `xlsx_mais_recente`, leitura de XLSX (stdlib) |
| `report.css` | Variáveis de tema, layout, abas, gráficos, tabelas e responsividade |
| `__init__.py` | Reexporta a API principal (`analisar`, `Relatorio`, `escrever_html_abas`, etc.) |

**Dependência de arquivo:** `escrever_html_abas` exige `components/report.css` no mesmo diretório do pacote; sem esse arquivo a geração do HTML falha com erro explícito.

---

## Como Funciona

### 1) Pipeline GoKursos

O `GoKursos/script.py`:

1. Garante que a raiz do projeto esteja em `sys.path` e importa o pacote `components`
2. Lê os CSVs padronizados via `analisar`
3. Opcionalmente imprime o resumo no console (`imprimir_console`)
4. Gera `index.html` com abas (`escrever_html_abas`, passando o caminho do GeoJSON para o mapa)

### 2) Pipeline Exito

O `Exito/script.py`:

1. Localiza o `.xlsx` mais recente na pasta `Exito/`
2. Converte para `progress_instituto_exito.csv` com `components.exito_xlsx`
3. Executa o ponto de entrada GoKursos (`GoKursos/script.py`)

---

## Requisitos

- Python 3.10+ (recomendado)
- Sem dependências externas obrigatórias (usa bibliotecas padrão)

---

## Execução

### Fluxo completo (recomendado)

Executa conversão da Exito + geração do relatório final:

```bash
python3 Exito/script.py
```

### Fluxo somente GoKursos

Se quiser regenerar apenas com os CSVs já prontos:

```bash
python3 GoKursos/script.py
```

Após a execução, o relatório estará em:

- `index.html`

---

## Formato de Dados Esperado

### CSV padrão utilizado pelo motor

Colunas obrigatórias:

- `NOME`
- `EMAIL`
- `PROGRESSO`
- `SITUACAO`
- `CARGA_HORARIA`
- `ULTIMO_LOGIN`
- `ULTIMO_REGISTRO_DE_ATIVIDADE`
- `TELEFONE`

### Conversão Exito (XLSX -> CSV)

A planilha da Exito é convertida para o padrão acima com base em colunas como:

- `ALUNO`
- `E-MAIL`
- `PROGRESSO`
- `CURSO`
- `DATA DE INÍCIO`
- `DATA DE CONCLUSÃO`

---

## Recursos de Visualização

### Aba GoKursos

- KPIs principais
- Tabelas e cruzamentos
- Gráficos verticais de faixas e séries mensais
- Card: **Pessoas na faixa de 80%**
  - Exibe 3 primeiras linhas
  - Botão "Mostrar mais / Mostrar menos"
  - Layout responsivo para mobile

### Aba Instituto Exito

- KPIs principais
- Tabelas e cruzamentos adaptados
- Card: **Últimos 10 concluintes (mais recentes)**
  - Colunas: Nome, E-mail, Data

---

## Responsividade e Tema

- Interface com suporte a tema claro/escuro baseado no sistema (`prefers-color-scheme`)
- Componentes responsivos para telas menores
- Card de contatos na faixa 80% otimizado para mobile (itens em bloco vertical)

---

## Publicação no GitHub Pages (opcional)

Se você hospedar o `index.html` no GitHub Pages:

1. Suba o repositório para o GitHub
2. Habilite Pages em **Settings > Pages**
3. Selecione a branch/pasta de publicação
4. Compartilhe o link público gerado

---

## Boas Práticas de Atualização

1. Coloque novos arquivos de entrada (`.csv` ou `.xlsx`) nas pastas corretas
2. Execute `python3 Exito/script.py` para atualizar tudo
3. Revise o `index.html`
4. Faça commit das mudanças relevantes

---

## Observações

- O relatório é estático (HTML), sem backend.
- Os números de telefone podem não existir em algumas fontes (Exito, por exemplo).
- Quando o GeoJSON não está disponível, blocos dependentes de mapa podem ser omitidos conforme layout da aba.

---

## Licença

Defina aqui a licença desejada para o projeto (ex.: MIT, Apache-2.0, Proprietária).

## Desenvolvedores

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/DevLucasFontoura" target="_blank">
        <img src="https://github.com/DevLucasFontoura.png" width="120" alt="Lucas Fontoura" style="border-radius: 50%"/><br/>
        <b>Lucas Fontoura</b>
      </a><br/>
      <sub>Desenvolvedor · <a href="https://github.com/DevLucasFontoura">@DevLucasFontoura</a></sub>
    </td>
  </tr>
</table>