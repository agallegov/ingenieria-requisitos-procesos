#!/usr/bin/env python3
"""unidad.py — el despacho de una unidad, scriptado (regla del método: script > plantilla > prosa).

Hasta hoy el ritual de despacho era prosa en `00-metodo/README.md` y en los runbooks: el padre
recordaba asignar NNN, copiar la plantilla, esperar la aprobación y crear el worktree. Esto lo
convierte en tres comandos con PRECONDICIONES que bloquean, para que las reglas duras 4 (el NNN
no se renumera), 5 (una unidad en vuelo), "la spec va antes que la rama" y "el contrato lo
aprueba el usuario" (frontmatter `aprobado:`) se cumplan solas.

Uso (desde cualquier directorio del workspace; la raíz se deriva de la ruta del script):
  python docs/00-metodo/scripts/unidad.py nnn                      siguiente NNN libre
  python docs/00-metodo/scripts/unidad.py nueva feature mi-slug    crea la unidad (sin rama)
  python docs/00-metodo/scripts/unidad.py despachar 004-mi-slug    crea rama + worktree
  python docs/00-metodo/scripts/unidad.py despachar 005-auditoria --documental
                                                                  trabaja solo en su ficha
  python docs/00-metodo/scripts/unidad.py cerrar 004-mi-slug --ok-usuario 2026-08-01
                                                                  cierra la unidad ya fusionada
  python docs/00-metodo/scripts/unidad.py estado                   resumen de un vistazo

Solo stdlib. Nada destructivo: este script crea y avisa, jamás borra ni pisa lo escrito.
Exit 0 si todo bien; exit 1 con mensaje claro si una precondición bloquea.
"""
import argparse
import datetime
import posixpath
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Windows: en cuanto la salida va a un PIPE —setup.py, la CI, cualquier harness de agente— el
# encoding deja de ser el de la consola y pasa a ser el local (cp1252), donde un `→` o un `·`
# mata el script con UnicodeEncodeError. Se fuerza UTF-8 antes de imprimir nada.
for _salida in (sys.stdout, sys.stderr):
    if hasattr(_salida, "reconfigure"):
        _salida.reconfigure(encoding="utf-8", errors="replace")

# Este script vive en docs/00-metodo/scripts/, igual que lint_metodo.py:
# parents[3] es la raíz del meta-repo sea cual sea el directorio de trabajo.
RAIZ = Path(__file__).resolve().parents[3]
TRABAJO = RAIZ / "docs/05-trabajo"
ARCHIVO = TRABAJO / "archivo"
BUGS = RAIZ / "docs/bugs"
PLANTILLAS = RAIZ / "docs/00-metodo/plantillas"
WORKTREES = RAIZ / "worktrees"

# Vocabulario cerrado: el mismo que valida lint_metodo.py. No se crean variantes.
TIPOS = ["bug", "feature", "refactor", "migracion", "auditoria", "investigacion", "documentacion"]
ESTADOS = {"planificada", "en_obra", "en_revision", "en_validacion", "mergeada", "bloqueada",
           "descartada"}
# `en_validacion` NO está en vuelo (ADR-010): su rama ya está fusionada y el trabajo de
# construcción terminó; lo único pendiente es que el usuario pruebe la app. Ocupaba cupo de
# paralelismo sin consumir atención de nadie, y eso obligaba a subir el tope para seguir
# trabajando: el problema no era el tope, era un estado que no existía.
EN_VUELO = {"en_obra", "en_revision"}
RE_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
RE_UNIDAD = re.compile(r"^(\d{3})-([a-z0-9][a-z0-9-]*)$")

# Caracteres mínimos de prosa PROPIA que debe tener el contrato para poder despacharse.
MINIMO_PROSA = 200
TOPE_EN_VUELO = 3  # regla 5: default 1, tope absoluto 3 y solo con --paralelo explícito

# El contrato lo aprueba el USUARIO, no el agente: `aprobado:` solo vale si es una fecha ISO.
# Todo lo demás (`no`, vacío, ausente, "sí", "ok") es ausencia de aprobación.
RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MARCA_DEUDA = ("> **DEUDA DE SPEC — HOTFIX**: rama creada sin contrato completo. "
               "Rellenar al estabilizar.")

HOY = datetime.date.today().isoformat()


def ok(msg):
    print(f"  OK   {msg}")


def warn(msg):
    print(f"  WARN {msg}")


def fail(msg):
    err(f"  FAIL {msg}")


def err(msg):
    """Escribe en stderr sin descolocar la salida: stdout va con búfer y stderr no."""
    sys.stdout.flush()
    print(msg, file=sys.stderr)
    sys.stderr.flush()


def rel(p):
    """Ruta relativa a la raíz para que la salida sea legible."""
    try:
        return str(Path(p).relative_to(RAIZ))
    except ValueError:
        return str(p)


# --------------------------------------------------------------------------- frontmatter y prosa

def frontmatter(path):
    """Parseo mínimo del frontmatter YAML (clave: valor). Devuelve dict o None.

    Idéntico al de lint_metodo.py a propósito: si el linter lo acepta, este script también.

    Admite las DOS formas en que se escribe una lista de verdad:

        ficheros: [api/rutas.py, api/modelos.py]      en línea
        ficheros:                                     multilínea
          - api/rutas.py
          - api/modelos.py

    Sin esto el parseo era línea a línea y una lista multilínea dejaba `ficheros` en cadena
    VACÍA: la comprobación de ficheros disjuntos comparaba conjuntos vacíos y daba el visto
    bueno siempre. Un guardián que mira de menos es peor que ninguno, porque da permiso con
    cara de haber mirado. Las listas se normalizan a "a, b" para que quien lea el valor no
    tenga que cambiar.
    """
    try:
        lineas = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lineas or lineas[0].strip() != "---":
        return None
    datos = {}
    clave_abierta, items = None, []

    def cerrar_lista():
        nonlocal clave_abierta, items
        if clave_abierta and items:
            datos[clave_abierta] = ", ".join(items)
        clave_abierta, items = None, []

    for linea in lineas[1:]:
        if linea.strip() == "---":
            cerrar_lista()
            return datos
        m = re.match(r"^(\w+):\s*(.*)$", linea)
        if m:
            cerrar_lista()
            valor = m.group(2).split("#")[0].strip()
            datos[m.group(1)] = valor
            if not valor:
                clave_abierta = m.group(1)      # puede venir una lista debajo
            continue
        item = re.match(r"^\s+-\s*(.+)$", linea)
        if item and clave_abierta:
            items.append(item.group(1).split("#")[0].strip().strip("'\""))
    return None


def ficheros_de(fm):
    """Conjunto de rutas NORMALIZADAS que declara una unidad. Mismo criterio que lint_metodo.py.

    La puerta de paralelismo compara CONJUNTOS DE CADENAS, así que `api/x.py`, `./api/x.py` y
    `API/x.py` —el mismo fichero en disco, en macOS y en Windows— eran tres rutas distintas y
    dos unidades podían declarar el mismo fichero con el visto bueno de la puerta. Y esas
    variantes no son rebuscadas: las produce solo un agente que copia rutas de contextos
    distintos. Se normaliza el separador, los `./` y las mayúsculas.

    `casefold` acerca de más en sistemas de ficheros sensibles a mayúsculas (Linux): allí
    `API/x.py` y `api/x.py` PUEDEN ser dos ficheros. Se prefiere ese error, que bloquea un
    paralelismo legítimo y raro, al contrario, que bendice un choque real.
    """
    crudos = (fm.get("ficheros") or "").strip("[]").split(",")
    limpias = set()
    for crudo in crudos:
        ruta = crudo.strip().strip("'\"")
        if not ruta:
            continue
        limpias.add(posixpath.normpath(ruta.replace("\\", "/")).casefold())
    return limpias


def aprobacion(fm):
    """Fecha de aprobación del contrato, o None si nadie lo ha aprobado todavía.

    `aprobado:` es el ÚNICO rastro de que el usuario dio su OK. Se exige fecha ISO a propósito:
    un `sí` lo teclea cualquiera sin haber leído nada, una fecha dice CUÁNDO se leyó. Y no
    puede ser futura (mismo criterio que el OK del usuario, `fecha_ok`): `aprobado: 2030-01-01`
    es lo que teclea un agente que deja "preparada" la aprobación, no un usuario que leyó.
    """
    return fecha_ok(fm.get("aprobado"))


