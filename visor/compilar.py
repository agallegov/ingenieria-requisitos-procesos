#!/usr/bin/env python3
"""Compila la documentación final de planificación empresarial.

Estructura de salida, siempre la misma:
    plan/
      README.md                      (índice)
      01-constitution/
        constitution.md              (los principios y el mapa: lo global)
      02-procesos/
        <flujo>.md                   (un documento por flujo)
      03-plan-accion/
        plan.md                      (acciones secuenciadas)
      04-entregables/
        entregables.md               (entregables con criterios de aprobación)
      05-cumplimiento/
        cumplimiento.md              (requisitos legales/fiscales/laborales)
      06-presupuesto/
        presupuesto.md               (ítem por ítem)

Se regenera ENTERA en cada ejecución: no se edita a mano. Solo stdlib.

Uso: python compilar.py --planos <ruta/planos.json> [--salida <dir>]
(por defecto escribe en especificaciones/ junto al planos.json)
"""

import argparse
import json
import os
import re
import shutil
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))


def slug(texto):
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "area"


def generar(datos, salida):
    """Genera un markdown descriptivo desde un planos.json."""
    with open(datos, "r", encoding="utf-8") as f:
        d = json.load(f)
    L = []
    a = L.append

    a("# %s" % d.get("titulo", "Proyecto"))
    a("")
    if d.get("descripcion"):
        a(d["descripcion"])
        a("")
    if d.get("contrato") and d["contrato"].get("frase"):
        a("> %s" % d["contrato"]["frase"])
        a("")
    if d.get("flujos"):
        a("## Flujos")
        a("")
        for f in d["flujos"]:
            a("### %s (`%s`)" % (f["titulo"], f["id"]))
            a("")
            a("- Momento: **%s**" % f.get("momento", "sin declarar"))
            if f.get("descripcion"):
                a("- %s" % f["descripcion"])
            if f.get("pasos"):
                a("")
                a("| # | Acción | Responsable |")
                a("|---|--------|-------------|")
                for i, p in enumerate(f["pasos"], 1):
                    if p.get("tipo") == "decision":
                        a("| %d | **%s: %s?** | %s |" % (
                            i,
                            "Regla" if p.get("clase") == "regla" else "Excepción",
                            p.get("condicion", ""),
                            p.get("quien", ""),
                        ))
                        ramas = p.get("ramas") if isinstance(p.get("ramas"), list) else ([p.get("rama")] if p.get("rama") else [])
                        for r in ramas:
                            etiqueta = r.get("etiqueta", "sin etiqueta")
                            a("|   | ↳ **%s** | |" % etiqueta)
                    else:
                        texto = p.get("texto", "")
                        quien = p.get("quien", "")
                        quien_str = " | ".join(quien) if isinstance(quien, list) else quien
                        a("| %d | %s | %s |" % (i, texto, quien_str))
                a("")
    if d.get("actores"):
        a("## Actores")
        a("")
        for x in d["actores"]:
            a("- **%s**%s" % (x["nombre"], (": %s" % x["rol"]) if x.get("rol") else ""))
        a("")
    return "\n".join(L) + "\n"


