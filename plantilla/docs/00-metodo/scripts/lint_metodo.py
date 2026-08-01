#!/usr/bin/env python3
"""Linter del método: valida que la estructura y el vocabulario cerrado no degeneren.

Uso: python docs/00-metodo/scripts/lint_metodo.py   (desde la raíz del meta-repo)
Salida: OK/WARN/FAIL por comprobación. Exit 0 si no hay FAIL; exit 1 si hay alguno.
Se ejecuta: al arrancar sesión del padre, en cada cierre, y en CI del meta-repo.
Sin dependencias: solo stdlib. El disco es la verdad; este script solo la comprueba.
"""
import datetime
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
fallos, avisos = [], []
HOY = datetime.date.today()


def ok(msg):
    print(f"  OK   {msg}")


def warn(msg):
    avisos.append(msg)
    print(f"  WARN {msg}")


def fail(msg):
    fallos.append(msg)
    print(f"  FAIL {msg}")


ESTADOS_UNIDAD = {"planificada", "en_obra", "en_revision", "mergeada", "bloqueada", "descartada"}
TIPOS = {"bug", "feature", "refactor", "migracion", "auditoria", "investigacion", "documentacion"}
CARRILES = {"normal", "completo"}
DOCS_PERMITIDOS = {"00-metodo", "01-constitucion", "02-flujos", "03-investigacion",
                   "04-planificacion", "05-trabajo", "bugs", "conocimiento", "decisiones"}
CLAVES_FRONTMATTER = {"unidad", "tipo", "carril", "estado", "actividad", "ficheros",
                      "actualizado", "aprobado"}
EN_VUELO = {"en_obra", "en_revision"}
RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Marca que `unidad.py despachar --force` escribe en la ficha de un hotfix P0. Es la única
# forma legítima de estar en obra sin `aprobado:`, y es DEUDA: hotfix.md da 24 h para pagarla.
MARCA_DEUDA = "DEUDA DE SPEC — HOTFIX"

# Línea de cierre de la ficha de bug: "**Validación del usuario:** PENDIENTE | OK (fecha) | …".
# El separador es laxo (`:`, `*`, espacios) porque el énfasis markdown varía entre fichas.
RE_VALIDACION = re.compile(r"Validaci[oó]n del usuario[\s:*]*(.*)$", re.IGNORECASE)
# Marcador de plantilla sin rellenar: `<ruta del test>`, `<qué se cambió>`, …
RE_PLACEHOLDER = re.compile(r"<[^<>\n]{2,}>")
PISTA_PLANTILLA = "(pegado, no resumido)"


def lineas_de_plantilla_bug():
    """Líneas literales de plantillas/bug.md: sirven para separar PLANTILLA de EVIDENCIA.

    La propia plantilla nombra ROJO y VERDE en sus instrucciones ("Test del bug: VERDE —
    output pegado…"), así que buscar esas palabras a pelo daría por buena una ficha en blanco.
    Solo cuenta como evidencia el texto que alguien AÑADIÓ a la ficha.
    """
    try:
        texto = (RAIZ / "docs/00-metodo/plantillas/bug.md").read_text(encoding="utf-8")
    except OSError:
        return set()
    return {linea.strip() for linea in texto.splitlines() if linea.strip()}


PLANTILLA_BUG = lineas_de_plantilla_bug()


def validado_por_el_usuario(texto):
    """¿La sección 6 de la ficha lleva la validación del usuario en OK?

    Se mira el VALOR que sigue a 'Validación del usuario:' y se exige que EMPIECE por OK. Así
    la línea intacta de la plantilla —que contiene la palabra OK dentro del menú
    'PENDIENTE | OK (YYYY-MM-DD) | REABIERTO'— no cuela como validación.
    """
    for linea in texto.splitlines():
        m = RE_VALIDACION.search(linea)
        if m and re.match(r"^OK\b", m.group(1).strip().strip("*").strip(), re.IGNORECASE):
            return True
    return False


