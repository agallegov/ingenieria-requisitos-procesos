#!/usr/bin/env python3
"""Genera spec.md desde planos.json. Proyección de TEXTO de los planos:
determinista, misma estructura siempre. No se edita el spec a mano; se
edita planos.json y se regenera.

Uso: python generar_spec.py --datos <ruta/planos.json> [--salida <ruta/spec.md>]
(por defecto escribe spec.md junto al planos.json)
"""

import argparse
import json
import os
import sys

L = []  # líneas del documento


def p(texto=""):
    L.append(texto)


def celda(x):
    return " ".join(str(x).split()).replace("|", "\\|")


def tabla_md(columnas, filas):
    p("| " + " | ".join(celda(c) for c in columnas) + " |")
    p("|" + "---|" * len(columnas))
    for f in filas:
        p("| " + " | ".join(celda(c) for c in f) + " |")
    p()


ETIQUETAS = {"humano": "persona", "automatizado": "automático", "externo": "tercero externo"}


def paso_texto(paso, sangria):
    pre = "    " * sangria
    if paso["tipo"] == "decision":
        marca = "⚠ Excepción" if paso["clase"] == "excepcion" else "⚑ Regla"
        quien = (" (la evalúa %s)" % paso["quien"]) if paso.get("quien") else ""
        p("%s- %s%s: %s" % (pre, marca, quien, paso["condicion"]))
        ramas = paso.get("ramas") or ([paso["rama"]] if paso.get("rama") else [])
        for r in ramas:
            p("%s    - si %s:" % (pre, r["etiqueta"]))
            for x in r["pasos"]:
                paso_texto(x, sangria + 2)
            p("%s        - %s" % (pre, "aquí termina este camino" if r.get("termina") else "…y vuelve al flujo"))
        if paso.get("sigue"):
            p("%s    - camino normal: %s" % (pre, paso["sigue"]))
    else:
        quien = (" · %s" % paso["quien"]) if paso.get("quien") else ""
        p("%s- [%s] %s%s" % (pre, ETIQUETAS.get(paso["tipo"], paso["tipo"]), paso["texto"], quien))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True)
    ap.add_argument("--salida")
    args = ap.parse_args()

    try:
        with open(args.datos, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("No pude leer los planos: %s" % e)
    if d.get("version") != 3 or not d.get("titulo"):
        sys.exit("planos.json debe tener version: 3 y titulo.")
    d["titulo"] = " ".join(str(d["titulo"]).split())
    no_aplican = set((d.get("definicion") or {}).get("bloques_no_aplican", []))

    def ausencia(bloque, pendiente="(Pendiente.)"):
        p("(No aplica a este proyecto.)" if bloque in no_aplican else pendiente)

    salida = args.salida or os.path.join(os.path.dirname(os.path.abspath(args.datos)), "spec.md")

    p("# Planificación: %s" % d["titulo"])
    p()
    p("Proyecto `%s`. Generado desde `planos.json` (la fuente de verdad): no editar a mano." % d.get("proyecto", "?"))
    p()

    # ---- Definición: estado, supuestos, riesgos ----
    if d.get("definicion"):
        definicion = d["definicion"]
        p("**Estado del diseño:** %s · **modo:** %s." % (
            definicion.get("estado", "borrador"),
            definicion.get("modo", "sin declarar"),
        ))
        p()
    supuestos = (d.get("definicion") or {}).get("supuestos", [])
    if supuestos:
        p("Supuestos que el usuario debe revisar:")
        for supuesto in supuestos:
            p("- **%s · %s:** %s" % (
                supuesto.get("id", "supuesto"),
                supuesto.get("estado", "propuesto"),
                supuesto.get("texto", ""),
            ))
        p()

    riesgos = (d.get("definicion") or {}).get("riesgos", [])
    if riesgos:
        p("Riesgos identificados:")
        for riesgo in riesgos:
            p("- **%s** [impacto: %s]: %s" % (
                riesgo.get("id", "Riesgo"),
                riesgo.get("impacto", ""),
                riesgo.get("descripcion", ""),
            ))
            if riesgo.get("mitigacion"):
                p("  - Mitigación: %s" % riesgo["mitigacion"])
        p()

    # ---- Propósito ----
    p("## 1. Propósito")
    p()
    if d.get("descripcion"):
        p(d["descripcion"])
        p()
    c = d.get("contrato") or {}
    p(c.get("frase") or "(Pendiente: aún sin frase de contrato.)")
    exito = c.get("exito")
    if exito:
        p()
        p("Criterios de éxito:")
        for x in (exito if isinstance(exito, list) else [exito]):
            p("- %s" % x)
    p()

    # ---- Actores y vocabulario ----
    p("## 2. Actores y vocabulario")
    p()
    for a in d.get("actores", []):
        p("- **%s**%s" % (a["nombre"], (": %s" % a["rol"]) if a.get("rol") else ""))
    if d.get("glosario"):
        p()
        for v in d["glosario"]:
            p("- \"%s\": %s" % (v["termino"], v["significado"]))
    if not d.get("actores") and not d.get("glosario"):
        ausencia("actores")
    p()

    # ---- Estructura organizativa ----
    if d.get("estructura_organizativa"):
        p("## 3. Estructura organizativa")
        p()
        for u in d["estructura_organizativa"]:
            ubi = u.get("ubicacion", {})
            ubi_str = ", ".join(v for v in [ubi.get("pais"), ubi.get("ciudad")] if v)
            reporta = " (reporta a: %s)" % u.get("reporta_a", "") if u.get("reporta_a") else ""
            p("- **%s** (`%s`) — %s, %s%s" % (
                u["nombre"], u["id"], u["tipo"], ubi_str, reporta
            ))
        p()

    # ---- Flujos de proceso ----
    p("## 4. Flujos de proceso")
    p()
    p("La versión gráfica vive en el visor local del paquete (visor/servir.py).")
    p()
    flujos = sorted(d.get("flujos", []), key=lambda f: 0 if f.get("momento") == "futuro" else 1)
    for f in flujos:
        p("### %s [%s]" % (
            f["titulo"],
            "con el nuevo proceso" if f["momento"] == "futuro" else "actual",
        ))
        if f.get("descripcion"):
            p()
            p(f["descripcion"])
        p()
        for paso in f["pasos"]:
            paso_texto(paso, 0)
        p()
    if not d.get("flujos"):
        ausencia("flujos")
        p()

    # ---- Plan de acción ----
    p("## 5. Plan de acción")
    p()
    acciones = d.get("acciones", [])
    if acciones:
        p("| # | Acción | Responsable | Fecha prevista | Entregable | Avance |")
        p("|---|----------|-------------|----------------|------------|--------|")
        for i, acc in enumerate(acciones, 1):
            avance = acc.get("avance", {}).get("estado", "pendiente") if isinstance(acc.get("avance"), dict) else "pendiente"
            entregable = acc.get("entregable", "")
            p("| %d | **%s** | %s | %s | %s | %s |" % (
                i, acc["nombre"], acc.get("responsable", ""),
                acc.get("fecha_prevista", ""), entregable, avance,
            ))
        p()

        # Secuencia
        secuencia_ids = [a["id"] for a in acciones]
        if len(secuencia_ids) > 1:
            p("**Secuencia:** %s" % " → ".join(secuencia_ids))
            p()

        # Detalles por acción
        for acc in acciones:
            p("### %s (`%s`)" % (acc["nombre"], acc["id"]))
            p()
            if acc.get("descripcion"):
                p(acc["descripcion"])
                p()
            p("- Responsable: **%s**" % acc.get("responsable", ""))
            p("- Entregable: %s" % acc.get("entregable", ""))
            if acc.get("fecha_prevista"):
                p("- Fecha prevista: %s" % acc["fecha_prevista"])
            avance = acc.get("avance", {})
            if isinstance(avance, dict) and avance:
                p("- Estado: **%s**" % avance.get("estado", "pendiente"))
                if avance.get("completado_el"):
                    p("- Completado el: %s" % avance["completado_el"])
                if avance.get("observaciones"):
                    p("- Observaciones: %s" % avance["observaciones"])
            p()
    else:
        ausencia("acciones")
        p()

    # ---- Entregables ----
    p("## 6. Entregables")
    p()
    entregables = d.get("entregables", [])
    if entregables:
        p("| # | Entregable | Tipo | Acciones | Fecha prevista | Avance |")
        p("|---|-----------|------|----------|----------------|--------|")
        for i, ent in enumerate(entregables, 1):
            avance = ent.get("avance", {}).get("estado", "pendiente") if isinstance(ent.get("avance"), dict) else "pendiente"
            p("| %d | **%s** | %s | %s | %s | %s |" % (
                i, ent["nombre"], ent.get("tipo", ""),
                ", ".join(ent.get("acciones", [])), ent.get("fecha_prevista", ""), avance,
            ))
        p()

        for ent in entregables:
            p("### %s (`%s`)" % (ent["nombre"], ent["id"]))
            p()
            if ent.get("descripcion"):
                p(ent["descripcion"])
                p()
            p("- Tipo: **%s**" % ent.get("tipo", ""))
            p("- Acciones productoras: %s" % ", ".join(ent.get("acciones", [])))
            if ent.get("fecha_prevista"):
                p("- Fecha prevista: %s" % ent["fecha_prevista"])
            if ent.get("entregado_el"):
                p("- Entregado el: %s" % ent["entregado_el"])
            criterios = ent.get("criterios_aprobacion", [])
            if criterios:
                p()
                p("**Criterios de aprobación:**")
                p()
                for c in criterios:
                    p("- **%s**: %s" % (c.get("id", ""), c.get("condicion", "")))
            p()
    else:
        ausencia("entregables")
        p()

    # ---- Cumplimiento ----
    p("## 7. Cumplimiento legal, fiscal y laboral")
    p()
    cumplimiento = d.get("cumplimiento", [])
    if cumplimiento:
        for c in cumplimiento:
            p("### %s" % c.get("jurisdiccion", "Sin jurisdicción"))
            p()
            for categoria in ("laboral", "fiscal", "licencias"):
                items = c.get(categoria, [])
                if not items:
                    continue
                etiqueta = {"laboral": "Laboral", "fiscal": "Fiscal", "licencias": "Licencias"}[categoria]
                p("#### %s" % etiqueta)
                p()
                tabla_md(
                    ["ID", "Requisito", "Plazo", "Responsable", "Estado"],
                    [["%s-%d" % (categoria[:3].upper(), j + 1),
                      req.get("requisito", ""),
                      req.get("plazo", ""),
                      req.get("responsable", ""),
                      req.get("estado", "")] for j, req in enumerate(items)]
                )
            p()
    else:
        ausencia("cumplimiento")
        p()

    # ---- Distribución ----
    p("## 8. Distribución y canales")
    p()
    dist = d.get("distribucion") or {}
    if dist:
        p("Canales de distribución y alcance del proyecto:")
        p()
        for canal in dist.get("canales", []):
            p("- **%s**: %s" % (canal.get("nombre", ""), canal.get("descripcion", "")))
        if dist.get("alcance_geo"):
            p("- Alcance geográfico: %s" % ", ".join(dist["alcance_geo"]))
        p()
    else:
        ausencia("distribucion")
        p()

    # ---- Presupuesto ----
    p("## 9. Presupuesto")
    p()
    pres = d.get("presupuesto") or {}
    if pres:
        moneda = pres.get("moneda", "EUR")
        p("Moneda: **%s**" % moneda)
        p()
        tabla_md(
            ["Ítem", "Categoría", "Importe", "Periodicidad", "Responsable"],
            [[item.get("nombre", ""),
              item.get("categoria", ""),
              "%s %s" % (item.get("importe_estimado", ""), moneda),
              item.get("periodicidad", ""),
              item.get("responsable", "")] for item in pres.get("items", [])]
        )
        p("**Total estimado: %s %s**" % (pres.get("total_estimado", 0), moneda))
        p()
    else:
        ausencia("presupuesto")
        p()

    # ---- Proveedores ----
    if d.get("proveedores"):
        p("## 10. Proveedores y colaboradores externos")
        p()
        tabla_md(
            ["ID", "Nombre", "Servicio", "Tipo", "Coste/Periodicidad"],
            [[p.get("id", ""),
              p.get("nombre", ""),
              p.get("servicio", ""),
              p.get("tipo", ""),
              "%s %s" % (p.get("coste_estimado", ""), p.get("periodicidad", ""))] for p in d["proveedores"]]
        )
        p()

    # ---- Métricas ----
    if d.get("metricas"):
        p("## 11. Métricas del negocio")
        p()
        for m in d["metricas"]:
            p("- **%s**: %s" % (m["que"], m["cuanto"]))
        p()

    # ---- Calidad ----
    p("## 12. Calidad")
    p()
    for q in d.get("calidad", []):
        p("- **%s**: %s" % (q["id"], q["criterio"]))
    if not d.get("calidad"):
        ausencia("calidad")
    p()

    # ---- Datos ----
    if d.get("datos"):
        p("## 13. Datos gestionados")
        p()
        tabla_md(["Cosa", "Qué se guarda", "Origen"],
                 [[x["cosa"], ", ".join(x.get("guarda", [])), x.get("origen", "")] for x in d["datos"]])
        p()

    # ---- Antecedentes ----
    if d.get("antecedentes"):
        p("## 14. Antecedentes")
        p()
        for ant in d["antecedentes"]:
            refs_str = (" (refs: %s)" % ", ".join(ant.get("refs", []))) if ant.get("refs") else ""
            p("- %s%s" % (ant["texto"], refs_str))
        p()

    # ---- Fuera de alcance ----
    p("## 15. Fuera de alcance")
    p()
    for x in d.get("fuera", []):
        p("- %s" % x)
    if not d.get("fuera"):
        ausencia("fuera")
    p()

    # ---- Preguntas ----
    p("## 16. Preguntas abiertas")
    p()
    p("Buzón del planificador: las dudas se apuntan aquí, nunca se responden de palabra.")
    p()
    for x in d.get("preguntas", []):
        p("- %s" % x)
    if not d.get("preguntas"):
        p("- (Ninguna por ahora.)")
    p()

    with open(salida, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("Planificación generada: %s (%d líneas)" % (salida, len(L)))


if __name__ == "__main__":
    try:
        main()
    except KeyError as e:
        sys.exit("planos.json no respeta el esquema: falta el campo %s en algún "
                 "bloque. Valida contra visor/esquema.json y reintenta." % e)
