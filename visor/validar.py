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

TIPOS_ACCION = ("humano", "automatizado", "externo")
BASE = Path(__file__).resolve().parent
CAMPOS_FICHA = ("quien", "llega", "cuando", "ve", "puede", "nunca")
ESTADOS_DEFINICION = ("borrador", "listo para revisar", "aprobado", "congelado")
MODOS_DEFINICION = ("entrevista", "documentacion", "experto")
ORIGENES = ("usuario", "documentacion", "inferido", "mixto")
ESTADOS_AVANCE = ("pendiente", "en progreso", "completado", "cancelado")
ESTADOS_CUMPLIMIENTO = ("pendiente", "en proceso", "cumplido", "no aplicable")

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


# Lo que _errores_esquema implementa DE VERDAD. Si esquema.json usara cualquier otra keyword
# de validación (if/then, patternProperties, allOf, maxLength, …), este validador la ignoraría
# EN SILENCIO y unos planos inválidos pasarían por válidos. Antes de validar nada se recorre
# el esquema entero y cualquier keyword fuera de esta lista es un error ruidoso.
KEYWORDS_SOPORTADAS = frozenset((
    "$ref", "anyOf", "oneOf", "type", "const", "enum", "minLength", "pattern",
    "minItems", "items", "required", "properties", "additionalProperties",
))
# Anotaciones y estructura: por definición no validan nada, así que ignorarlas es correcto.
KEYWORDS_ESTRUCTURALES = frozenset((
    "$schema", "$id", "$comment", "title", "description", "examples", "default",
    "definitions",
))


def _keywords_no_soportadas(regla, donde="#"):
    """Keywords de esquema.json que este validador ignoraría en silencio.

    Distingue posición de KEYWORD de posición de NOMBRE: las claves dentro de `properties`
    o `definitions` son nombres de campo (un campo puede llamarse `if` sin ser la keyword),
    así que ahí no se juzga la clave, solo se desciende a su subesquema. También caza las
    FORMAS no implementadas de keywords soportadas: `items` como lista (tupla), `type` como
    lista y `additionalProperties` con un subesquema en vez de un booleano.
    """
    if not isinstance(regla, dict):
        return ["%s: se esperaba un objeto-esquema, no %s" % (donde, type(regla).__name__)]
    hallazgos = []
    for clave, valor in regla.items():
        ruta = "%s/%s" % (donde, clave)
        if clave in ("properties", "definitions"):
            if isinstance(valor, dict):
                for nombre, sub in valor.items():
                    hallazgos += _keywords_no_soportadas(sub, "%s/%s" % (ruta, nombre))
        elif clave in ("anyOf", "oneOf"):
            if isinstance(valor, list):
                for i, sub in enumerate(valor):
                    hallazgos += _keywords_no_soportadas(sub, "%s[%d]" % (ruta, i))
        elif clave == "items":
            if isinstance(valor, list):
                hallazgos.append("%s: items en forma de lista (tupla) no está implementado"
                                 % ruta)
            else:
                hallazgos += _keywords_no_soportadas(valor, ruta)
        elif clave == "additionalProperties":
            if not isinstance(valor, bool):
                hallazgos.append("%s: additionalProperties solo se implementa como booleano"
                                 % ruta)
        elif clave == "type":
            if not isinstance(valor, str):
                hallazgos.append("%s: type como lista no está implementado" % ruta)
        elif clave not in KEYWORDS_SOPORTADAS and clave not in KEYWORDS_ESTRUCTURALES:
            hallazgos.append("%s: keyword de validación no soportada por este validador "
                             "(se ignoraría en silencio)" % ruta)
    return hallazgos


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
    sospechosas = _keywords_no_soportadas(esquema)
    if sospechosas:
        for hallazgo in sospechosas:
            err("esquema.json", hallazgo)
        return err("esquema.json", "NO se validó nada contra el esquema: primero quita o "
                   "implementa las keywords de arriba (validar.py, _errores_esquema)")
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