def evidencia_rojo_verde(texto):
    """¿Está pegado el par ROJO (§2) → VERDE (§5) del test del bug? Devuelve (rojo, verde).

    Detección a propósito tolerante —basta con que aparezcan las palabras ROJO y VERDE, porque
    el formato del output pegado no se puede predecir—, pero se descarta todo lo que siga
    siendo plantilla: líneas idénticas a plantillas/bug.md, marcadores `<…>` sin rellenar o la
    pista "(pegado, no resumido)". Una ficha sin tocar no puede pasar por evidencia.
    """
    rojo = verde = False
    for linea in texto.splitlines():
        limpia = linea.strip()
        if not limpia or limpia in PLANTILLA_BUG:
            continue
        if RE_PLACEHOLDER.search(limpia) or PISTA_PLANTILLA in limpia:
            continue
        minuscula = limpia.lower()
        rojo = rojo or "rojo" in minuscula
        verde = verde or "verde" in minuscula
    return rojo, verde


def aprobado_por_el_usuario(fm):
    """¿El frontmatter lleva una fecha de aprobación real? (`no`, vacío o ausente = no)."""
    valor = (fm.get("aprobado") or "").strip().strip("`'\"")
    if not RE_FECHA.match(valor):
        return False
    try:
        datetime.date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def revisar_deuda_hotfix(nombre, ruta, fm):
    """La deuda de spec de un hotfix deja de ser un adorno: aquí se le pone reloj.

    Criterio (runbook hotfix.md): la marca se borra al pagar la deuda — reproducción
    determinista, causa raíz y tests de regresión contraprobados — en las 24 h siguientes a
    estabilizar. Por eso:
      · FAIL si la unidad ya está `mergeada`: se cerró con el contrato a deber, y después de
        cerrar nadie vuelve a pagarlo.
      · FAIL si `actualizado:` tiene más de 24 h (granularidad de día: ayer aún cabe en el
        plazo, anteayer ya no): venció el plazo del runbook.
      · WARN mientras siga dentro del plazo, para que se vea en cada arranque de sesión.
    """
    if MARCA_DEUDA not in ruta.read_text(encoding="utf-8"):
        return
    if fm.get("estado") == "mergeada":
        fail(f"{nombre}: mergeada con la DEUDA DE SPEC del hotfix sin pagar "
             f"(hotfix.md: se paga ANTES de cerrar; borra la marca al completar la ficha)")
        return
    actualizado = (fm.get("actualizado") or "").strip()
    try:
        dias = (HOY - datetime.date.fromisoformat(actualizado)).days
    except ValueError:
        fail(f"{nombre}: deuda de hotfix con 'actualizado: {actualizado or 'ausente'}' "
             f"ilegible — sin fecha no hay plazo que valga")
        return
    if dias > 1:
        fail(f"{nombre}: DEUDA DE SPEC del hotfix sin pagar {dias} días después de "
             f"'actualizado: {actualizado}' (plazo: 24 h, hotfix.md). No se abre trabajo "
             f"nuevo que no sea otro hotfix hasta pagarla")
    else:
        warn(f"{nombre}: DEUDA DE SPEC del hotfix sin pagar (dentro del plazo de 24 h desde "
             f"{actualizado}): completa la ficha y borra la marca")


def frontmatter(path):
    """Parseo mínimo del frontmatter YAML (clave: valor). Devuelve dict o None."""
    try:
        lineas = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lineas or lineas[0].strip() != "---":
        return None
    datos = {}
    for linea in lineas[1:]:
        if linea.strip() == "---":
            return datos
        m = re.match(r"^(\w+):\s*(.*)$", linea)
        if m:
            datos[m.group(1)] = m.group(2).split("#")[0].strip()
    return None


print("== Linter del método ==")

# --- 1. Raíz: ficheros y tope de tamaño del router ---
agents = RAIZ / "AGENTS.md"
if not agents.exists():
    fail("AGENTS.md no existe")
else:
    n = len(agents.read_text(encoding="utf-8").splitlines())
    if n > 160:
        fail(f"AGENTS.md tiene {n} líneas (tope 160): el router está engordando")
    else:
        ok(f"AGENTS.md existe ({n} líneas ≤ 160)")

