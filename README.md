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
├── GoKursos/
│   ├── script.py                         # Motor principal: leitura, consolidação e geração do HTML
│   ├── progress_130426162242.csv         # Base GoKursos
│   └── br_ibge_uf.json                   # GeoJSON de UFs (opcional para mapa)
├── Exito/
│   ├── script.py                         # Conversor XLSX -> CSV padrão e executor do motor principal
│   ├── *.xlsx                            # Planilhas de origem Exito
│   └── progress_instituto_exito.csv      # CSV normalizado gerado automaticamente
└── index.html                            # Relatório final (gerado)
```

---

## Como Funciona

### 1) Pipeline GoKursos

O `GoKursos/script.py`:

1. Lê os CSVs padronizados
2. Consolida dados por pessoa
3. Calcula métricas e cruzamentos
4. Gera `index.html` com abas

### 2) Pipeline Exito

O `Exito/script.py`:

1. Localiza o `.xlsx` mais recente na pasta `Exito/`
2. Converte para `progress_instituto_exito.csv` no formato esperado
3. Executa o motor principal (`GoKursos/script.py`)

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