def severidad_declarada(texto):
    """Severidad P0-P4 realmente ELEGIDA en la ficha del bug, o None.

    La plantilla trae la escalera entera en la misma línea ("P0 (producción caída) … P4
    (cosmético)"): si en el valor siguen apareciendo varios niveles, nadie ha triado aún y
    aceptar ese "P0" convertiría la válvula de hotfix en un bypass gratis.
    """
    for m in re.finditer(r"^\s*(?:[-*]\s*)?\**\s*Severidad[^:\n]*:\s*(.+)$", texto,
                         flags=re.M | re.I):
        niveles = set(re.findall(r"\bP[0-4]\b", m.group(1)))
        if len(niveles) == 1:
            return niveles.pop()
    return None


def cuerpo(texto):
    """El documento sin su frontmatter (el frontmatter son metadatos, no contrato)."""
    lineas = texto.splitlines()
    if lineas and lineas[0].strip() == "---":
        for i, linea in enumerate(lineas[1:], start=1):
            if linea.strip() == "---":
                return "\n".join(lineas[i + 1:])
    return texto


MARCADOR = re.compile(r"<[^>\n]*>")       # `<lo que hay que rellenar>`
VINETA = re.compile(r"^(?:[-*]|\d+\.)\s*(?:\[[ xX]\]\s*)?")
PLACEHOLDERS = {"", "—", "-", "…", "..."}


def prosa_real(texto, texto_plantilla):
    """Caracteres de prosa PROPIA: lo escrito por encima de la plantilla.

    Por qué no basta con "el fichero existe y es largo": la plantilla ya trae mucha prosa fija
    (Reglas del constructor, Definición de hecho, Plan de trabajo). Un fichero recién copiado
    pesa miles de caracteres sin que nadie haya escrito UNA línea de contrato. Así que se
    descuenta línea a línea todo lo que sigue siendo plantilla, y de lo que queda se ignoran
    encabezados, citas `>` (instrucciones de la plantilla), marcadores `<...>` (huecos sin
    rellenar) y viñetas vacías (`- —`). Lo que sobrevive es contrato escrito por una persona.
    """
    plantilla_lineas = {l.strip() for l in cuerpo(texto_plantilla).splitlines() if l.strip()}
    total = 0
    for linea in cuerpo(texto).splitlines():
        s = linea.strip()
        if not s or s in plantilla_lineas:
            continue                                   # vacío o idéntico a la plantilla: no aporta
        if s.startswith(("#", ">", "<", "```", "|", "---")):
            continue                                   # encabezado, cita, marcador, código o tabla
        s = MARCADOR.sub("", s)                        # huecos `<...>` embebidos: no son prosa
        s = VINETA.sub("", s).strip()                  # viñeta o casilla `- [ ]`
        if s in PLACEHOLDERS:
            continue
        total += len(s)
    return total


# --------------------------------------------------------------------------- repo de código

def repo_codigo():
    """Lee de repos.yaml la ruta local y la rama principal del repo de código.

    Parseo mínimo con regex (nada de PyYAML: el método es solo stdlib). repos.yaml es la única
    fuente de verdad de dónde vive el código; este script no la duplica.
    """
    ruta_local, rama = "main/", "main"
    cfg = RAIZ / "repos.yaml"
    if cfg.exists():
        texto = cfg.read_text(encoding="utf-8")
        m = re.search(r"^\s*ruta_local:\s*(\S+)", texto, flags=re.M)
        if m:
            ruta_local = m.group(1)
        m = re.search(r"^\s*rama_principal:\s*(\S+)", texto, flags=re.M)
        if m:
            rama = m.group(1)
    return (RAIZ / ruta_local.rstrip("/")).resolve(), rama


def git(repo, *args, silencioso=False):
    """Ejecuta git y devuelve (codigo, salida). Nunca lanza: los errores se deciden arriba."""
    try:
        p = subprocess.run(["git", "-C", str(repo), *args],
                           capture_output=True, text=True, check=False)
    except OSError as e:
        if not silencioso:
            warn(f"no se pudo ejecutar git: {e}")
        return 1, ""
    return p.returncode, (p.stdout + p.stderr).strip()


def ramas_del_codigo():
    """Nombres de rama del repo de código (locales y remotas), sin el prefijo del remoto."""
    repo, _ = repo_codigo()
    if not (repo / ".git").exists():
        return None                                    # sin clon: quien llame decide si avisa
    codigo, salida = git(repo, "branch", "-a", "--format=%(refname:short)", silencioso=True)
    if codigo != 0:
        return None
    nombres = set()
    for linea in salida.splitlines():
        nombre = linea.strip().split(" ")[0]
        if not nombre or "HEAD" in nombre:
            continue
        nombres.add(nombre.split("/")[-1])             # origin/004-x → 004-x
    return nombres


# --------------------------------------------------------------------------- censo y numeración

def censo():
    """Unidades VIVAS: carpetas de 05-trabajo/ y fichas de docs/bugs/. Devuelve {nombre: dict}."""
    unidades = {}
    if TRABAJO.is_dir():
        for carpeta in sorted(TRABAJO.iterdir()):
            if not carpeta.is_dir() or carpeta.name == "archivo":
                continue
            if not RE_UNIDAD.match(carpeta.name):
                continue
            unidades[carpeta.name] = {"ruta": carpeta / "especificacion.md",
                                      "clase": "unidad",
                                      "fm": frontmatter(carpeta / "especificacion.md") or {}}
    if BUGS.is_dir():
        for fichero in sorted(BUGS.glob("*.md")):
            if not RE_UNIDAD.match(fichero.stem):
                continue
            unidades[fichero.stem] = {"ruta": fichero,
                                      "clase": "bug",
                                      "fm": frontmatter(fichero) or {}}
    return unidades


def numeros_ocupados():
    """{NNN: [de dónde sale]} mirando TODAS las fuentes donde un número puede haberse gastado.

    Regla dura 4: el NNN lo asigna el padre y NUNCA se renumera. Por eso no vale con mirar
    05-trabajo/: un número puede estar gastado y no verse ahí porque (a) la unidad ya se cerró
    y vive en archivo/, (b) es un bug, y los bugs no se archivan ni tienen carpeta: viven en
    docs/bugs/NNN-slug.md (ADR-006), o (c) la carpeta se movió/borró pero la RAMA sigue en el
    repo de código, y una colisión ahí rompe la trazabilidad rama ↔ PR ↔ unidad. Los worktrees
    no se miran aparte: cada worktree tiene su rama, así que la fuente (c) ya los cubre.
    """
    usados = {}

    def apunta(nnn, fuente):
        usados.setdefault(nnn, []).append(fuente)

    for base, etiqueta in ((TRABAJO, "05-trabajo"), (ARCHIVO, "archivo")):
        if not base.is_dir():
            continue
        for carpeta in sorted(base.iterdir()):
            if carpeta.is_dir() and RE_UNIDAD.match(carpeta.name):
                apunta(carpeta.name[:3], f"{etiqueta}/{carpeta.name}")
    if BUGS.is_dir():
        for fichero in sorted(BUGS.glob("*.md")):
            if RE_UNIDAD.match(fichero.stem):
                apunta(fichero.stem[:3], f"bugs/{fichero.name}")
    ramas = ramas_del_codigo()
    if ramas is None:
        # Por stderr: `nnn` debe poder usarse en un $(...) sin que el aviso ensucie el número.
        err("  WARN no pude listar las ramas del repo de código (¿falta el clon en main/?): "
            "el NNN se calcula solo con lo que hay en docs/")
    else:
        for rama in sorted(ramas):
            m = RE_UNIDAD.match(rama)
            if m:
                apunta(m.group(1), f"rama {rama}")
    return usados


def siguiente_nnn():
    """Máximo ocupado + 1, a 3 dígitos. Nunca reutiliza huecos: un número gastado es historia."""
    usados = numeros_ocupados()
    maximo = max((int(n) for n in usados), default=0)
    return f"{maximo + 1:03d}", usados


def buscar_unidad(nombre):
    """Localiza una unidad por nombre NNN-slug (carpeta o ficha de bug). None si no existe."""
    return censo().get(nombre)


def slug_ya_usado(slug):
    """¿Existe ya una unidad (viva o archivada) con este slug? Devuelve su nombre o None."""
    for nombre in censo():
        if nombre[4:] == slug:
            return nombre
    if ARCHIVO.is_dir():
        for carpeta in sorted(ARCHIVO.iterdir()):
            if carpeta.is_dir() and RE_UNIDAD.match(carpeta.name) and carpeta.name[4:] == slug:
                return f"archivo/{carpeta.name}"
    return None