for puente in ("CLAUDE.md", "GEMINI.md"):
    ruta_puente = RAIZ / puente
    if not ruta_puente.exists() or ruta_puente.read_text(encoding="utf-8") != "@AGENTS.md\n":
        fail(f"{puente} debe contener únicamente '@AGENTS.md'")
    else:
        ok(f"{puente} redirige directamente a AGENTS.md")

# --- 2. El árbol congelado ---
for d in sorted(DOCS_PERMITIDOS):
    if not (RAIZ / "docs" / d).is_dir():
        fail(f"falta docs/{d}/ (árbol congelado, ver ADR/estructura)")
extras = {p.name for p in (RAIZ / "docs").iterdir() if p.is_dir()} - DOCS_PERMITIDOS
if extras:
    fail(f"directorios NO permitidos en docs/ (cambiar la estructura exige ADR): {sorted(extras)}")
else:
    ok("docs/ contiene exactamente el árbol congelado")

# --- 3. ESTADO.md: existe y no engorda ---
estado_md = RAIZ / "docs/05-trabajo/ESTADO.md"
if not estado_md.exists():
    fail("docs/05-trabajo/ESTADO.md no existe")
else:
    n = len(estado_md.read_text(encoding="utf-8").splitlines())
    (ok if n <= 100 else fail)(f"ESTADO.md: {n} líneas {'≤ 100' if n <= 100 else '> 100 (es un digest, no un archivo)'}")

# --- 4. Unidades: nombre, frontmatter, vocabulario, coherencia ---
trabajo = RAIZ / "docs/05-trabajo"
unidades, numeros = {}, {}
for carpeta in sorted(trabajo.iterdir()):
    if not carpeta.is_dir() or carpeta.name == "archivo":
        continue
    if not re.match(r"^\d{3}-[a-z0-9-]+$", carpeta.name):
        fail(f"unidad con nombre fuera de convención NNN-slug: {carpeta.name}")
        continue
    nnn = carpeta.name[:3]
    if nnn in numeros:
        fail(f"NNN duplicado: {carpeta.name} y {numeros[nnn]}")
    numeros[nnn] = carpeta.name
    spec = carpeta / "especificacion.md"
    fm = frontmatter(spec)
    if fm is None:
        fail(f"{carpeta.name}: especificacion.md sin frontmatter válido")
        continue
    faltan = CLAVES_FRONTMATTER - set(fm)
    if faltan:
        fail(f"{carpeta.name}: frontmatter sin claves {sorted(faltan)}")
    if fm.get("estado") not in ESTADOS_UNIDAD:
        fail(f"{carpeta.name}: estado '{fm.get('estado')}' fuera del vocabulario {sorted(ESTADOS_UNIDAD)}")
    if fm.get("tipo") not in TIPOS:
        fail(f"{carpeta.name}: tipo '{fm.get('tipo')}' fuera del vocabulario")
    if fm.get("carril") not in CARRILES:
        fail(f"{carpeta.name}: carril '{fm.get('carril')}' fuera del vocabulario")
    if fm.get("estado") in EN_VUELO:
        spec_txt = spec.read_text(encoding="utf-8") if spec.exists() else ""
        if "## Plan de trabajo" not in spec_txt:
            fail(f"{carpeta.name}: en obra sin 'Plan de trabajo' en su especificacion (ADR-005)")
        # El contrato lo aprueba el usuario: estar en obra con 'aprobado: no' significa que
        # alguien se despachó a sí mismo. La única excepción es el hotfix P0, que deja marca
        # de deuda (y esa deuda la vigila revisar_deuda_hotfix con su propio reloj).
        if not aprobado_por_el_usuario(fm) and MARCA_DEUDA not in spec_txt:
            fail(f"{carpeta.name}: {fm.get('estado')} con 'aprobado: "
                 f"{fm.get('aprobado') or 'ausente'}' — se despachó SIN aprobación del usuario "
                 f"(el contrato lo aprueba él, no el agente)")
    revisar_deuda_hotfix(carpeta.name, spec, fm)
    if fm.get("estado") == "mergeada":
        fail(f"{carpeta.name}: mergeada pero sin archivar (el cierre quedó a medias — re-ejecutar)")
    unidades[carpeta.name] = fm