def validar_avance(valor, donde):
    if not isinstance(valor, dict):
        return err(donde, "falta el objeto de avance")
    if valor.get("estado") not in ESTADOS_AVANCE:
        err(donde, "estado inválido; usa: %s" % ", ".join(ESTADOS_AVANCE))


def exigir_revision(d):
    """Impide presentar planos parciales como si estuvieran listos."""
    definicion = d.get("definicion")
    if not isinstance(definicion, dict):
        err("perfil revision", "falta definicion")
        definicion = {}
    if definicion.get("estado") not in ("listo para revisar", "aprobado", "congelado"):
        err("perfil revision", 'definicion.estado debe ser "listo para revisar" o posterior')
    no_aplican = set(definicion.get("bloques_no_aplican", []) or [])

    # V3: bloques obligatorios para planificación empresarial
    obligatorios = (
        ("descripcion", d.get("descripcion")),
        ("contrato.frase", (d.get("contrato") or {}).get("frase")),
        ("contrato.exito", (d.get("contrato") or {}).get("exito")),
        ("actores", d.get("actores")),
        ("flujos", d.get("flujos")),
        ("acciones", d.get("acciones")),
        ("entregables", d.get("entregables")),
        ("fuera", d.get("fuera")),
    )
    for nombre, valor in obligatorios:
        if not valor and nombre.split(".", 1)[0] not in no_aplican:
            err("perfil revision", "bloque obligatorio sin completar: %s" % nombre)
    if d.get("preguntas"):
        err("perfil revision", "quedan preguntas abiertas")
    if not any(f.get("momento") == "futuro" for f in d.get("flujos", [])):
        err("perfil revision", "falta al menos un flujo futuro (el diseño a implementar)")

    # Validar acciones: deben tener entregables y origen válido
    for i, a in enumerate(d.get("acciones", [])):
        donde = "perfil revision.acciones[%d]" % i
        if a.get("origen") not in ORIGENES:
            err(donde, "falta origen válido")
        validar_avance(a.get("avance"), donde + ".avance")
        if a.get("entregable"):
            entregable_id = a["entregable"]
            ids_entregables = {e.get("id") for e in d.get("entregables", []) or []}
            if entregable_id not in ids_entregables:
                err(donde, 'entregable "%s" no existe en entregables' % entregable_id)

    # Validar entregables: deben tener criterios de aprobación
    for i, ent in enumerate(d.get("entregables", [])):
        donde = "perfil revision.entregables[%d]" % i
        if not ent.get("criterios_aprobacion"):
            err(donde, "no contiene criterios de aprobación")
        validar_avance(ent.get("avance"), donde + ".avance")
        for c in ent.get("criterios_aprobacion", []) or []:
            if c.get("entregable") and c["entregable"] != ent.get("id"):
                err(donde, 'criterio指向 entregable incorrecto: "%s"' % c.get("entregable"))