# --------------------------------------------------------------------------- subcomando: nnn

def cmd_nnn(args):
    nnn, usados = siguiente_nnn()
    if args.detalle:
        print("== Números ocupados ==")
        for n in sorted(usados):
            print(f"  {n}  {', '.join(usados[n])}")
        print(f"\nSiguiente NNN libre: {nnn}")
    else:
        print(nnn)
    return 0


# --------------------------------------------------------------------------- subcomando: nueva

def rellenar(texto, nombre, nnn, tipo):
    """Sustituye los marcadores obvios de la plantilla. Lo demás lo escribe una persona."""
    texto = texto.replace("NNN-slug", nombre)                       # frontmatter y rutas
    texto = texto.replace("actualizado: YYYY-MM-DD", f"actualizado: {HOY}")
    texto = re.sub(r"^# NNN ", f"# {nnn} ", texto, flags=re.M)      # encabezado del documento
    texto = re.sub(r"^tipo: \S+", f"tipo: {tipo}", texto, count=1, flags=re.M)
    return texto


def cmd_nueva(args):
    tipo, slug = args.tipo, args.slug
    if tipo not in TIPOS:
        fail(f"tipo '{tipo}' fuera del vocabulario cerrado: {' | '.join(TIPOS)}")
        return 1
    if not RE_SLUG.match(slug):
        fail(f"slug '{slug}' inválido: debe casar con ^[a-z0-9][a-z0-9-]*$ "
             "(minúsculas, números y guiones; sin acentos ni espacios)")
        return 1

    # Idempotencia: si ya hay una unidad con este slug, no se crea otra ni se pisa nada.
    ya = slug_ya_usado(slug)
    if ya:
        warn(f"ya existe una unidad con el slug '{slug}': {ya} — no toco nada")
        print(f"\n  Si de verdad es trabajo NUEVO, usa otro slug. Si quieres despacharla:\n"
              f"      python {rel(__file__)} despachar {Path(ya).name}")
        return 0

    nnn, _ = siguiente_nnn()
    nombre = f"{nnn}-{slug}"

    if tipo == "bug":
        # ADR-006: el bug es un fichero vivo en docs/bugs/, sin carpeta y sin archivarse.
        plantilla = PLANTILLAS / "bug.md"
        destino = BUGS / f"{nombre}.md"
        if destino.exists():
            warn(f"{rel(destino)} ya existe — no toco nada")
            return 0
        if not plantilla.exists():
            fail(f"falta la plantilla {rel(plantilla)}")
            return 1
        BUGS.mkdir(parents=True, exist_ok=True)
        destino.write_text(rellenar(plantilla.read_text(encoding="utf-8"), nombre, nnn, tipo),
                           encoding="utf-8")
        creados = [destino]
        fichero_contrato = destino
    else:
        carpeta = TRABAJO / nombre
        if carpeta.exists():
            warn(f"{rel(carpeta)} ya existe — no toco nada")
            return 0
        faltan = [p for p in ("especificacion.md", "hallazgos.md") if not (PLANTILLAS / p).exists()]
        if faltan:
            fail(f"faltan plantillas en {rel(PLANTILLAS)}: {faltan}")
            return 1
        carpeta.mkdir(parents=True)
        creados = []
        for origen, nombre_destino in (("especificacion.md", "especificacion.md"),
                                       ("hallazgos.md", "hallazgos.md")):
            destino = carpeta / nombre_destino
            destino.write_text(
                rellenar((PLANTILLAS / origen).read_text(encoding="utf-8"), nombre, nnn, tipo),
                encoding="utf-8")
            creados.append(destino)
        fichero_contrato = carpeta / "especificacion.md"

    print(f"== Unidad {nombre} creada ({tipo}) ==")
    for c in creados:
        ok(f"creado {rel(c)}")
    print(f"\n  Siguientes pasos (en este orden — el worktree NO se crea todavía):\n"
          f"    1. Rellena el contrato en {rel(fichero_contrato)}\n"
          f"       (Qué · Criterios R* · Deltas al mapa · Verificación · ficheros que posee).\n"
          f"    2. <HARD-GATE> El usuario lee, anota y APRUEBA el contrato; su OK se escribe\n"
          f"       como 'aprobado: YYYY-MM-DD' en el frontmatter. Sin esa fecha no hay despacho.\n"
          f"    3. Rellena Contexto para el constructor y Plan de trabajo.\n"
          f"    4. python {rel(__file__)} despachar {nombre}\n"
          f"    5. Registra la unidad en ESTADO.md"
          f"{' e INDICE.md de bugs' if tipo == 'bug' else ''} (lo escribe el padre).")
    return 0


# --------------------------------------------------------------------------- subcomando: despachar

def marcar_deuda(ruta, motivo):
    """Escribe la marca de deuda de spec y la emergencia declarada, tras el frontmatter.

    Idempotente. El motivo se guarda AQUÍ y no en un log aparte porque la ficha es lo único
    que el linter, el revisor y el usuario van a leer después: una emergencia sin nombre
    escrito es indistinguible de un atajo.
    """
    texto = ruta.read_text(encoding="utf-8")
    if "DEUDA DE SPEC" in texto:
        return False
    lineas = texto.splitlines()
    corte = 0
    if lineas and lineas[0].strip() == "---":
        for i, linea in enumerate(lineas[1:], start=1):
            if linea.strip() == "---":
                corte = i + 1
                break
    lineas[corte:corte] = ["", MARCA_DEUDA,
                           f"> **Emergencia declarada por el usuario ({HOY}):** {motivo}",
                           "> Deuda a pagar en 24 h (runbook `hotfix.md`); el linter la vigila."]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return True


def marcar_en_obra(ruta, documental=False):
    """estado → en_obra y actualizado → hoy: el despacho es lo que pone la unidad en obra."""
    texto = ruta.read_text(encoding="utf-8")
    texto = re.sub(r"^estado:\s*\S+", "estado: en_obra", texto, count=1, flags=re.M)
    texto = re.sub(r"^actualizado:\s*\S+", f"actualizado: {HOY}", texto, count=1, flags=re.M)
    if documental and not re.search(r"^ejecucion:", texto, flags=re.M):
        texto = texto.replace(
            "\n---\n", "\nejecucion: documental\n---\n", 1
        )
    ruta.write_text(texto, encoding="utf-8")


def preparar_worktree(destino):
    """Gancho OPCIONAL del proyecto: `worktree-listo` en la raíz del meta-repo.

    Un worktree recién creado es código sin entorno: sin dependencias instaladas, sin base de
    datos de pruebas, sin lo que el stack necesite. El constructor que aterriza ahí ve fallar
    tests que en main pasan, y los usa como vara de medir durante horas antes de descubrir que
    medía el entorno. El método no sabe montar eso —depende del stack— pero sí sabe CUÁNDO hay
    que montarlo: justo aquí.

    Si el proyecto deja `worktree-listo` (ejecutable) o `worktree-listo.py` en la raíz, se
    ejecuta con el worktree como argumento y como directorio de trabajo. Es del proyecto, no
    del método: ninguna actualización del método lo toca.
    """
    for nombre in ("worktree-listo", "worktree-listo.py"):
        gancho = RAIZ / nombre
        if not gancho.is_file():
            continue
        orden = [sys.executable, str(gancho)] if gancho.suffix == ".py" else [str(gancho)]
        print(f"\n  Preparando el entorno del worktree con {nombre}…", flush=True)
        try:
            codigo = subprocess.run([*orden, str(destino)], cwd=str(destino)).returncode
        except OSError as e:
            warn(f"no pude ejecutar {nombre} ({e}): el worktree existe pero su entorno no "
                 f"está preparado")
            return
        if codigo:
            warn(f"{nombre} terminó con código {codigo}: el worktree existe, pero su entorno "
                 f"puede estar a medias — arréglalo ANTES de lanzar al constructor, o medirá "
                 f"el entorno y creerá que mide su código")
        else:
            ok(f"entorno del worktree preparado por {nombre}")
        return


