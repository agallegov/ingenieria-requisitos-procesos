#!/usr/bin/env python3
"""Compila la carpeta especificaciones/: la documentación completa de la app.

Regenera el spec del mapa y el de cada actividad con planos, agrupados por
área, más un índice (README.md). Se regenera ENTERA en cada ejecución: no se
edita a mano. Solo biblioteca estándar.

Uso: python3 compilar.py --mapa <ruta/planos.json> [--salida <dir>]
(por defecto escribe en especificaciones/ junto al planos.json del mapa)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))


def slug(texto):
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "area"


def generar(datos, salida):
    r = subprocess.run([sys.executable, os.path.join(BASE, "generar_spec.py"),
                        "--datos", datos, "--salida", salida],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("Fallo generando %s:\n%s%s" % (salida, r.stdout, r.stderr))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapa", required=True, help="El planos.json del mapa (o de un proyecto de una sola actividad)")
    ap.add_argument("--salida", help="Carpeta destino (defecto: especificaciones/ junto al mapa)")
    args = ap.parse_args()

    ruta_mapa = os.path.abspath(args.mapa)
    try:
        with open(ruta_mapa, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("No pude leer el mapa: %s" % e)

    raiz = os.path.dirname(ruta_mapa)
    out = os.path.abspath(args.salida or os.path.join(raiz, "especificaciones"))
    os.makedirs(out, exist_ok=True)

    # Se regenera entera: fuera los .md de compilaciones anteriores.
    for dirpath, _, ficheros in os.walk(out):
        for f in ficheros:
            if f.endswith(".md"):
                os.remove(os.path.join(dirpath, f))

    idx = []
    idx.append("# %s: especificaciones" % d.get("titulo", "Proyecto"))
    idx.append("")
    if d.get("descripcion"):
        idx.append(d["descripcion"])
        idx.append("")
    if (d.get("contrato") or {}).get("frase"):
        idx.append("> %s" % d["contrato"]["frase"])
        idx.append("")
    idx.append("Documentación generada desde los planos (no editar a mano; se "
               "regenera con `visor/compilar.py`).")
    idx.append("")

    actividades = d.get("actividades", [])
    if actividades:
        generar(ruta_mapa, os.path.join(out, "00-el-mapa.md"))
        idx.append("- [El mapa de la aplicación](00-el-mapa.md)")
        idx.append("")
        con, sin = 0, 0
        areas = []
        for a in actividades:
            if a["area"] not in areas:
                areas.append(a["area"])
        for area in areas:
            idx.append("## %s" % area)
            idx.append("")
            for a in [x for x in actividades if x["area"] == area]:
                pj = os.path.join(raiz, "actividades", a["id"], "planos.json")
                estado = a.get("estado", "sin empezar")
                if os.path.isfile(pj):
                    destino_rel = os.path.join(slug(area), a["id"] + ".md")
                    destino = os.path.join(out, destino_rel)
                    os.makedirs(os.path.dirname(destino), exist_ok=True)
                    generar(pj, destino)
                    idx.append("- [%s](%s) · %s" % (a["nombre"], destino_rel.replace(os.sep, "/"), estado))
                    con += 1
                else:
                    idx.append("- %s · %s · (aún sin planos)" % (a["nombre"], estado))
                    sin += 1
            idx.append("")
        resumen = "%d actividades con especificación, %d aún sin planos." % (con, sin)
    else:
        generar(ruta_mapa, os.path.join(out, "especificacion.md"))
        idx.append("- [Especificación completa](especificacion.md)")
        idx.append("")
        resumen = "Proyecto de una sola actividad."

    idx.append("---")
    idx.append("")
    idx.append(resumen)
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx) + "\n")
    print("Especificaciones compiladas en %s (%s)" % (out, resumen))


if __name__ == "__main__":
    main()