# --- 4c. Bugs: docs/bugs/NNN-slug.md, fichero vivo por bug (ADR-006) ---
bugs_dir = RAIZ / "docs/bugs"
if bugs_dir.is_dir():
    indice_bugs = bugs_dir / "INDICE.md"
    texto_indice = indice_bugs.read_text(encoding="utf-8") if indice_bugs.exists() else ""
    for fichero in sorted(bugs_dir.glob("*.md")):
        nombre = fichero.stem
        if not re.match(r"^\d{3}", nombre):
            continue  # INDICE.md y ficheros de soporte: no son fichas de bug
        if not re.match(r"^\d{3}-[a-z0-9-]+$", nombre):
            fail(f"bug con nombre fuera de convención NNN-slug.md: bugs/{fichero.name}")
            continue
        nnn = nombre[:3]
        if nnn in numeros:
            fail(f"NNN duplicado: bugs/{nombre} y {numeros[nnn]}")
        numeros[nnn] = f"bugs/{nombre}"
        fm = frontmatter(fichero)
        if fm is None:
            fail(f"bugs/{nombre}: sin frontmatter válido")
            continue
        if fm.get("tipo") != "bug":
            fail(f"bugs/{nombre}: tipo '{fm.get('tipo')}' (en docs/bugs/ solo tipo bug)")
        if fm.get("estado") not in ESTADOS_UNIDAD:
            fail(f"bugs/{nombre}: estado '{fm.get('estado')}' fuera del vocabulario {sorted(ESTADOS_UNIDAD)}")
        texto_bug = fichero.read_text(encoding="utf-8")
        if fm.get("estado") in EN_VUELO and not aprobado_por_el_usuario(fm) \
                and MARCA_DEUDA not in texto_bug:
            fail(f"bugs/{nombre}: {fm.get('estado')} con 'aprobado: "
                 f"{fm.get('aprobado') or 'ausente'}' — se despachó SIN aprobación del usuario "
                 f"(o, si fue producción caída, sin la marca de deuda del hotfix)")
        revisar_deuda_hotfix(f"bugs/{nombre}", fichero, fm)
        # Un bug NO se archiva (ADR-006): `mergeada` es su estado final, así que nadie vuelve a
        # mirarlo después. Las dos puertas del paso 9 de runbooks/bug.md —evidencia rojo→verde
        # y OK del usuario— se comprueban aquí, sobre la ficha viva, o no se comprueban nunca.
        if fm.get("estado") in {"en_revision", "mergeada"}:
            rojo, verde = evidencia_rojo_verde(texto_bug)
            if not (rojo and verde):
                falta = " ni ".join(m for m, hay in (("ROJO (§2)", rojo), ("VERDE (§5)", verde))
                                    if not hay)
                fail(f"bugs/{nombre}: {fm.get('estado')} sin el output {falta} pegado en la "
                     f"ficha — el par ROJO→VERDE del MISMO test es la única prueba de que se "
                     f"arregló ESTE bug (bug.md paso 9: evidencia, no afirmación)")
        if fm.get("estado") == "mergeada" and not validado_por_el_usuario(texto_bug):
            fail(f"bugs/{nombre}: mergeada sin 'Validación del usuario: OK' en la sección de "
                 f"cierre — un bug no está cerrado hasta que el USUARIO lo valida sobre una "
                 f"instancia corriendo; sin ese OK el bug sigue ABIERTO (bug.md, hard-gate "
                 f"del paso 9)")
        # El alta en el índice la hace el padre al reportar el bug: una ficha fuera del índice
        # es un bug invisible para quien solo mira docs/bugs/INDICE.md. WARN, no FAIL: el bug
        # existe y está bien escrito; lo que falta es su línea en el índice.
        if nombre not in texto_indice:
            warn(f"bugs/{nombre}: no aparece en docs/bugs/INDICE.md (el padre da de alta el "
                 f"bug en el índice al reportarlo: una línea con NNN, ficha, severidad, "
                 f"triaje y estado)")
        unidades[nombre] = fm  # mismo censo: tope en vuelo, ficheros disjuntos y worktrees

if unidades:
    ok(f"{len(unidades)} unidad(es) activas con frontmatter válido")
else:
    ok("sin unidades activas")