def cmd_despachar(args):
    nombre = args.unidad.strip("/")
    if not RE_UNIDAD.match(nombre):
        fail(f"'{nombre}' no tiene forma NNN-slug (tres dígitos, guion, slug)")
        return 1

    # --- Precondición 1: la unidad existe y su frontmatter es válido -----------------------
    unidad = buscar_unidad(nombre)
    if unidad is None:
        fail(f"no existe la unidad {nombre} (ni carpeta en 05-trabajo/ ni ficha en docs/bugs/)")
        err(f"\n  Créala primero:  python {rel(__file__)} nueva <tipo> {nombre[4:]}")
        return 1
    ruta, fm = unidad["ruta"], unidad["fm"]
    if not fm:
        fail(f"{rel(ruta)} no tiene frontmatter válido (debe abrir con --- y cerrar con ---)")
        return 1
    if fm.get("unidad") != nombre:
        fail(f"{rel(ruta)}: el frontmatter dice unidad '{fm.get('unidad')}' y la carpeta/ficha "
             f"dice '{nombre}' — arréglalo antes de despachar")
        return 1
    if fm.get("tipo") not in TIPOS:
        fail(f"{rel(ruta)}: tipo '{fm.get('tipo')}' fuera del vocabulario cerrado")
        return 1
    if fm.get("estado") not in ESTADOS:
        fail(f"{rel(ruta)}: estado '{fm.get('estado')}' fuera del vocabulario cerrado")
        return 1
    ok(f"{nombre} existe con frontmatter válido ({fm.get('tipo')} · {fm.get('estado')})")

    if args.documental and fm.get("tipo") not in {
        "auditoria", "investigacion", "documentacion", "bug"
    }:
        fail(
            "--documental solo vale para auditoria, investigacion, documentacion "
            "o un bug del META-repo que NO toca el repositorio de código"
        )
        return 1
    if args.documental and fm.get("tipo") == "bug":
        rutas_bug = ficheros_de(fm)
        if not rutas_bug:
            fail(f"{nombre}: --documental en un bug exige declarar `ficheros:` en la ficha "
                 f"(al menos una ruta dentro de docs/, para demostrar que es del meta-repo "
                 f"y no del código)")
            return 1
        meta = [r for r in rutas_bug if r.startswith("docs/")]
        if not meta:
            fail(f"{nombre}: --documental en un bug con ficheros TODOS fuera de docs/ — "
                 f"un bug que toca el repositorio de código se despacha SIN --documental")
            return 1
        if any(not r.startswith("docs/") for r in rutas_bug):
            warn(f"{nombre}: bug meta con ficheros MIXTOS docs/ y código — el worktree de "
                 f"código NO se crea (la parte de código la trabaja el subagente sin rama)")
        ok(f"{nombre}: bug del meta-repo confirmado — ficheros dentro de docs/")
    if args.documental and args.force:
        fail("--documental no se combina con --force; un hotfix siempre toca código")
        return 1

    texto_unidad = ruta.read_text(encoding="utf-8")

    # --- Precondición 2: si se invoca --force, que sea de verdad una emergencia --------------
    # --force es la ÚNICA válvula que salta las puertas 3 (aprobación) y 4 (contrato escrito),
    # y por eso se acota a lo que `hotfix.md` permite: producción caída. Sin las tres cosas
    # (bug + P0 triado + motivo escrito) no es una emergencia, es un atajo con otro nombre.
    motivo = (args.motivo or "").strip()
    if args.force:
        severidad = severidad_declarada(texto_unidad)
        problemas = []
        if fm.get("tipo") != "bug":
            problemas.append(f"la unidad es tipo '{fm.get('tipo')}', y un hotfix es SIEMPRE "
                             f"un bug (plantillas/bug.md → docs/bugs/)")
        if severidad != "P0":
            problemas.append(f"la ficha no declara severidad P0 "
                             f"(leído: {severidad or 'sin triar'}) — P0 es producción caída "
                             f"para usuarios reales, no 'urgente'")
        if not motivo:
            problemas.append("falta --motivo: la emergencia se escribe en la ficha con "
                             "nombre y apellidos")
        if problemas:
            fail(f"--force rechazado para {nombre}: no es un hotfix")
            for p in problemas:
                err(f"       · {p}")
            err(f"\n  --force NO es un bypass de la aprobación: es la válvula de producción\n"
                f"  caída, y solo el usuario declara la emergencia. Lee\n"
                f"  {rel(RAIZ / 'docs/00-metodo/runbooks/hotfix.md')}.\n"
                f"  Si de verdad hay sangría:\n"
                f"      python {rel(__file__)} despachar {nombre} --force "
                f"--motivo \"produccion caida: ...\"\n"
                f"  Si no la hay, es un bug normal: rellena la ficha, que el usuario la\n"
                f"  apruebe (aprobado: {HOY}) y despacha sin --force.")
            return 1
        warn(f"--force aceptado: bug P0 con emergencia declarada — «{motivo}»")

    # --- Precondición 3: el usuario ha aprobado el contrato (regla dura: lo aprueba él) ------
    aprobado = aprobacion(fm)
    if aprobado is None and not args.force:
        fail(f"{rel(ruta)}: sin aprobación del usuario (aprobado: "
             f"{fm.get('aprobado') or 'ausente'})")
        err(f"\n  EL CONTRATO LO APRUEBA EL USUARIO, NO EL AGENTE. Que la spec esté escrita\n"
            f"  no la convierte en acordada: la escribió el mismo que quiere despacharla.\n"
            f"  Para desbloquear: enséñale el contrato al usuario y, cuando dé su OK, que\n"
            f"  quede escrita la fecha en el frontmatter de {rel(ruta)}:\n"
            f"      aprobado: {HOY}\n"
            f"  Producción caída (bug P0): runbooks/hotfix.md → --force --motivo \"...\".")
        return 1
    if aprobado:
        ok(f"contrato aprobado por el usuario el {aprobado}")

    # --- Precondición 4: el contrato está escrito (la spec va antes que la rama) -------------
    plantilla = PLANTILLAS / ("bug.md" if unidad["clase"] == "bug" else "especificacion.md")
    texto_plantilla = ""
    if plantilla.exists():
        # Se compara contra la plantilla YA RELLENADA con los datos de esta unidad (NNN, slug,
        # tipo, fecha): si no, esas mismas líneas dejarían de casar y contarían como prosa.
        texto_plantilla = rellenar(plantilla.read_text(encoding="utf-8"),
                                   nombre, nombre[:3], fm.get("tipo", ""))
    prosa = prosa_real(texto_unidad, texto_plantilla)
    if prosa < MINIMO_PROSA:
        if not args.force:
            fail(f"{rel(ruta)} sigue siendo la plantilla: solo {prosa} caracteres de prosa propia "
                 f"(mínimo {MINIMO_PROSA})")
            que_falta = ("el Reporte: qué esperaba el usuario, qué pasa de verdad (con ejemplo\n"
                         "  concreto), severidad y triaje"
                         if unidad["clase"] == "bug" else
                         "el Qué, los criterios R*, los deltas al mapa y la\n  verificación")
            err(f"\n  LA SPEC VA ANTES QUE LA RAMA. Sin contrato escrito y aprobado por el\n"
                f"  usuario no hay worktree: un constructor sin contrato inventa el suyo.\n"
                f"  Rellena en {rel(ruta)} {que_falta};\n"
                f"  después vuelve a ejecutar este comando.\n"
                f"  Producción caída: solo un bug P0 con --force --motivo \"...\" (hotfix.md),\n"
                f"  y la deuda se paga en 24 h.")
            return 1
        err(f"  WARN --force: despacho SIN contrato completo ({prosa}/{MINIMO_PROSA} caracteres "
            f"de prosa).")
    else:
        ok(f"contrato escrito ({prosa} caracteres de prosa propia ≥ {MINIMO_PROSA})")

    # La marca se escribe SIEMPRE que se acepta --force, tenga o no prosa la ficha: lo que se
    # ha saltado (la aprobación previa del usuario) es deuda igual, y sin marca el linter no
    # puede vigilarla.
    if args.force:
        if marcar_deuda(ruta, motivo):
            ok(f"deuda de hotfix y emergencia declarada escritas en {rel(ruta)}")
        else:
            warn(f"{rel(ruta)} ya tenía marca de deuda sin pagar: no la piso "
                 f"(págala antes de abrir más trabajo — hotfix.md)")

    # --- Precondición 5: trabajo en vuelo (regla 5: UNA unidad por defecto) ------------------
    activas = sorted(n for n, u in censo().items()
                     if n != nombre and u["fm"].get("estado") in EN_VUELO)
    if activas and not args.paralelo:
        fail(f"ya hay {len(activas)} unidad(es) en vuelo: {', '.join(activas)}")
        err(f"\n  Regla 5: UNA unidad en vuelo por defecto — el límite real es la atención, no\n"
            f"  la máquina. Cierra la que está en obra, o repite con --paralelo si esta unidad\n"
            f"  NO comparte ningún fichero con ella (declarado en el frontmatter 'ficheros').")
        return 1
    if len(activas) >= TOPE_EN_VUELO:
        fail(f"{len(activas)} unidades en vuelo: {', '.join(activas)} — tope absoluto "
             f"{TOPE_EN_VUELO}, ni con --paralelo")
        return 1
    # La regla "en paralelo jamás se comparten ficheros" la comprobaba un WARN dirigido a un
    # humano, o sea a nadie: se despachaban dos unidades sobre el mismo fichero sin que nada
    # avisara. Aquí se verifica y se bloquea. Una unidad --documental no toca el repo de
    # código, así que no tiene ficheros que declarar y queda fuera de la comprobación.
    if activas and not args.documental:
        mios = ficheros_de(fm)
        censo_actual = censo()
        if not mios:
            fail(f"{rel(ruta)}: 'ficheros:' vacío y hay trabajo en vuelo ({', '.join(activas)})")
            err("\n  Para trabajar en paralelo hay que declarar qué ficheros POSEE esta unidad:\n"
                "  sin declaración no hay forma de comprobar que no pisáis lo mismo, y el\n"
                "  guardián daría el visto bueno sin haber mirado nada.\n"
                "      ficheros: [ruta/uno.py, ruta/dos.py]")
            return 1
        for otra in activas:
            comunes = mios & ficheros_de(censo_actual[otra]["fm"])
            if comunes:
                fail(f"{nombre} y {otra} comparten ficheros declarados: {sorted(comunes)}")
                err("\n  Dos unidades en paralelo JAMÁS comparten fichero: el segundo merge\n"
                    "  llega a un fichero que ya no es el que leyó su constructor. Los hotspots\n"
                    "  (migraciones, rutas, modelos compartidos, manifiestos, lockfiles) van\n"
                    "  SIEMPRE en secuencia: cierra una, o quítale el fichero a esta unidad y\n"
                    "  que lo proponga en hallazgos.md para que lo aplique el padre al cerrar.")
                return 1
        ok(f"ficheros disjuntos de {', '.join(activas)} ({len(mios)} declarado(s))")
    elif activas:
        warn(f"despacho documental en paralelo con: {', '.join(activas)} (no toca código)")
    else:
        ok("no hay ninguna otra unidad en vuelo")

    if args.documental:
        marcar_en_obra(ruta, documental=True)
        ok(f"{rel(ruta)}: estado → en_obra · ejecución documental (sin rama ni worktree)")
        print(
            "\n  Siguientes pasos:\n"
            f"    1. Lanza el subagente documental con {rel(ruta)} como punto de entrada.\n"
            "       Solo puede leer main/ y escribir en la carpeta de esta unidad.\n"
            "    2. Actualiza ESTADO.md con la unidad en obra (lo escribe el padre).\n"
            f"    3. python {rel(RAIZ / 'docs/00-metodo/scripts/lint_metodo.py')}"
        )
        return 0

    # --- Precondición 6: el repo de código está listo y la rama/worktree no existen ----------
    repo, rama_principal = repo_codigo()
    if git(repo, "rev-parse", "--is-inside-work-tree", silencioso=True)[0] != 0:
        fail(f"no encuentro el clon del repo de código en {rel(repo)} (repos.yaml → ruta_local)")
        err("\n  Ejecuta primero:  python setup.py")
        return 1
    tiene_origin = git(
        repo, "remote", "get-url", "origin", silencioso=True
    )[0] == 0
    if tiene_origin:
        codigo, salida = git(repo, "fetch", "origin", rama_principal)
        if codigo != 0:
            fail(
                f"no pude actualizar origin/{rama_principal}; no creo trabajo desde "
                f"una referencia posiblemente antigua:\n{salida}"
            )
            return 1
        ok(f"origin/{rama_principal} actualizado antes de crear la rama")
    destino = WORKTREES / nombre
    if destino.exists():
        fail(f"{rel(destino)} ya existe — no piso worktrees (¿cierre a medias?)")
        return 1
    if git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{nombre}", silencioso=True)[0] == 0:
        fail(f"la rama '{nombre}' ya existe en {rel(repo)} — el NNN no se reutiliza")
        return 1
    base_remota = f"origin/{rama_principal}"
    if git(repo, "rev-parse", "--verify", "--quiet",
           f"refs/remotes/{base_remota}", silencioso=True)[0] == 0:
        base = base_remota
    elif git(repo, "rev-parse", "--verify", "--quiet",
             f"refs/heads/{rama_principal}", silencioso=True)[0] == 0:
        base = rama_principal
    else:
        fail(f"no existe la rama principal '{rama_principal}' en {rel(repo)}")
        err("\n  Crea o recupera la rama principal antes de despachar trabajo.")
        return 1
    ok(f"repo de código listo en {rel(repo)} (base: {base})")

    # --- Acción: rama + worktree ------------------------------------------------------------
    WORKTREES.mkdir(parents=True, exist_ok=True)
    codigo, salida = git(repo, "worktree", "add", str(destino), "-b", nombre, base)
    if codigo != 0:
        fail(f"git worktree add falló:\n{salida}")
        return 1
    ok(f"worktree {rel(destino)} en la rama {nombre}")
    preparar_worktree(destino)
    marcar_en_obra(ruta)
    ok(f"{rel(ruta)}: estado → en_obra · actualizado → {HOY}")

    print(f"\n  Siguientes pasos:\n"
          f"    1. Lanza el subagente constructor con {rel(ruta)} como punto de entrada\n"
          f"       (trabaja SOLO en {rel(destino)}; la tarea es autocontenida).\n"
          f"    2. Actualiza ESTADO.md con la unidad en obra (lo escribe el padre).\n"
          f"    3. python {rel(RAIZ / 'docs/00-metodo/scripts/lint_metodo.py')}")
    return 0