def md_constitution(d):
    L = []
    a = L.append
    a("# Constitución: %s" % d.get("titulo", "Proyecto"))
    a("")
    a("Lo que vale para toda la planificación: qué se quiere planificar y para qué sirve. "
      "Generado desde los planos: no editar a mano.")
    a("")
    definicion = d.get("definicion") or {}
    a("## Estado y procedencia")
    a("")
    a("- Estado: **%s** (modo: %s)." % (
        definicion.get("estado", "borrador"),
        definicion.get("modo", "sin declarar"),
    ))
    a("")
    supuestos = definicion.get("supuestos", [])
    if supuestos:
        a("### Supuestos")
        a("")
        for supuesto in supuestos:
            a("- %s [%s, %s]: %s" % (
                supuesto.get("id", "Supuesto"),
                supuesto.get("origen", "inferido"),
                supuesto.get("estado", "propuesto"),
                supuesto.get("texto", ""),
            ))
        a("")
    riesgos = definicion.get("riesgos", [])
    if riesgos:
        a("### Riesgos identificados")
        a("")
        for riesgo in riesgos:
            a("- **%s** [impacto: %s]: %s" % (
                riesgo.get("id", "Riesgo"),
                riesgo.get("impacto", ""),
                riesgo.get("descripcion", ""),
            ))
            if riesgo.get("mitigacion"):
                a("  - Mitigación: %s" % riesgo["mitigacion"])
        a("")
    if d.get("descripcion"):
        a("## Qué es")
        a("")
        a(d["descripcion"])
        a("")
    c = d.get("contrato") or {}
    if c.get("frase"):
        a("## Propósito")
        a("")
        a(c["frase"])
        exito = c.get("exito")
        if exito:
            a("")
            a("Criterios de éxito:")
            for x in (exito if isinstance(exito, list) else [exito]):
                a("- %s" % x)
        a("")
    if d.get("actores") or d.get("glosario"):
        a("## Actores y vocabulario")
        a("")
        for x in d.get("actores", []):
            a("- **%s**%s" % (x["nombre"], (": %s" % x["rol"]) if x.get("rol") else ""))
        if d.get("glosario"):
            a("")
            for v in d["glosario"]:
                a("- \"%s\": %s" % (v["termino"], v["significado"]))
        a("")
    if d.get("estructura_organizativa"):
        a("## Estructura organizativa")
        a("")
        for u in d["estructura_organizativa"]:
            ubi = u.get("ubicacion", {})
            ubi_str = ", ".join(v for v in [ubi.get("pais"), ubi.get("ciudad")] if v)
            reporta = " (reporta a: %s)" % u.get("reporta_a", "") if u.get("reporta_a") else ""
            a("- **%s** (`%s`) — %s, %s%s" % (
                u["nombre"], u["id"], u["tipo"], ubi_str, reporta
            ))
        a("")
    if d.get("metricas"):
        a("## Métricas del negocio")
        a("")
        for m in d["metricas"]:
            a("- **%s**: %s" % (m["que"], m["cuanto"]))
        a("")
    if d.get("datos"):
        a("## Datos gestionados")
        a("")
        for x in d["datos"]:
            a("- **%s**: %s%s" % (x["cosa"], ", ".join(x.get("guarda", [])),
                                  (" (origen: %s)" % x["origen"]) if x.get("origen") else ""))
        a("")
    if d.get("proveedores"):
        a("## Proveedores y colaboradores externos")
        a("")
        a("| ID | Nombre | Servicio | Tipo | Coste/Perioc. |")
        a("|----|--------|----------|------|---------------|")
        for p in d["proveedores"]:
            coste = "%s %s" % (p.get("coste_estimado", ""), p.get("periodicidad", "")) if p.get("coste_estimado") else ""
            a("| %s | %s | %s | %s | %s |" % (
                p.get("id", ""),
                p.get("nombre", ""),
                p.get("servicio", ""),
                p.get("tipo", ""),
                coste,
            ))
        a("")
    if d.get("calidad"):
        a("## Compromisos de calidad")
        a("")
        for q in d["calidad"]:
            a("- **%s**: %s" % (q["id"], q["criterio"]))
        a("")
    if d.get("antecedentes"):
        a("## Antecedentes")
        a("")
        for ant in d["antecedentes"]:
            refs_str = " (refs: %s)" % ", ".join(ant.get("refs", [])) if ant.get("refs") else ""
            a("- %s%s" % (ant["texto"], refs_str))
        a("")
    if d.get("fuera"):
        a("## Fuera de alcance")
        a("")
        for x in d["fuera"]:
            a("- %s" % x)
        a("")
    if d.get("preguntas"):
        a("## Preguntas abiertas")
        a("")
        for x in d["preguntas"]:
            a("- %s" % x)
        a("")
    return "\n".join(L) + "\n"


def md_plan_accion(d):
    L = []
    a = L.append
    a("# Plan de Acción")
    a("")
    a("Acciones secuenciadas, responsables y entregables. Generado desde los planos: no editar a mano.")
    a("")
    acciones = d.get("acciones", [])
    if not acciones:
        a("*No hay acciones definidas.*")
        return "\n".join(L) + "\n"

    # Mostrar flujo de dependencias
    a("## Secuencia de acciones")
    a("")
    a("| # | Acción | Responsable | Fecha prevista | Entregable | Avance |")
    a("|---|--------|-------------|----------------|------------|--------|")
    for i, acc in enumerate(acciones, 1):
        avance = acc.get("avance", {}).get("estado", "pendiente") if isinstance(acc.get("avance"), dict) else "pendiente"
        entregable = acc.get("entregable", "")
        fecha = acc.get("fecha_prevista", "")
        secuencia = ", ".join(acc.get("secuencia", [])) if acc.get("secuencia") else ""
        a("| %d | **%s**%s | %s | %s | %s | %s |" % (
            i,
            acc["nombre"],
            (": %s" % acc.get("descripcion", "")) if acc.get("descripcion") else "",
            acc.get("responsable", ""),
            fecha,
            entregable,
            avance,
        ))
        if secuencia:
            a("|   | ↳ siguientes: %s | | | | |" % secuencia)
    a("")
    return "\n".join(L) + "\n"