# --- 4b. Trabajo en vuelo: tope y ownership disjunto ---
activas = {n: fm for n, fm in unidades.items() if fm.get("estado") in {"en_obra", "en_revision"}}
if len(activas) > 3:
    fail(f"{len(activas)} unidades en vuelo (tope absoluto 3, default 1): {sorted(activas)}")
elif len(activas) > 1:
    warn(f"{len(activas)} unidades en vuelo (default 1; 2-3 solo sin ficheros compartidos y pedido por el usuario)")


def ficheros_de(fm):
    return {f.strip() for f in fm.get("ficheros", "").strip("[]").split(",") if f.strip()}


nombres_activas = sorted(activas)
for i, a in enumerate(nombres_activas):
    for b in nombres_activas[i + 1:]:
        comunes = ficheros_de(activas[a]) & ficheros_de(activas[b])
        if comunes:
            fail(f"{a} y {b} comparten ficheros declarados: {sorted(comunes)} (paralelas jamás comparten)")

# --- 5. Worktrees ↔ unidades (huérfanos y zombis) ---
worktrees = RAIZ / "worktrees"
wt = {p.name for p in worktrees.iterdir() if p.is_dir()} if worktrees.is_dir() else set()
en_obra = {
    n for n, fm in unidades.items()
    if fm.get("estado") in {"en_obra", "en_revision"}
    and fm.get("ejecucion") != "documental"
}
for h in sorted(wt - set(unidades)):
    fail(f"worktree huérfano sin unidad: worktrees/{h} (¿cierre a medias?)")
for z in sorted(en_obra - wt):
    warn(f"unidad {z} en obra sin worktree (¿aún no despachada de verdad?)")
if wt and not (wt - set(unidades)):
    ok(f"worktrees coherentes con unidades: {sorted(wt)}")
elif not wt:
    ok("sin worktrees")

# --- 6. Archivo: lo archivado debe estar mergeada/descartada ---
archivo = trabajo / "archivo"
for carpeta in sorted(p for p in archivo.iterdir() if p.is_dir()) if archivo.is_dir() else []:
    spec_archivada = carpeta / "especificacion.md"
    fm = frontmatter(spec_archivada)
    if fm and fm.get("estado") not in {"mergeada", "descartada"}:
        fail(f"archivo/{carpeta.name}: archivada con estado '{fm.get('estado')}' (solo mergeada/descartada)")
    if fm and spec_archivada.exists():
        revisar_deuda_hotfix(f"archivo/{carpeta.name}", spec_archivada, fm)

# --- 6b. Cosecha de hallazgos en unidades archivadas ---
# Convención: en el cierre, el padre marca CADA bullet de "Descubrimientos" y "Trabajo
# descubierto" con "→ promovido a <destino>" o "→ descartado (motivo)". Un bullet con
# contenido real sin marca = conocimiento sin cosechar → WARN (no bloquea).
for carpeta in sorted(p for p in archivo.iterdir() if p.is_dir()) if archivo.is_dir() else []:
    hallazgos = carpeta / "hallazgos.md"
    if not hallazgos.exists():
        continue
    seccion, sin_cosechar = None, 0
    for linea in hallazgos.read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            titulo = linea[3:].strip()
            seccion = titulo if titulo.startswith(("Descubrimientos", "Trabajo descubierto")) else None
        elif seccion and re.match(r"^-\s+\S", linea):
            contenido = re.sub(r"^-\s+", "", linea).strip()
            if contenido in {"—", "-", ""}:
                continue  # bullet placeholder de la plantilla
            if "→ promovido" not in linea and "→ descartado" not in linea:
                sin_cosechar += 1
    if sin_cosechar:
        warn(f"archivo/{carpeta.name}: hallazgos sin cosechar "
             f"(marca cada bullet con '→ promovido a …' o '→ descartado (motivo)')")

# --- 7. Higiene ---
if (RAIZ / "codebase").exists():
    fail("codebase/ existe (estructura vieja: debe ser main/ + worktrees/)")

# --- Resultado ---
print(f"\n{len(fallos)} FAIL · {len(avisos)} WARN")
sys.exit(1 if fallos else 0)