# --------------------------------------------------------------------------- subcomando: cerrar

# La línea de veredicto de hallazgos.md y la de revisión de una ficha de bug. Si el valor
# conserva el menú de la plantilla ("LIMPIO | HUECOS DE CORRECCIÓN"), nadie ha revisado nada:
# mismo truco que `severidad_declarada`, porque una plantilla intacta no es una decisión.
RE_VEREDICTO = re.compile(r"^\s*[-*]?\s*\**\s*(?:Veredicto|Revisi[oó]n)[^:\n]*:\s*(.+)$",
                          re.M | re.I)
# Marca de cosecha, tolerante al énfasis markdown: `→ promovido a X` y `→ **descartado** (…)`.
RE_COSECHA = re.compile(r"→\s*\**\s*(promovido|descartado)", re.I)
LINEA_OK_USUARIO = "- **Validación del usuario sobre la app corriendo:**"


def fecha_ok(valor):
    """Fecha ISO real y no futura, o None. El OK del usuario no se firma por adelantado."""
    valor = (valor or "").strip().strip("`'\"")
    if not RE_FECHA.match(valor):
        return None
    try:
        dia = datetime.date.fromisoformat(valor)
    except ValueError:
        return None
    return None if dia > datetime.date.today() else valor


def veredicto_elegido(texto):
    """El veredicto de la revisión, o None si sigue siendo el menú de la plantilla."""
    for m in RE_VEREDICTO.finditer(texto):
        valor = m.group(1).strip().strip("*").strip()   # `**Veredicto:** LIMPIO` → `LIMPIO`
        if "|" in valor or not valor or valor in {"—", "-"}:
            continue                                   # menú sin elegir o hueco vacío
        return valor
    return None


def sin_cosechar(texto):
    """Viñetas con contenido y sin marca de cosecha en las dos secciones que se cosechan.

    Se mira la viñeta ENTERA —su línea y las indentadas que la continúan—, porque la
    conclusión ("→ promovido a X") cae de forma natural al final de una viñeta larga.
    """
    pendientes, en_seccion, bloque = 0, False, None

    def cerrar_bloque():
        nonlocal pendientes, bloque
        if bloque:
            entero = "\n".join(bloque)
            contenido = re.sub(r"^\s*[-*]\s+", "", entero).strip()
            if contenido not in {"—", "-", ""} and not RE_COSECHA.search(entero):
                pendientes += 1
        bloque = None

    for linea in texto.splitlines():
        if linea.startswith("#"):
            cerrar_bloque()
            titulo = linea.lstrip("#").strip()
            en_seccion = titulo.startswith(("Descubrimientos", "Trabajo descubierto"))
        elif en_seccion and re.match(r"^[-*]\s+\S", linea):
            cerrar_bloque()
            bloque = [linea]
        elif bloque is not None and re.match(r"^\s+\S", linea):
            bloque.append(linea)
        elif linea.strip():
            cerrar_bloque()
    cerrar_bloque()
    return pendientes


