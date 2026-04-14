"""Documento HTML completo com abas, estilos e script."""

from __future__ import annotations

from pathlib import Path

from components.html_fragment import html_fragmento_relatorio, html_sem_csv_origem
from components.html_utils import esc
from components.models import Relatorio

_CSS_PATH = Path(__file__).resolve().parent / "report.css"

_TAB_SCRIPT = """
(function () {
  var tabs = document.querySelectorAll(".tab-bar [role=tab]");
  var panels = document.querySelectorAll(".tab-panel");
  function show(slug) {
    tabs.forEach(function (btn) {
      var on = btn.getAttribute("data-panel") === slug;
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    panels.forEach(function (p) {
      p.classList.toggle("is-active", p.id === "panel-" + slug);
    });
  }
  tabs.forEach(function (btn) {
    btn.addEventListener("click", function () {
      show(btn.getAttribute("data-panel"));
    });
  });

  var toggles = document.querySelectorAll(".contatos-80-toggle");
  toggles.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var sec = btn.closest(".block");
      if (!sec) return;
      var extras = sec.querySelectorAll(".contatos-80-row-extra");
      var open = btn.getAttribute("aria-expanded") === "true";
      extras.forEach(function (tr) {
        tr.style.display = open ? "none" : "";
      });
      btn.setAttribute("aria-expanded", open ? "false" : "true");
      btn.textContent = open ? "Mostrar mais" : "Mostrar menos";
    });
  });

  var extrasInit = document.querySelectorAll(".contatos-80-row-extra");
  extrasInit.forEach(function (tr) {
    tr.style.display = "none";
  });
})();
"""


def _load_report_css() -> str:
    if not _CSS_PATH.is_file():
        raise FileNotFoundError(
            f"CSS do relatório não encontrado: {_CSS_PATH}. "
            "Mantenha components/report.css junto ao pacote."
        )
    return _CSS_PATH.read_text(encoding="utf-8")


def escrever_html_abas(
    abas: list[tuple[str, str, Relatorio | None, Path]],
    destino: Path,
    *,
    geojson_ufs_path: Path,
) -> None:
    """Gera HTML com abas. Cada item: (id_slug, rótulo, relatório ou None, path do CSV esperado)."""
    botoes = []
    paineis = []
    for i, (slug, label, rel, csv_esperado) in enumerate(abas):
        panel_id = f"panel-{slug}"
        sel = "true" if i == 0 else "false"
        botoes.append(
            f'<button type="button" class="tab-btn" role="tab" id="tab-{slug}" '
            f'aria-controls="{panel_id}" aria-selected="{sel}" data-panel="{slug}">{esc(label)}</button>'
        )
        active = " is-active" if i == 0 else ""
        inner = (
            html_fragmento_relatorio(
                rel,
                exito_layout=(slug == "instituto-exito"),
                geojson_ufs_path=geojson_ufs_path,
            )
            if rel is not None
            else html_sem_csv_origem(label, csv_esperado)
        )
        paineis.append(
            f'<div class="tab-panel{active}" role="tabpanel" id="{panel_id}" '
            f'aria-labelledby="tab-{slug}" tabindex="0">{inner}</div>'
        )

    tabs_html = '<div class="tab-bar" role="tablist">' + "".join(botoes) + "</div>"
    panels_html = "".join(paineis)
    css = _load_report_css()

    doc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Relatório de progresso — GoKursos / Instituto Exito</title>
  <style>
{css}
  </style>
</head>
<body>
  <div class="wrap">
    {tabs_html}
    {panels_html}
  </div>
  <script>
  {_TAB_SCRIPT}
  </script>
</body>
</html>
"""

    destino.write_text(doc, encoding="utf-8")
