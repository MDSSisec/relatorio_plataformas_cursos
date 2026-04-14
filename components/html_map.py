"""Mapa SVG (choropleth) e blocos HTML relacionados a DDD/UF."""

from __future__ import annotations

import html
import json
from pathlib import Path

from components.constants import CODIGO_IBGE_PARA_SIGLA, DDD_PARA_UF
from components.html_utils import fmt_int
from components.html_widgets import tabela_simples
from components.models import Relatorio


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


def _maior_anel(
    rings: list[list[tuple[float, float]]],
) -> list[tuple[float, float]] | None:
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


def gerar_svg_mapa_brasil(por_uf: dict[str, int], caminho: Path) -> str | None:
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
        title = f"{sigla}: {fmt_int(n)} pessoas"
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
        txt_n = fmt_int(n)
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


def html_bloco_mapa_visual(r: Relatorio, geojson_ufs_path: Path) -> str:
    """Coluna esquerda: apenas mapa + legenda (SVG estático)."""
    svg = gerar_svg_mapa_brasil(r.por_uf, geojson_ufs_path)
    extra = ""
    if r.ddd_nao_mapeado:
        extra = (
            f'<p class="muted map-foot">DDD sem correspondência na tabela de UFs: '
            f"<strong>{fmt_int(r.ddd_nao_mapeado)}</strong> pessoas (não entram no mapa).</p>"
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


def html_tabela_ddd(r: Relatorio) -> str:
    linhas: list[list[str]] = []
    for ddd, n in r.ddd_top:
        uf = DDD_PARA_UF.get(ddd)
        linhas.append([f"DDD {ddd}", uf if uf else "—", fmt_int(n)])
    linhas.append(["Sem DDD válido / sem telefone", "—", fmt_int(r.sem_ddd)])
    return f"""
    <section class="block">
      <h2>Tabela DDD (detalhe)</h2>
      {tabela_simples(["Região (DDD)", "UF", "Pessoas"], linhas)}
    </section>
    """