def sha_de(repo, referencia):
    """El SHA de una referencia (rama, remoto o SHA suelto), o None si no existe en el repo."""
    if not referencia:
        return None
    codigo, salida = git(repo, "rev-parse", "--verify", "--quiet", f"{referencia}^{{commit}}",
                         silencioso=True)
    return salida.strip() if codigo == 0 and salida.strip() else None


def base_principal(repo, principal):
    """La rama contra la que se mide la fusión: la principal local, o la del remoto."""
    if sha_de(repo, f"refs/heads/{principal}"):
        return principal
    if sha_de(repo, f"refs/remotes/origin/{principal}"):
        return f"origin/{principal}"
    return None


def rama_mergeada(repo, rama, principal, fusion_declarada=""):
    """(mergeada, motivo, prueba_fuerte, sha). Prueba de que el trabajo está en la principal.

    Antes, que la rama no existiera se tomaba como prueba de que ya se había fusionado, para
    poder reanudar un cierre a medias. Es exactamente lo contrario: la forma NORMAL de perder
    trabajo es un `git branch -D` sobre una rama sin fusionar —que es lo que el propio git
    sugiere cuando `-d` se queja— y el cierre lo archivaba como `mergeada`, con acta de que se
    entregó. Ausencia de rama no es prueba de nada.

    Se buscan pruebas de verdad, en orden de fiabilidad, y basta con que una diga que sí:

      1. la rama local,
      2. `origin/<rama>` — que ya no se borra en el cierre, justo para esto,
      3. el SHA que este mismo cierre anotó (`fusion:`) o el que declara `--fusion`,
      4. como último recurso, un commit de la principal que NOMBRE a la unidad: es la huella
         que deja un squash merge, donde el commit original no queda como ancestro de nada.
         Es prueba débil y se dice que lo es; sirve para no bloquear un flujo legítimo.

    Sin ninguna de las cuatro, FAIL: cerrar ahí es firmar una entrega que no existe.
    """
    base = base_principal(repo, principal)
    if base is None:
        return False, f"no encuentro la rama principal '{principal}' en el repo de código", \
            False, ""

    # Si la rama LOCAL existe, manda ella y nadie más: es la que tiene el trabajo más nuevo.
    # Mirar además `origin/<rama>` aquí bendeciría un cierre con la foto vieja del remoto
    # mientras quedan commits locales sin fusionar. Los otros dos rastros solo entran en juego
    # cuando la rama ya no está, que es justo el agujero que se está tapando.
    if sha_de(repo, f"refs/heads/{rama}"):
        candidatos = [(f"refs/heads/{rama}", f"la rama {rama}")]
    else:
        candidatos = [(f"refs/remotes/origin/{rama}", f"origin/{rama}")]
        if fusion_declarada:
            candidatos.append((fusion_declarada, f"el commit anotado {fusion_declarada[:8]}"))

    vivos = [(sha, etiqueta) for sha, etiqueta in
             ((sha_de(repo, ref), etiqueta) for ref, etiqueta in candidatos) if sha]
    for sha, etiqueta in vivos:
        if git(repo, "merge-base", "--is-ancestor", sha, base, silencioso=True)[0] == 0:
            return True, f"{etiqueta} está dentro de {base} ({sha[:8]})", True, sha

    # Ninguna referencia viva es ancestro de la principal. Antes de bloquear, la huella del
    # squash: el método exige NNN-slug en el título del PR, y el squash lo hereda como asunto.
    codigo, salida = git(repo, "log", base, f"--grep={rama}", "--format=%H %s", "-1",
                         silencioso=True)
    if codigo == 0 and salida.strip():
        sha, _, asunto = salida.strip().partition(" ")
        return True, (f"prueba INDIRECTA: {base} tiene «{sha[:8]} {asunto}», que nombra a "
                      f"{rama} (huella típica de un squash merge). Ninguna referencia de la "
                      f"unidad es ancestro de {base}"), False, sha

    if vivos:
        etiquetas = " ni ".join(etiqueta for _, etiqueta in vivos)
        return False, (f"{etiquetas} NO está fusionada en {base}: cerrar ahora dejaría el "
                       f"trabajo fuera de la rama principal (que es perderlo)"), False, ""
    return False, (f"no queda NI UNA prueba de que {rama} se fusionara en {base}: ni la rama "
                   f"local, ni origin/{rama}, ni un 'fusion:' anotado en la ficha, ni un "
                   f"commit de {base} que la nombre. Una rama que ya no existe NO prueba que "
                   f"se fusionara: prueba que alguien la borró. Recupérala (git reflog) o, si "
                   f"sabes con qué commit entró, cierra con --fusion <sha>"), False, ""


def anotar_fusion(ruta, sha):
    """Deja el commit que probó la fusión en el frontmatter, ANTES de borrar nada.

    Es la única forma de que un cierre reanudado —o uno en un proyecto sin remoto, donde no
    hay `origin/<rama>` que mirar— siga teniendo prueba después de que desaparezca la rama.
    """
    if not sha:
        return False
    texto = ruta.read_text(encoding="utf-8")
    if re.search(r"^fusion:\s*\S", texto, flags=re.M):
        return False
    lineas = texto.splitlines()
    if not lineas or lineas[0].strip() != "---":
        return False
    for i, linea in enumerate(lineas[1:], start=1):
        if linea.strip() == "---":
            lineas.insert(i, f"fusion: {sha}")
            ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
            return True
    return False


def escribir_ok_usuario(ruta, fecha):
    """Deja escrito el OK del usuario donde ya se lee la revisión. Sin vocabulario nuevo."""
    texto = ruta.read_text(encoding="utf-8")
    if LINEA_OK_USUARIO in texto:
        texto = re.sub(re.escape(LINEA_OK_USUARIO) + r".*",
                       f"{LINEA_OK_USUARIO} OK ({fecha})", texto, count=1)
    elif re.search(r"^\s*[-*]\s*\**Validaci[oó]n del usuario", texto, flags=re.M | re.I):
        texto = re.sub(r"^(\s*[-*]\s*\**Validaci[oó]n del usuario[^:\n]*:\**)\s*.*",
                       rf"\1 OK ({fecha})", texto, count=1, flags=re.M | re.I)
    else:
        texto = texto.rstrip("\n") + f"\n{LINEA_OK_USUARIO} OK ({fecha})\n"
    ruta.write_text(texto, encoding="utf-8")


def borrar_worktree(repo, destino):
    """Quita el worktree. Se ha comprobado antes que no tiene cambios: --force solo vence a
    los ficheros IGNORADOS (node_modules, .venv, build/), que `git status` no ve y que en un
    proyecto real siempre están ahí. Sin esto el comando no valdría fuera de un repo de juguete."""
    if not destino.exists():
        return True, "ya no existía"
    codigo, salida = git(repo, "worktree", "remove", str(destino))
    if codigo == 0:
        return True, "borrado"
    codigo, salida = git(repo, "worktree", "remove", "--force", str(destino))
    if codigo == 0:
        return True, "borrado (tenía ficheros ignorados dentro)"
    if destino.exists():
        shutil.rmtree(destino, ignore_errors=True)
        git(repo, "worktree", "prune")
    return (not destino.exists()), salida


