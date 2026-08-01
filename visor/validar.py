#!/usr/bin/env python3
"""Validador oficial de planos.json. Solo biblioteca estándar.

Comprueba lo que el esquema exige más lo que el método promete: ids únicos
globales, referencias que existen, tablas cuadradas, fichas completas.
Ejecútalo tras CADA actualización de planos.json.

Uso: python validar.py --datos <ruta/planos.json> [--perfil borrador|revision|congelado]
Sale con código 0 si no hay errores (los avisos no bloquean), 1 si los hay.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TIPOS_ACCION = ("humano", "estatico", "ia", "externo")
BASE = Path(__file__).resolve().parent
CAMPOS_FICHA = ("quien", "llega", "cuando", "ve", "puede", "nunca")
ESTADOS_DEFINICION = ("borrador", "listo para revisar", "aprobado", "congelado")
MODOS_DEFINICION = ("entrevista", "autopropuesto", "analisis de codigo", "mixto")
ORIGENES = ("usuario", "codigo", "inferido", "mixto")
ESTADOS_COBERTURA = (
    "no verificado", "implementado", "parcial", "no implementado", "contradice"
)

errores = []
avisos = []


def err(donde, msg):
    errores.append("%s: %s" % (donde, msg))


def aviso(donde, msg):
    avisos.append("%s: %s" % (donde, msg))


def _resolver_ref(esquema_raiz, ref):
    if not ref.startswith("#/"):
        raise ValueError("solo se admiten referencias locales en esquema.json: %s" % ref)
    actual = esquema_raiz
    for parte in ref[2:].split("/"):
        actual = actual[parte.replace("~1", "/").replace("~0", "~")]
    return actual


def _es_tipo(valor, tipo):
    tipos = {
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "string": lambda x: isinstance(x, str),
        "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
        "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        "boolean": lambda x: isinstance(x, bool),
        "null": lambda x: x is None,
    }
    return tipo in tipos and tipos[tipo](valor)


def _errores_esquema(valor, regla, raiz, donde="$" ):
    """Subconjunto Draft 7 usado por nuestro esquema, sin dependencias externas."""
    if "$ref" in regla:
        return _errores_esquema(valor, _resolver_ref(raiz, regla["$ref"]), raiz, donde)
    fallos = []
    if "anyOf" in regla:
        opciones = [_errores_esquema(valor, x, raiz, donde) for x in regla["anyOf"]]
        if not any(not x for x in opciones):
            fallos.append("%s: no cumple ninguna alternativa" % donde)
    if "oneOf" in regla:
        validas = sum(not _errores_esquema(valor, x, raiz, donde) for x in regla["oneOf"])
        if validas != 1:
            fallos.append("%s: debe cumplir exactamente una alternativa" % donde)

    tipo = regla.get("type")
    if tipo and not _es_tipo(valor, tipo):
        return ["%s: se esperaba %s" % (donde, tipo)]
    if "const" in regla and valor != regla["const"]:
        fallos.append("%s: debe ser %r" % (donde, regla["const"]))
    if "enum" in regla and valor not in regla["enum"]:
        fallos.append("%s: valor no permitido" % donde)
    if isinstance(valor, str):
        if len(valor) < regla.get("minLength", 0):
            fallos.append("%s: texto demasiado corto" % donde)
        if regla.get("pattern") and re.search(regla["pattern"], valor) is None:
            fallos.append("%s: no cumple el patrón %s" % (donde, regla["pattern"]))
    if isinstance(valor, list):
        if len(valor) < regla.get("minItems", 0):
            fallos.append("%s: faltan elementos" % donde)
        if "items" in regla:
            for i, item in enumerate(valor):
                fallos.extend(_errores_esquema(item, regla["items"], raiz, "%s[%d]" % (donde, i)))
    if isinstance(valor, dict):
        for nombre in regla.get("required", []):
            if nombre not in valor:
                fallos.append("%s: falta %s" % (donde, nombre))
        propiedades = regla.get("properties", {})
        if regla.get("additionalProperties") is False:
            for nombre in valor:
                if nombre not in propiedades:
                    fallos.append("%s.%s: campo desconocido" % (donde, nombre))
        for nombre, subregla in propiedades.items():
            if nombre in valor:
                fallos.extend(_errores_esquema(valor[nombre], subregla, raiz,
                                                "%s.%s" % (donde, nombre)))
    return fallos


def validar_esquema(d):
    try:
        esquema = json.loads((BASE / "esquema.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return err("esquema.json", "no se puede leer: %s" % exc)
    for fallo in _errores_esquema(d, esquema, esquema):
        err("esquema", fallo)


def _identificadores(d):
    for regla in d.get("reglas", []) or []:
        yield regla.get("id"), "reglas"
    for rec in d.get("recorridos", []) or []:
        yield rec.get("id"), "recorridos"
        for req in rec.get("requisitos", []) or []:
            yield req.get("id"), "%s.requisitos" % rec.get("id", "recorrido")
        for criterio in rec.get("criterios", []) or []:
            yield criterio.get("id"), "%s.criterios" % rec.get("id", "recorrido")
    for calidad in d.get("calidad", []) or []:
        yield calidad.get("id"), "calidad"


def validar_ids_del_proyecto(d, ruta_mapa):
    """Comprueba la promesa de unicidad entre el mapa y todas sus actividades."""
    if not d.get("actividades"):
        return
    raiz = Path(ruta_mapa).resolve().parent
    documentos = [(Path(ruta_mapa).resolve(), d)]
    for actividad in d.get("actividades", []):
        aid = actividad.get("id")
        ruta = raiz / "actividades" / str(aid) / "planos.json"
        if not ruta.is_file():
            continue
        try:
            documentos.append((ruta, json.loads(ruta.read_text(encoding="utf-8"))))
        except (OSError, ValueError) as exc:
            err("ids globales.%s" % aid, "no se puede leer %s: %s" % (ruta, exc))
    vistos = {}
    for ruta, datos in documentos:
        relativo = str(ruta.relative_to(raiz)) if ruta != raiz else str(ruta)
        for identificador, lugar in _identificadores(datos):
            if not identificador:
                continue
            actual = "%s:%s" % (relativo, lugar)
            if identificador in vistos:
                err("ids globales", 'id duplicado "%s" en %s; ya estaba en %s' %
                    (identificador, actual, vistos[identificador]))
            else:
                vistos[identificador] = actual


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


def validar_implementacion(valor, donde):
    if not isinstance(valor, dict):
        return err(donde, "falta el objeto de cobertura de implementación")
    if valor.get("estado") not in ESTADOS_COBERTURA:
        err(donde, "estado inválido; usa: %s" % ", ".join(ESTADOS_COBERTURA))
    if not isinstance(valor.get("evidencias", []), list):
        err(donde, "evidencias debe ser una lista")
    if not isinstance(valor.get("pruebas", []), list):
        err(donde, "pruebas debe ser una lista")


def exigir_revision(d):
    """Impide presentar planos parciales como si estuvieran listos."""
    definicion = d.get("definicion")
    if not isinstance(definicion, dict):
        err("perfil revision", "falta definicion")
        definicion = {}
    if definicion.get("estado") not in ("listo para revisar", "aprobado", "congelado"):
        err("perfil revision", 'definicion.estado debe ser "listo para revisar" o posterior')
    no_aplican = set(definicion.get("bloques_no_aplican", []) or [])

    if d.get("actividades"):
        for nombre, valor in (
            ("descripcion", d.get("descripcion")),
            ("contrato.frase", (d.get("contrato") or {}).get("frase")),
            ("contrato.exito", (d.get("contrato") or {}).get("exito")),
            ("actores", d.get("actores")),
        ):
            if not valor and nombre.split(".", 1)[0] not in no_aplican:
                err("perfil revision", "bloque de mapa sin completar: %s" % nombre)
        if d.get("preguntas"):
            err("perfil revision", "quedan preguntas abiertas en el mapa")
        validar_implementacion(d.get("cobertura"), "perfil revision.cobertura")
        for i, actividad in enumerate(d.get("actividades", [])):
            donde = "perfil revision.actividades[%d]" % i
            if actividad.get("estado") not in ("especificada", "en obra", "entregada"):
                err(donde, "la actividad todavía no está especificada")
            if actividad.get("origen") not in ORIGENES:
                err(donde, "falta origen válido")
            validar_implementacion(actividad.get("cobertura"), donde + ".cobertura")
        return

    obligatorios = (
        ("descripcion", d.get("descripcion")),
        ("contrato.frase", (d.get("contrato") or {}).get("frase")),
        ("contrato.exito", (d.get("contrato") or {}).get("exito")),
        ("actores", d.get("actores")),
        ("flujos", d.get("flujos")),
        ("recorridos", d.get("recorridos")),
        ("estados", d.get("estados")),
        ("datos", d.get("datos")),
        ("superficie", d.get("superficie")),
        ("calidad", d.get("calidad")),
        ("fuera", d.get("fuera")),
    )
    for nombre, valor in obligatorios:
        if not valor and nombre.split(".", 1)[0] not in no_aplican:
            err("perfil revision", "bloque obligatorio sin completar: %s" % nombre)
    for nombre in ("episodios", "reglas", "volumen", "integraciones"):
        if not d.get(nombre) and nombre not in no_aplican:
            err(
                "perfil revision",
                'el bloque "%s" está vacío: complétalo o decláralo en bloques_no_aplican'
                % nombre,
            )
    if d.get("preguntas"):
        err("perfil revision", "quedan preguntas abiertas")
    if not any(f.get("momento") == "futuro" for f in d.get("flujos", [])):
        err("perfil revision", "falta al menos un flujo futuro (el diseño a implementar)")
    validar_implementacion(d.get("cobertura"), "perfil revision.cobertura")

    for i, f in enumerate(d.get("flujos", [])):
        if f.get("origen") not in ORIGENES:
            err("perfil revision.flujos[%d]" % i, "falta origen válido")
    for i, rec in enumerate(d.get("recorridos", [])):
        if not rec.get("requisitos"):
            err("perfil revision.recorridos[%d]" % i, "no contiene requisitos")
        if not rec.get("criterios"):
            err("perfil revision.recorridos[%d]" % i, "no contiene criterios comprobables")
        for j, req in enumerate(rec.get("requisitos", []) or []):
            donde = "perfil revision.recorridos[%d].requisitos[%d]" % (i, j)
            if req.get("origen") not in ORIGENES:
                err(donde, "falta origen válido")
            validar_implementacion(req.get("implementacion"), donde + ".implementacion")


def validar_definicion_y_cobertura(d):
    definicion = d.get("definicion")
    if definicion is not None:
        if not isinstance(definicion, dict):
            err("definicion", "debe ser un objeto")
        else:
            if definicion.get("estado") not in ESTADOS_DEFINICION:
                err("definicion.estado", "valor inválido; usa: %s" % ", ".join(ESTADOS_DEFINICION))
            if definicion.get("modo") not in MODOS_DEFINICION:
                err("definicion.modo", "valor inválido; usa: %s" % ", ".join(MODOS_DEFINICION))
            for i, supuesto in enumerate(definicion.get("supuestos", []) or []):
                if supuesto.get("origen") not in ORIGENES:
                    err("definicion.supuestos[%d]" % i, "falta origen válido")
                if supuesto.get("estado") not in ("propuesto", "confirmado", "rechazado"):
                    err("definicion.supuestos[%d]" % i, "estado inválido")
    cobertura = d.get("cobertura")
    if cobertura is not None:
        validar_implementacion(cobertura, "cobertura")


def validar_planos_de_actividades(d, ruta_mapa, perfil):
    if not d.get("actividades"):
        return
    base = Path(ruta_mapa).resolve().parent
    for actividad in d["actividades"]:
        aid = actividad.get("id")
        if not aid:
            continue
        ruta = base / "actividades" / aid / "planos.json"
        if not ruta.is_file():
            if perfil != "borrador":
                err("perfil %s.actividades.%s" % (perfil, aid), "falta %s" % ruta)
            continue
        r = subprocess.run(
            [sys.executable, __file__, "--datos", str(ruta), "--perfil", perfil],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if r.returncode:
            resumen = " | ".join(x.strip() for x in r.stdout.splitlines() if x.strip())
            err("perfil %s.actividades.%s" % (perfil, aid), resumen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True)
    ap.add_argument(
        "--perfil",
        choices=("borrador", "revision", "congelado"),
        default="borrador",
        help="borrador tolera huecos; revision exige entrega completa; congelado exige aprobación",
    )
    args = ap.parse_args()

    try:
        with open(args.datos, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("ERROR: no pude leer el JSON: %s" % e)

    validar_esquema(d)
    if d.get("version") != 2:
        err("version", "debe ser 2")
    if not d.get("titulo"):
        err("titulo", "falta")
    validar_definicion_y_cobertura(d)
    validar_ids_del_proyecto(d, args.datos)

    # actores y quienes válidos
    ids_quien = set()
    for a in d.get("actores", []):
        if not a.get("nombre"):
            err("actores", "actor sin nombre")
            continue
        ids_quien.add(a["nombre"].lower())
        for m in a.get("miembros", []) or []:
            ids_quien.add(str(m).lower())

    # actividades (plano mapa)
    ids_act = set()
    for i, a in enumerate(d.get("actividades", [])):
        donde = "actividades[%d]" % i
        if not a.get("id") or not a.get("nombre") or not a.get("area"):
            err(donde, "actividad sin id/nombre/area")
            continue
        if a["id"] in ids_act:
            err(donde, 'id de actividad duplicado: "%s"' % a["id"])
        ids_act.add(a["id"])
    for i, a in enumerate(d.get("actividades", [])):
        for dep in a.get("depende_de", []) or []:
            if dep not in ids_act:
                err("actividades[%d] (%s)" % (i, a.get("id")), 'depende de "%s", que no existe en el mapa' % dep)

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

    if args.perfil in ("revision", "congelado"):
        exigir_revision(d)
    if args.perfil == "congelado":
        definicion = d.get("definicion") or {}
        if definicion.get("estado") not in ("aprobado", "congelado"):
            err("perfil congelado", 'definicion.estado debe ser "aprobado" o "congelado"')
        for i, supuesto in enumerate(definicion.get("supuestos", []) or []):
            if supuesto.get("estado") != "confirmado":
                err(
                    "perfil congelado",
                    "el supuesto %s debe estar confirmado antes de congelar"
                    % supuesto.get("id", i + 1),
                )
    validar_planos_de_actividades(d, args.datos, args.perfil)

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

    # estados: acciones como texto u objeto; pasa_a debe apuntar a un estado real
    for e in d.get("estados", []):
        nombres = {x.get("nombre") for x in e.get("estados", [])}
        for x in e.get("estados", []):
            for a in x.get("acciones", []) or []:
                if isinstance(a, dict):
                    if not a.get("accion"):
                        err("estados %s/%s" % (e.get("entidad"), x.get("nombre")), "acción sin texto")
                    if a.get("pasa_a") and a["pasa_a"] not in nombres:
                        aviso("estados %s/%s" % (e.get("entidad"), x.get("nombre")),
                              'pasa_a "%s" no es un estado declarado de esta entidad' % a["pasa_a"])

    # cobertura: reglas huérfanas y requisitos sin prueba
    reglas_citadas = set()
    requisitos_cubiertos = set()
    for rec in d.get("recorridos", []):
        for q in rec.get("requisitos", []) or []:
            if q.get("regla"):
                reglas_citadas.add(q["regla"])
        for c in rec.get("criterios", []) or []:
            if c.get("cubre"):
                requisitos_cubiertos.add(c["cubre"])
    for g in todas_g:
        if g and g not in reglas_citadas:
            aviso("reglas", '%s no la implementa ningún requisito (campo "regla"): regla huérfana o campo sin rellenar' % g)
    for rid in sorted(todos_r):
        if rid and rid not in requisitos_cubiertos:
            aviso("recorridos", '%s no tiene ninguna prueba que lo cubra (campo "cubre" de los criterios)' % rid)

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
    print("OK: planos válidos para perfil %s (%d aviso(s))." % (args.perfil, len(avisos)))


if __name__ == "__main__":
    main()