def md_entregables(d):
    L = []
    a = L.append
    a("# Entregables")
    a("")
    a("Documentos, certificados y resultados del proyecto con criterios de aprobación. Generado desde los planos: no editar a mano.")
    a("")
    entregables = d.get("entregables", [])
    if not entregables:
        a("*No hay entregables definidos.*")
        return "\n".join(L) + "\n"

    a("## Resumen")
    a("")
    a("| # | Entregable | Tipo | Acciones | Fecha prevista | Avance |")
    a("|---|-----------|------|----------|----------------|--------|")
    for i, ent in enumerate(entregables, 1):
        avance = ent.get("avance", {}).get("estado", "pendiente") if isinstance(ent.get("avance"), dict) else "pendiente"
        acciones_refs = ", ".join(ent.get("acciones", [])) if ent.get("acciones") else ""
        a("| %d | **%s** | %s | %s | %s | %s |" % (
            i, ent["nombre"], ent.get("tipo", ""), acciones_refs,
            ent.get("fecha_prevista", ""), avance,
        ))
    a("")

    a("## Detalles")
    a("")
    for ent in entregables:
        a("### %s (`%s`)" % (ent["nombre"], ent["id"]))
        a("")
        if ent.get("descripcion"):
            a(ent["descripcion"])
            a("")
        a("- Tipo: **%s**" % ent.get("tipo", ""))
        if ent.get("acciones"):
            a("- Acciones productoras: %s" % ", ".join(ent["acciones"]))
        if ent.get("fecha_prevista"):
            a("- Fecha prevista: %s" % ent["fecha_prevista"])
        if ent.get("entregado_el"):
            a("- Entregado el: %s" % ent["entregado_el"])
        a("")
        criterios = ent.get("criterios_aprobacion", [])
        if criterios:
            a("#### Criterios de aprobación")
            a("")
            a("| ID | Condición |")
            a("|----|-----------|")
            for c in criterios:
                a("| %s | %s |" % (c.get("id", ""), c.get("condicion", "")))
            a("")
    return "\n".join(L) + "\n"


def md_cumplimiento(d):
    L = []
    a = L.append
    a("# Cumplimiento Legal, Fiscal y Laboral")
    a("")
    a("Requisitos por jurisdicción. Generado desde los planos: no editar a mano.")
    a("")
    cumplimiento = d.get("cumplimiento", [])
    if not cumplimiento:
        a("*No hay requisitos de cumplimiento definidos.*")
        return "\n".join(L) + "\n"

    for c in cumplimiento:
        a("## %s" % c.get("jurisdiccion", "Sin jurisdicción"))
        a("")
        for categoria in ("laboral", "fiscal", "licencias"):
            items = c.get(categoria, [])
            if not items:
                continue
            etiqueta = {"laboral": "Laboral", "fiscal": "Fiscal", "licencias": "Licencias"}[categoria]
            a("### %s" % etiqueta)
            a("")
            a("| ID | Requisito | Plazo | Responsable | Estado |")
            a("|----|----------|-------|-------------|--------|")
            for j, req in enumerate(items, 1):
                # Generamos un ID artificial basado en posición
                req_id = "%s-%d" % (categoria[:3].upper(), j)
                a("| %s | %s | %s | %s | %s |" % (
                    req_id,
                    req.get("requisito", ""),
                    req.get("plazo", ""),
                    req.get("responsable", ""),
                    req.get("estado", ""),
                ))
            a("")
    return "\n".join(L) + "\n"