def cmd_cerrar(args):
    nombre = args.unidad.strip("/")
    if not RE_UNIDAD.match(nombre):
        fail(f"'{nombre}' no tiene forma NNN-slug (tres dígitos, guion, slug)")
        return 1
    unidad = buscar_unidad(nombre)
    if unidad is None:
        fail(f"no existe la unidad {nombre} (¿ya está cerrada y archivada?)")
        return 1
    ruta, fm, clase = unidad["ruta"], unidad["fm"], unidad["clase"]
    estado = fm.get("estado")
    if estado not in {"en_revision", "en_validacion", "mergeada"}:
        fail(f"{nombre} está '{estado}': solo se cierra lo que está en_revision "
             f"(o 'en_validacion'/'mergeada', para reanudar un cierre que quedó a medias)")
        return 1

    print(f"== Cerrando {nombre} ({fm.get('tipo')}) ==\n")
    print("Puertas (lo que NO se puede saltar):")
    problemas = []

    # --- Puerta 1: el usuario ha probado la app y ha dado su OK -----------------------------
    # No entra en `problemas` a propósito (ADR-010): es lo único de esta lista que no depende
    # del agente. Si TODO lo demás está en verde y solo falta esto, la unidad no se queda
    # bloqueada ocupando cupo: pasa a `en_validacion` y libera el sitio.
    ok_usuario = fecha_ok(args.ok_usuario)
    if ok_usuario:
        ok(f"OK del usuario sobre la app corriendo: {ok_usuario}")

    # --- Puerta 2: la revisión fresca existe y dice algo -------------------------------------
    hallazgos = ruta.parent / "hallazgos.md" if clase == "unidad" else ruta
    texto_hallazgos = hallazgos.read_text(encoding="utf-8") if hallazgos.exists() else ""
    fm_hallazgos = frontmatter(hallazgos) or {} if clase == "unidad" else fm
    if not texto_hallazgos:
        problemas.append(f"no encuentro {rel(hallazgos)}")
    else:
        veredicto = veredicto_elegido(texto_hallazgos)
        if not veredicto:
            problemas.append(
                f"{rel(hallazgos)}: la revisión sigue sin veredicto (la línea conserva el menú "
                f"de la plantilla). El paso 2 del cierre es un agente FRESCO leyendo el diff "
                f"contra el contrato; sin eso no hay nada que cerrar")
        else:
            ok(f"revisión con veredicto: {veredicto[:60]}")
        if clase == "unidad":
            revisor = (fm_hallazgos.get("revisor") or "").strip()
            revisado = fecha_ok(fm_hallazgos.get("revisado"))
            if revisor.lower() in {"", "no"} or not revisado:
                problemas.append(
                    f"{rel(hallazgos)}: falta 'revisor:' y/o 'revisado: YYYY-MM-DD' en su "
                    f"cabecera — es lo que distingue una revisión de verdad de un constructor "
                    f"que se puso un sello a sí mismo. Si la revisión ocurrió pero nadie firmó, "
                    f"NO rellenes la cabecera de memoria: eso es inventarse la firma. Se vuelve "
                    f"a revisar con un agente fresco")
            else:
                ok(f"revisado por {revisor} el {revisado}")

    # --- Puerta 3: un hotfix no se cierra con el contrato a deber ----------------------------
    # `despachar --force` deja la marca de deuda y hotfix.md da 24 h para pagarla. Si se cierra
    # sin pagarla nadie vuelve a mirarla: el FAIL del linter se quedaría para siempre sobre una
    # unidad ya archivada. La puerta va ANTES del cierre, que es cuando aún se puede pagar.
    if MARCA_DEUDA.split(":")[0] in ruta.read_text(encoding="utf-8"):
        problemas.append(
            "esta unidad conserva la DEUDA DE SPEC del hotfix: se despachó sin contrato "
            "completo y hotfix.md da 24 h para escribirlo. Complétalo y borra la marca antes "
            "de cerrar — después de cerrar, nadie vuelve a pagarla")

    # --- Puerta 4: no queda trabajo sin guardar en el worktree -------------------------------
    repo, principal = repo_codigo()
    destino = WORKTREES / nombre
    documental = fm.get("ejecucion") == "documental"
    if destino.exists():
        codigo, salida = git(destino, "status", "--porcelain")
        if codigo == 0 and salida:
            problemas.append(
                f"worktrees/{nombre} tiene {len(salida.splitlines())} fichero(s) sin commitear: "
                f"cerrar ahora los borra y no hay copia en ningún sitio")
        elif codigo == 0:
            ok(f"worktrees/{nombre} sin cambios pendientes")

    # --- Puerta 5: la rama está fusionada en la principal ------------------------------------
    hay_repo = git(repo, "rev-parse", "--is-inside-work-tree", silencioso=True)[0] == 0
    sha_fusion = ""
    if documental:
        ok("unidad documental: sin rama ni worktree que comprobar")
    elif not hay_repo:
        problemas.append(f"no encuentro el repo de código en {rel(repo)} (repos.yaml)")
    else:
        fusionada, motivo, fuerte, sha_fusion = rama_mergeada(
            repo, nombre, principal, args.fusion or fm.get("fusion", ""))
        if not fusionada:
            problemas.append(motivo)
        else:
            (ok if fuerte else warn)(motivo)

    if problemas:
        err(f"\n  CIERRE BLOQUEADO ({len(problemas)}):")
        for p in problemas:
            err(f"       · {p}")
        err("\n  El cierre es indivisible: se arregla lo de arriba y se vuelve a ejecutar.")
        return 1

    # La prueba de la fusión se escribe ANTES de tocar nada, y vale para los dos caminos: si
    # este cierre se queda en `en_validacion` y días después alguien borra la rama, la ficha
    # sigue sabiendo con qué commit entró el trabajo.
    if sha_fusion and anotar_fusion(ruta, sha_fusion):
        ok(f"prueba de fusión anotada en {rel(ruta)} (fusion: {sha_fusion[:8]})")

    # --- Cierre parcial: todo hecho salvo lo que solo puede hacer el usuario ------------------
    if not ok_usuario:
        if estado != "en_validacion":
            texto = ruta.read_text(encoding="utf-8")
            texto = re.sub(r"^estado:\s*\S+", "estado: en_validacion", texto, count=1, flags=re.M)
            texto = re.sub(r"^actualizado:\s*\S+", f"actualizado: {HOY}", texto, count=1,
                           flags=re.M)
            ruta.write_text(texto, encoding="utf-8")
            ok(f"{rel(ruta)}: estado → en_validacion")
        else:
            ok(f"{nombre} ya estaba en_validacion: sigue esperando al usuario")
        print(f"\n  CIERRE A MEDIAS, Y ES LO CORRECTO. Todo lo que depende de un agente está\n"
              f"  hecho y comprobado; falta lo único que no puede hacer: que el usuario pruebe\n"
              f"  la aplicación CORRIENDO y diga que sí.\n\n"
              f"  · La unidad DEJA de contar para el tope de trabajo en vuelo: puedes despachar\n"
              f"    otra sin tocar el tope ni inventarte un ADR.\n"
              f"  · No está cerrada: no se archiva, no se borra el worktree ni la rama, y el\n"
              f"    linter la enseñará en cada arranque hasta que se termine.\n"
              f"  · Cuando el usuario dé el OK, con la fecha del día en que lo dio:\n"
              f"        python {rel(__file__)} cerrar {nombre} --ok-usuario {HOY}")
        return 0

    # --- Aviso (no bloquea): la cosecha de hallazgos ------------------------------------------
    pendientes = sin_cosechar(texto_hallazgos)
    if pendientes:
        warn(f"{pendientes} hallazgo(s) sin cosechar en {rel(hallazgos)}: marca cada viñeta "
             f"con '→ promovido a <destino>' o '→ descartado (motivo)' (formato en la propia "
             f"plantilla). No bloqueo el cierre, pero eso es conocimiento que se pierde")

    # --- Mecánica (lo que el padre tecleaba a mano, en orden) ---------------------------------
    print("\nMecánica:")
    escribir_ok_usuario(hallazgos, ok_usuario)
    ok(f"OK del usuario escrito en {rel(hallazgos)}")

    texto = ruta.read_text(encoding="utf-8")
    texto = re.sub(r"^estado:\s*\S+", "estado: mergeada", texto, count=1, flags=re.M)
    texto = re.sub(r"^actualizado:\s*\S+", f"actualizado: {HOY}", texto, count=1, flags=re.M)
    ruta.write_text(texto, encoding="utf-8")
    ok(f"{rel(ruta)}: estado → mergeada")

    if not documental and hay_repo:
        borrado, detalle = borrar_worktree(repo, destino)
        (ok if borrado else warn)(f"worktree worktrees/{nombre}: {detalle}")
        if git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{nombre}",
               silencioso=True)[0] == 0:
            codigo, salida = git(repo, "branch", "-d", nombre)
            (ok if codigo == 0 else warn)(
                f"rama local {nombre}: {'borrada' if codigo == 0 else salida}")
        # La rama REMOTA no se borra, a propósito. Es la única copia del trabajo que no vive
        # en este disco, y borrarla convierte cualquier accidente local en pérdida definitiva.
        # Cuesta nada dejarla y es la prueba que mira `rama_mergeada` cuando la local ya no
        # está. Si el repositorio tiene "delete branch on merge" activado en su servidor, esto
        # no lo impide: eso se decide allí, no aquí.
        if git(repo, "rev-parse", "--verify", "--quiet",
               f"refs/remotes/origin/{nombre}", silencioso=True)[0] == 0:
            ok(f"rama remota origin/{nombre}: se conserva (respaldo del trabajo entregado)")

    # Camino B (merge local, sin `gh`): si la principal se queda sin empujar, la SIGUIENTE
    # unidad nacerá de una `origin/<principal>` vieja y su merge ya no será fast-forward.
    # Se avisa aquí, que es cuando acaba de pasar, y con el comando exacto.
    if hay_repo and git(repo, "remote", "get-url", "origin", silencioso=True)[0] == 0:
        codigo, salida = git(repo, "rev-list", "--count",
                             f"origin/{principal}..{principal}", silencioso=True)
        if codigo == 0 and salida.strip().isdigit() and int(salida.strip()) > 0:
            warn(f"la rama principal local va {salida.strip()} commit(s) por delante de "
                 f"origin/{principal}: empújala o la siguiente unidad partirá de una base "
                 f"vieja → git -C {rel(repo)} push origin {principal}")

    if clase == "bug":
        # ADR-006: la ficha del bug NO se archiva; docs/bugs/ es el historial.
        ok(f"{rel(ruta)} se queda en docs/bugs/ (los bugs no se archivan, ADR-006)")
    else:
        ARCHIVO.mkdir(parents=True, exist_ok=True)
        final = ARCHIVO / nombre
        if final.exists():
            warn(f"{rel(final)} ya existe: no piso nada, muévelo tú")
        else:
            shutil.move(str(ruta.parent), str(final))
            ok(f"unidad archivada en {rel(final)}")

    print("\nLo que queda es tuyo, porque es criterio y no mecánica:")
    print("    · aplicar los Deltas al mapa (docs/02-flujos/) y pasar el flujo a 'entregada'")
    print("    · promover los hallazgos a conocimiento/, decisiones/ o al ROADMAP")
    print("    · actualizar ESTADO.md" + (" e INDICE.md de bugs" if clase == "bug" else ""))

    linter = RAIZ / "docs/00-metodo/scripts/lint_metodo.py"
    if linter.exists():
        print()
        sys.stdout.flush()
        return subprocess.run([sys.executable, str(linter)]).returncode
    return 0


