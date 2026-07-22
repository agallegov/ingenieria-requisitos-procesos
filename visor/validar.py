#!/usr/bin/env python3
"""Validador oficial de planos.json. Solo biblioteca estándar.

Comprueba lo que el esquema exige más lo que el método promete: ids únicos
globales, referencias que existen, tablas cuadradas, fichas completas.
Ejecútalo tras CADA actualización de planos.json.

Uso: python3 validar.py --datos <ruta/planos.json>
Sale con código 0 si no hay errores (los avisos no bloquean), 1 si los hay.
"""

import argparse
import json
import re
import sys

TIPOS_ACCION = ("humano", "estatico", "ia", "externo")
BLOQUES = {"version", "proyecto", "titulo", "descripcion", "contrato", "actores",
           "vocabulario", "flujos", "episodios", "recorridos", "reglas", "estados",
           "datos", "volumen", "integraciones", "superficie", "calidad", "fuera",
           "preguntas"}
CAMPOS_FICHA = ("quien", "llega", "cuando", "ve", "puede", "nunca")

errores = []
avisos = []


def err(donde, msg):
    errores.append("%s: %s" % (donde, msg))


def aviso(donde, msg):
    avisos.append("%s: %s" % (donde, msg))


def validar_paso(p, donde, ids_quien):
    if not isinstance(p, dict):
        return err(donde, "el paso no es un objeto")
    tipo = p.get("tipo")
    if tipo == "decision":
        if p.get("clase") not in ("regla", "excepcion"):
            err(donde, 'decision sin "clase" regla/excepcion')
        if not p.get("condicion"):
            err(donde, 'decision sin "condicion"')
        ramas = p.get("ramas") if isinstance(p.get("ramas"), list) else ([p["rama"]] if isinstance(p.get("rama"), dict) else [])
        if not ramas:
            err(donde, "decision sin rama ni ramas")
        for i, r in enumerate(ramas):
            d2 = "%s.rama[%d]" % (donde, i)
            if not isinstance(r, dict) or not r.get("etiqueta"):
                err(d2, "rama sin etiqueta")
                continue
            if not isinstance(r.get("pasos"), list) or not r["pasos"]:
                err(d2, "rama sin pasos")
                continue
            for j, x in enumerate(r["pasos"]):
                validar_paso(x, "%s.pasos[%d]" % (d2, j), ids_quien)
    elif tipo in TIPOS_ACCION:
        if not p.get("texto"):
            err(donde, 'paso "%s" sin "texto"' % tipo)
        quien = p.get("quien")
        if quien and ids_quien and quien.lower() not in ids_quien:
            aviso(donde, 'quien "%s" no está en actores (ni como miembro)' % quien)
    else:
        err(donde, 'tipo de paso desconocido: "%s"' % tipo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True)
    args = ap.parse_args()

    try:
        with open(args.datos, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("ERROR: no pude leer el JSON: %s" % e)

    if d.get("version") != 2:
        err("version", "debe ser 2")
    if not d.get("titulo"):
        err("titulo", "falta")
    for k in d:
        if k not in BLOQUES:
            aviso(k, "bloque desconocido (no lo pinta el visor ni el spec)")

    # actores y quienes válidos
    ids_quien = set()
    for a in d.get("actores", []):
        if not a.get("nombre"):
            err("actores", "actor sin nombre")
            continue
        ids_quien.add(a["nombre"].lower())
        for m in a.get("miembros", []) or []:
            ids_quien.add(str(m).lower())

    # flujos
    vistos_flujo = set()
    for i, f in enumerate(d.get("flujos", [])):
        donde = "flujos[%d]" % i
        if not f.get("id") or not f.get("titulo") or f.get("momento") not in ("hoy", "futuro"):
            err(donde, "flujo sin id/titulo/momento válido")
        if f.get("id") in vistos_flujo:
            err(donde, 'id de flujo duplicado: "%s"' % f.get("id"))
        vistos_flujo.add(f.get("id"))
        for j, p in enumerate(f.get("pasos", []) or []):
            validar_paso(p, "%s.pasos[%d]" % (donde, j), ids_quien)
        if not f.get("pasos"):
            err(donde, "flujo sin pasos")

    # ids globales únicos
    ids = {}

    def registrar(idv, patron, donde):
        if not idv:
            return
        if not re.match(patron, idv):
            err(donde, 'id "%s" no cumple el patrón %s' % (idv, patron))
        if idv in ids:
            err(donde, 'id duplicado "%s" (ya usado en %s); la numeración es GLOBAL' % (idv, ids[idv]))
        ids[idv] = donde

    todos_r, todas_g = set(), set()
    for g in d.get("reglas", []):
        registrar(g.get("id"), r"^G-\d+$", "reglas")
        todas_g.add(g.get("id"))
        t = g.get("tabla")
        if t:
            ncol = len(t.get("columnas", []))
            for k, fila in enumerate(t.get("filas", [])):
                if len(fila) != ncol:
                    err("reglas %s fila %d" % (g.get("id"), k + 1),
                        "tiene %d celdas y la tabla %d columnas" % (len(fila), ncol))
    for rec in d.get("recorridos", []):
        registrar(rec.get("id"), r"^REC-\d+$", "recorridos")
        for q in rec.get("requisitos", []) or []:
            registrar(q.get("id"), r"^R-\d+$", rec.get("id", "recorrido"))
            todos_r.add(q.get("id"))
    for rec in d.get("recorridos", []):
        for q in rec.get("requisitos", []) or []:
            if q.get("regla") and q["regla"] not in todas_g:
                err("%s %s" % (rec.get("id"), q.get("id")), 'cita la regla inexistente "%s"' % q["regla"])
        for c in rec.get("criterios", []) or []:
            registrar(c.get("id"), r"^C-\d+$", rec.get("id", "recorrido"))
            if c.get("cubre") and c["cubre"] not in todos_r:
                err("%s %s" % (rec.get("id"), c.get("id")), 'dice cubrir el requisito inexistente "%s"' % c["cubre"])
    for q in d.get("calidad", []):
        registrar(q.get("id"), r"^Q-\d+$", "calidad")

    # episodios: refs que existan
    for i, e in enumerate(d.get("episodios", [])):
        for ref in e.get("refs", []) or []:
            if ref not in ids:
                aviso("episodios[%d]" % i, 'ref "%s" no corresponde a ningún id' % ref)

    # superficie: fichas completas, avisos con canal
    sup = d.get("superficie") or {}
    for i, p in enumerate(sup.get("puntos", []) or []):
        faltan = [c for c in CAMPOS_FICHA if not p.get(c)]
        if faltan:
            aviso("superficie.puntos[%d] (%s)" % (i, p.get("nombre", "?")),
                  "ficha coja, faltan: %s (el método exige los 7 campos)" % ", ".join(faltan))
    for i, a in enumerate(sup.get("avisos", []) or []):
        if not a.get("canal"):
            aviso("superficie.avisos[%d]" % i, "aviso sin canal (el método exige canal explícito)")
    perm = sup.get("permisos")
    if perm:
        acc = set(perm.get("acciones", []))
        for r in perm.get("roles", []) or []:
            for x in r.get("permitidas", []) or []:
                if x not in acc:
                    err("superficie.permisos", 'el rol "%s" tiene permitida "%s", que no está en acciones' % (r.get("rol"), x))

    for linea in avisos:
        print("AVISO  %s" % linea)
    for linea in errores:
        print("ERROR  %s" % linea)
    if errores:
        print("\n%d error(es), %d aviso(s). Corrige los errores antes de seguir." % (len(errores), len(avisos)))
        sys.exit(1)
    print("OK: planos válidos (%d aviso(s))." % len(avisos))


if __name__ == "__main__":
    main()