def md_presupuesto(d):
    L = []
    a = L.append
    a("# Presupuesto")
    a("")
    pres = d.get("presupuesto") or {}
    if not pres:
        a("*No hay presupuesto definido.*")
        return "\n".join(L) + "\n"

    moneda = pres.get("moneda", "EUR")
    a("Moneda: **%s**" % moneda)
    a("")

    a("## Detalle por ítem")
    a("")
    a("| # | Ítem | Categoría | Importe | Periodicidad | Responsable |")
    a("|---|------|-----------|---------|--------------|-------------|")
    for i, item in enumerate(pres.get("items", []), 1):
        a("| %d | %s | %s | %s %s | %s | %s |" % (
            i,
            item.get("nombre", ""),
            item.get("categoria", ""),
            item.get("importe_estimado", ""),
            moneda,
            item.get("periodicidad", ""),
            item.get("responsable", ""),
        ))
    a("")

    a("## Total")
    a("")
    total = pres.get("total_estimado", 0)
    a("**Total estimado: %s %s**" % (total, moneda))
    a("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planos", required=True, help="El planos.json del proyecto")
    ap.add_argument("--salida", help="Carpeta destino (defecto: plan/ junto al plano)")
    args = ap.parse_args()

    ruta_planos = os.path.abspath(args.planos)
    try:
        with open(ruta_planos, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("No pude leer los planos: %s" % e)

    raiz = os.path.dirname(ruta_planos)
    out = os.path.abspath(args.salida or os.path.join(raiz, "especificaciones"))
    dirs = [
        os.path.join(out, "01-constitution"),
        os.path.join(out, "02-procesos"),
        os.path.join(out, "03-plan-accion"),
        os.path.join(out, "04-entregables"),
        os.path.join(out, "05-cumplimiento"),
        os.path.join(out, "06-presupuesto"),
    ]
    for controlado in dirs:
        if os.path.isdir(controlado):
            shutil.rmtree(controlado)
    for d_path in dirs:
        os.makedirs(d_path, exist_ok=True)

    # 01-constitution
    with open(os.path.join(out, "01-constitution", "constitution.md"), "w", encoding="utf-8") as f:
        f.write(md_constitution(d))

    # 02-procesos - un doc por flujo
    for flujo in d.get("flujos", []):
        nombre_slug = slug(flujo.get("titulo", flujo.get("id", "flujo")))
        with open(os.path.join(out, "02-procesos", nombre_slug + ".md"), "w", encoding="utf-8") as f:
            f.write(generar(ruta_planos, None))

    # 03-plan-accion
    with open(os.path.join(out, "03-plan-accion", "plan.md"), "w", encoding="utf-8") as f:
        f.write(md_plan_accion(d))

    # 04-entregables
    with open(os.path.join(out, "04-entregables", "entregables.md"), "w", encoding="utf-8") as f:
        f.write(md_entregables(d))

    # 05-cumplimiento
    with open(os.path.join(out, "05-cumplimiento", "cumplimiento.md"), "w", encoding="utf-8") as f:
        f.write(md_cumplimiento(d))

    # 06-presupuesto
    with open(os.path.join(out, "06-presupuesto", "presupuesto.md"), "w", encoding="utf-8") as f:
        f.write(md_presupuesto(d))

    # README.md índice
    idx = []
    idx.append("# %s: plan de planificación" % d.get("titulo", "Proyecto"))
    idx.append("")
    if (d.get("contrato") or {}).get("frase"):
        idx.append("> %s" % d["contrato"]["frase"])
        idx.append("")
    idx.append("Generado desde los planos con `visor/compilar.py`: no editar a mano.")
    idx.append("")
    idx.append("- [01-constitution/constitution.md](01-constitution/constitution.md): lo que vale para toda la planificación.")
    idx.append("- [02-procesos/](02-procesos/): un documento por flujo de proceso.")
    idx.append("- [03-plan-accion/plan.md](03-plan-accion/plan.md): acciones secuenciadas.")
    idx.append("- [04-entregables/entregables.md](04-entregables/entregables.md): entregables y criterios de aprobación.")
    idx.append("- [05-cumplimiento/cumplimiento.md](05-cumplimiento/cumplimiento.md): requisitos legales, fiscales y laborales.")
    idx.append("- [06-presupuesto/presupuesto.md](06-presupuesto/presupuesto.md): presupuesto detallado.")
    idx.append("")
    idx.append("---")
    idx.append("")
    idx.append("Plan de %d acciones y %d entregables." % (
        len(d.get("acciones", [])), len(d.get("entregables", []))))
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx) + "\n")
    print("Plan compilado en %s (%d acciones, %d entregables)" % (out, len(d.get("acciones", [])), len(d.get("entregables", []))))


if __name__ == "__main__":
    main()