def validar_definicion_y_avance(d):
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
            for i, riesgo in enumerate(definicion.get("riesgos", []) or []):
                if riesgo.get("impacto") not in ("alto", "medio", "bajo"):
                    err("definicion.riesgos[%d]" % i, "impacto inválido")


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
    if d.get("version") != 3:
        err("version", "debe ser 3")
    if not d.get("titulo"):
        err("titulo", "falta")
    validar_definicion_y_avance(d)
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

    # Reglas/normas
    for g in d.get("normas", []):
        registrar(g.get("id"), r"^G-\d+$", "normas")
        t = g.get("tabla")
        if t:
            ncol = len(t.get("columnas", []))
            for k, fila in enumerate(t.get("filas", [])):
                if len(fila) != ncol:
                    err("normas %s fila %d" % (g.get("id"), k + 1),
                        "tiene %d celdas y la tabla %d columnas" % (len(fila), ncol))

    # Acciones
    ids_acciones = set()
    for a in d.get("acciones", []):
        registrar(a.get("id"), r"^A-\d+$", "acciones")
        ids_acciones.add(a.get("id"))

    # Entregables
    ids_entregables = set()
    for e in d.get("entregables", []):
        registrar(e.get("id"), r"^ENT-\d+$", "entregables")
        ids_entregables.add(e.get("id"))
        for c in e.get("criterios_aprobacion", []) or []:
            registrar(c.get("id"), r"^C-\d+$", e.get("id", "entregable"))
            if c.get("entregable") and c["entregable"] not in ids_entregables:
                err("%s %s" % (e.get("id"), c.get("id")), 'dice cubrir el entregable inexistente "%s"' % c["entregable"])

    # Proveedores
    for p in d.get("proveedores", []):
        registrar(p.get("id"), r"^PROV-\d+$", "proveedores")

    for a in d.get("acciones", []):
        if a.get("entregable") and a["entregable"] not in ids_entregables:
            err("acciones %s" % a.get("id"), 'cita el entregable inexistente "%s"' % a["entregable"])
        for sec in a.get("secuencia", []) or []:
            if sec not in ids_acciones:
                err("acciones %s" % a.get("id"), 'cita la acción inexistente "%s"' % sec)

    for q in d.get("calidad", []):
        registrar(q.get("id"), r"^Q-\d+$", "calidad")

    # Estructura organizativa: verifica dependencias
    ids_unidades = set()
    for u in d.get("estructura_organizativa", []):
        registrar(u.get("id"), r"^U-\d+$", "estructura_organizativa")
        ids_unidades.add(u.get("id"))
    for u in d.get("estructura_organizativa", []):
        if u.get("reporta_a") and u["reporta_a"] not in ids_unidades:
            err("estructura_organizativa %s" % u.get("id"), 'reporta_a "%s" no existe en estructura' % u["reporta_a"])
        for dep in u.get("depende_de", []) or []:
            if dep not in ids_unidades:
                err("estructura_organizativa %s" % u.get("id"), 'depende de "%s", que no existe en estructura' % dep)

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

    # episodios/antecedentes: refs que existan
    for i, e in enumerate(d.get("antecedentes", []) or []):
        for ref in e.get("refs", []) or []:
            if ref not in ids:
                aviso("antecedentes[%d]" % i, 'ref "%s" no corresponde a ningún id' % ref)

    # cumplimiento: estados válidos
    for i, c in enumerate(d.get("cumplimiento", []) or []):
        donde = "cumplimiento[%d] (%s)" % (i, c.get("jurisdiccion", "?"))
        if c.get("origen") not in ORIGENES:
            err(donde, "falta origen válido")
        for categoria in ("laboral", "fiscal", "licencias"):
            for j, req in enumerate(c.get(categoria, []) or []):
                if req.get("estado") not in ESTADOS_CUMPLIMIENTO:
                    err(donde + ".%s[%d]" % (categoria, j), "estado inválido")

    # distribucion: avisos con canal, permisos consistentes
    dist = d.get("distribucion") or {}
    for i, ent in enumerate(dist.get("entregas", []) or []):
        if not ent.get("canal"):
            aviso("distribucion.entregas[%d]" % i, "entrega sin canal (el método exige canal explícito)")
    for i, a in enumerate(dist.get("avisos", []) or []):
        if not a.get("canal"):
            aviso("distribucion.avisos[%d]" % i, "aviso sin canal (el método exige canal explícito)")
    perm = dist.get("permisos")
    if perm:
        acc = set(perm.get("acciones", []))
        for r in perm.get("roles", []) or []:
            for x in r.get("permitidas", []) or []:
                if x not in acc:
                    err("distribucion.permisos", 'el rol "%s" tiene permitida "%s", que no está en acciones' % (r.get("rol"), x))

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