# --------------------------------------------------------------------------- subcomando: estado

def cmd_estado(_args):
    unidades = censo()
    print("== Estado del trabajo ==\n")

    print("Unidades (docs/05-trabajo/):")
    filas = [(n, u) for n, u in sorted(unidades.items()) if u["clase"] == "unidad"]
    if not filas:
        print("  (ninguna)")
    for n, u in filas:
        fm = u["fm"]
        print(f"  {n:28} {fm.get('tipo', '?'):14} {fm.get('carril', '?'):9} "
              f"{fm.get('estado', 'SIN FRONTMATTER')}")

    print("\nBugs (docs/bugs/):")
    bugs = [(n, u) for n, u in sorted(unidades.items()) if u["clase"] == "bug"]
    abiertos = [(n, u) for n, u in bugs if u["fm"].get("estado") not in {"mergeada", "descartada"}]
    if not bugs:
        print("  (ninguno)")
    for n, u in bugs:
        estado = u["fm"].get("estado", "SIN FRONTMATTER")
        print(f"  {n:28} {estado}{'  ← abierto' if (n, u) in abiertos else ''}")

    print("\nWorktrees (worktrees/):")
    wt = sorted(p.name for p in WORKTREES.iterdir() if p.is_dir()) if WORKTREES.is_dir() else []
    if not wt:
        print("  (ninguno)")
    for w in wt:
        print(f"  {w}")

    print("\nCoherencia:")
    activas = sorted(n for n, u in unidades.items() if u["fm"].get("estado") in EN_VUELO)
    if not activas:
        ok("nada en vuelo (regla 5: 1 por defecto, tope 3)")
    elif len(activas) == 1:
        ok(f"1 unidad en vuelo: {activas[0]}")
    else:
        warn(f"{len(activas)} unidades en vuelo: {', '.join(activas)} "
             f"(default 1; en paralelo jamás comparten ficheros)")
    esperando = sorted(n for n, u in unidades.items()
                       if u["fm"].get("estado") == "en_validacion")
    if esperando:
        warn(f"{len(esperando)} unidad(es) esperando a que el usuario pruebe la app: "
             f"{', '.join(esperando)} — no cuentan para el tope, pero tampoco están cerradas")
    for huerfano in sorted(set(wt) - set(unidades)):
        fail(f"worktree sin unidad: worktrees/{huerfano} (¿cierre a medias?)")
    requieren_wt = [
        n for n in activas
        if unidades[n]["fm"].get("ejecucion") != "documental"
    ]
    for sin_wt in [n for n in requieren_wt if n not in wt]:
        warn(f"unidad {sin_wt} en obra SIN worktree (¿despachada de verdad?)")
    if wt and not (set(wt) - set(unidades)) and all(n in wt for n in requieren_wt):
        ok("worktrees y unidades casan")

    nnn, _ = siguiente_nnn()
    print(f"\nSiguiente NNN libre: {nnn}")
    print(f"Repo de código: {rel(repo_codigo()[0])}")
    return 0


# --------------------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(
        prog="unidad.py",
        description="Despacho de unidades del método: numeración, creación desde plantilla y "
                    "creación de rama/worktree con precondiciones que bloquean.")
    sub = ap.add_subparsers(dest="comando", metavar="{nnn,nueva,despachar,estado}")

    p_nnn = sub.add_parser("nnn", help="imprime el siguiente NNN libre")
    p_nnn.add_argument("--detalle", action="store_true",
                       help="además, lista qué número ocupa cada fuente")
    p_nnn.set_defaults(func=cmd_nnn)

    p_nueva = sub.add_parser("nueva", help="crea la unidad desde su plantilla (NO crea worktree)")
    p_nueva.add_argument("tipo", help=" | ".join(TIPOS))
    p_nueva.add_argument("slug", help="slug en minúsculas: ^[a-z0-9][a-z0-9-]*$")
    p_nueva.set_defaults(func=cmd_nueva)

    p_desp = sub.add_parser("despachar",
                            help="crea rama y worktree de una unidad ya especificada y aprobada")
    p_desp.add_argument("unidad", help="nombre completo NNN-slug")
    p_desp.add_argument("--paralelo", action="store_true",
                        help="permite despachar con otra unidad en vuelo (tope 3) — solo si NO "
                             "comparten ningún fichero")
    p_desp.add_argument(
        "--documental",
        action="store_true",
        help="despacha sin rama ni worktree; solo auditoria/investigacion/documentacion "
             "que leen main/ y escriben únicamente en su carpeta de unidad",
    )
    p_desp.add_argument("--force", action="store_true",
                        help="válvula de PRODUCCIÓN CAÍDA: salta la aprobación y la puerta de "
                             "la spec, y anota la deuda en la ficha. SOLO para unidades tipo "
                             "bug con severidad P0 declarada, y exige --motivo")
    p_desp.add_argument("--motivo", default="",
                        help="emergencia declarada por el usuario, en una frase; obligatorio "
                             'con --force (p. ej. --motivo "produccion caida: 500 en el login")')
    p_desp.set_defaults(func=cmd_despachar)

    p_cer = sub.add_parser("cerrar",
                           help="cierra una unidad revisada y ya fusionada: puertas + los "
                                "pasos mecánicos del ritual")
    p_cer.add_argument("unidad", help="nombre completo NNN-slug")
    p_cer.add_argument("--ok-usuario", default="", metavar="YYYY-MM-DD",
                       help="fecha en que el usuario probó la app corriendo y dio su OK. La "
                            "pone el usuario, igual que 'aprobado:' al despachar. Sin ella, si "
                            "todo lo demás está en verde, la unidad pasa a 'en_validacion': "
                            "deja de contar para el tope pero NO queda cerrada")
    p_cer.add_argument("--fusion", default="", metavar="SHA",
                       help="commit con el que el trabajo entró en la rama principal. Solo "
                            "hace falta si no queda rastro de la rama (ni local, ni remota, "
                            "ni anotada). No es un pase: el SHA tiene que existir y estar "
                            "dentro de la principal, o el cierre sigue bloqueado")
    p_cer.set_defaults(func=cmd_cerrar)

    p_est = sub.add_parser("estado", help="resumen: unidades, bugs, worktrees y su coherencia")
    p_est.set_defaults(func=cmd_estado)

    args = ap.parse_args()
    if not args.comando:
        ap.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
