#!/usr/bin/env python3
"""actualizar.py — lleva el método de esta herramienta a los workspaces ya creados.

    python visor/actualizar.py buscar            encuentra workspaces y los registra
    python visor/actualizar.py revisar --todos    qué cambiaría (no toca nada)
    python visor/actualizar.py aplicar --todos    lo actualiza

POR QUÉ NO ES UN `git pull`: el workspace es OTRO repositorio, con su propio remoto. Su
copia del método salió de aquí por copia de ficheros al hacer el bootstrap; no hay
submódulo, ni subtree, ni remoto compartido. `git pull` allí trae el historial de ESE
proyecto y del método no se entera.

CÓMO SE DESHACE: con git, que para eso está. Antes de tocar un solo fichero se commitea el
estado actual del workspace (y se hace `git init` si aún no era un repositorio). Volver
atrás es `git checkout <ese commit>`, y el commit queda escrito en `HISTORIAL.md`.

Por eso el método se sobrescribe ENTERO, sin clasificar nada ni preguntar por cada fichero:
la copia de seguridad no es un algoritmo, es un commit. Si un proyecto había adaptado un
runbook a su gusto, esa versión no se pierde — está en el punto de retorno, a un checkout.

Solo stdlib. `revisar` no escribe nada. `aplicar` solo escribe el método y las piezas que
lo ejecutan: jamás los planos, el trabajo, los bugs, el conocimiento ni el código.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import bootstrap
import proyectos

for _salida in (sys.stdout, sys.stderr):
    if hasattr(_salida, "reconfigure"):
        _salida.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent
HERRAMIENTA = BASE.parent
PLANTILLA = HERRAMIENTA / "plantilla"
HOY = datetime.date.today().isoformat()

RE_TITULO = re.compile(r"^#\s*AGENTS\.md\s*—\s*(.+?)\s*\(meta-repo\)", re.M)
HISTORIAL = "docs/00-metodo/HISTORIAL.md"
CABECERA_HISTORIAL = (
    "# Historial de actualizaciones del método\n"
    "\n"
    "> Lo escribe `visor/actualizar.py` de la herramienta de ingeniería de requisitos.\n"
    "> El método se sobrescribe entero en cada actualización: lo que hubiera antes en este\n"
    "> workspace queda guardado en el commit que cada entrada anota. Para volver a ese\n"
    "> estado: `git checkout <ese commit>`.\n"
)


def git(repo, *args):
    try:
        p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", check=False)
    except OSError:
        return 1, ""
    return p.returncode, (p.stdout + p.stderr).strip()


def contenido_esperado(workspace):
    """{ruta en el workspace: contenido que debe tener}, y los avisos que salgan.

    Mismas fuentes que el bootstrap: si el bootstrap lo coloca, esto lo actualiza.
    """
    esperado, avisos = {}, []
    for relativo in bootstrap.ARCHIVOS_METODO:
        esperado[f"docs/00-metodo/{relativo}"] = (
            PLANTILLA / "docs" / "00-metodo" / relativo).read_text(encoding="utf-8")
    for nombre in bootstrap.ARCHIVOS_REQUISITOS:
        origen = (HERRAMIENTA / nombre
                  if nombre in ("RUNBOOK.md", "requirements-dev.txt") else BASE / nombre)
        esperado[f"docs/00-metodo/requisitos/{nombre}"] = origen.read_text(encoding="utf-8")
    for origen in sorted((PLANTILLA / "githooks").rglob("*")):
        if origen.is_file():
            rel = origen.relative_to(PLANTILLA / "githooks")
            esperado[f".githooks/{rel}"] = origen.read_text(encoding="utf-8")
    esperado["setup.py"] = (PLANTILLA / "setup.py").read_text(encoding="utf-8")
    # El .gitignore del meta-repo es infraestructura del método: es lo que mantiene main/ y
    # worktrees/ fuera de git. Sin él, el workspace intenta versionar el repo de código.
    esperado[".gitignore"] = (PLANTILLA / "gitignore").read_text(encoding="utf-8")
    esperado["worktrees/README.md"] = (
        PLANTILLA / "worktrees-README.md").read_text(encoding="utf-8")
    esperado[".github/workflows/lint.yml"] = bootstrap.generar_ci()
    for puente in ("CLAUDE.md", "GEMINI.md"):
        esperado[puente] = "@AGENTS.md\n"

    # AGENTS.md lleva dentro el título del proyecto: se compara contra la plantilla rellenada
    # con SU título. Si no se puede leer, se dice y se deja fuera — antes desaparecía del
    # informe en silencio, que es la peor de las tres opciones.
    actual = workspace / "AGENTS.md"
    if actual.is_file():
        m = RE_TITULO.search(actual.read_text(encoding="utf-8", errors="replace"))
        if m:
            esperado["AGENTS.md"] = (PLANTILLA / "AGENTS.md").read_text(
                encoding="utf-8").replace("{{TITULO}}", m.group(1))
        else:
            avisos.append("no pude leer el título en la primera línea de AGENTS.md "
                          "(se espera '# AGENTS.md — <título> (meta-repo)'): lo dejo sin "
                          "actualizar para no borrarte el nombre del proyecto")
    return esperado, avisos


def diferencias(workspace, esperado):
    """(ficheros que cambian, ficheros del método que la herramienta ya no publica)."""
    cambios = []
    for relativo, texto in sorted(esperado.items()):
        destino = workspace / relativo
        if not destino.is_file() or destino.read_text(encoding="utf-8",
                                                      errors="replace") != texto:
            cambios.append(relativo)
    sobrantes = []
    metodo = workspace / "docs" / "00-metodo"
    if metodo.is_dir():
        for ruta in sorted(metodo.rglob("*")):
            if not ruta.is_file() or "__pycache__" in ruta.parts:
                continue
            relativo = str(ruta.relative_to(workspace)).replace("\\", "/")
            if relativo not in esperado and relativo != HISTORIAL:
                sobrantes.append(relativo)
    return cambios, sobrantes


def informe(ruta, titulo, cambios, sobrantes, avisos):
    print(f"\n=== {titulo} ===\n    {ruta}")
    if cambios:
        print(f"    {len(cambios)} fichero(s) del método cambian:")
        for f in cambios:
            print(f"          {f}")
    else:
        print("    Al día: nada que actualizar.")
    if sobrantes:
        print(f"    {len(sobrantes)} fichero(s) que el método ya no publica (no se tocan):")
        for f in sobrantes:
            print(f"          {f}")
    for a in avisos:
        print(f"    AVISO: {a}")


def punto_de_retorno(workspace):
    """Commitea el estado actual. Devuelve (sha, "") o (None, motivo por el que no se puede).

    Es la ÚNICA red de esta actualización: si no se puede dejar el punto de retorno, no se
    toca nada. `git add -A` aquí es lo correcto y es su único sitio — lo que se busca es que
    no quede fuera del respaldo ni un fichero. El .gitignore ya excluye main/ y worktrees/.
    """
    if git(workspace, "rev-parse", "--is-inside-work-tree")[0] != 0:
        codigo, salida = git(workspace, "init", "-q")
        if codigo:
            return None, f"no pude crear el repositorio git aquí:\n{salida}"
        print("    (no era un repositorio git: lo he creado para poder deshacer)")
    git(workspace, "add", "-A")
    if git(workspace, "status", "--porcelain")[1].strip():
        codigo, salida = git(workspace, "commit", "-m",
                             "Punto de retorno antes de actualizar el método")
        if codigo:
            return None, ("no pude commitear el estado actual, así que no toco nada (sin "
                          f"punto de retorno no hay vuelta atrás):\n{salida}")
    codigo, sha = git(workspace, "rev-parse", "HEAD")
    if codigo:
        return None, f"el repositorio no tiene ni un commit:\n{sha}"
    return sha.strip(), ""


def escribir_historial(workspace, sha, cambios):
    ruta = workspace / HISTORIAL
    ruta.parent.mkdir(parents=True, exist_ok=True)
    previo = ruta.read_text(encoding="utf-8") if ruta.is_file() else CABECERA_HISTORIAL
    bloque = [f"## {HOY} · método {bootstrap.huella_plantilla()[:12]}…",
              "",
              f"Estado anterior: `{sha[:8]}` — ahí está lo que hubiera aquí antes "
              f"(`git checkout {sha[:8]}`).",
              f"{len(cambios)} fichero(s) sobrescritos:",
              ""]
    bloque += [f"- `{c}`" for c in cambios]
    ruta.write_text(previo.rstrip("\n") + "\n\n" + "\n".join(bloque) + "\n", encoding="utf-8")


def pasar_linter(workspace):
    linter = workspace / "docs/00-metodo/scripts/lint_metodo.py"
    if not linter.is_file():
        return
    r = subprocess.run([sys.executable, str(linter)], cwd=str(workspace), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    salida = (r.stdout + r.stderr).strip()
    if r.returncode:
        print("\n    -- el linter del método NO pasa en este workspace --")
        for linea in salida.splitlines():
            print(f"      {linea}")
    elif salida:
        print(f"    linter del método: {salida.splitlines()[-1].strip()}")


def aplicar(workspace, titulo):
    esperado, avisos = contenido_esperado(workspace)
    cambios, sobrantes = diferencias(workspace, esperado)
    informe(workspace, titulo, cambios, sobrantes, avisos)
    if not cambios:
        return 0

    sha, motivo = punto_de_retorno(workspace)
    if sha is None:
        print(f"\n    NO TOCO NADA: {motivo}")
        return 1

    for relativo in cambios:
        destino = workspace / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(esperado[relativo], encoding="utf-8")
        if destino.suffix == ".py" or destino.parent.name == ".githooks":
            destino.chmod(0o755)
    (workspace / "METODO.json").write_text(
        json.dumps({"formato": 1, "huella": bootstrap.huella_plantilla(), "actualizado": HOY},
                   ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    escribir_historial(workspace, sha, cambios)

    git(workspace, "add", "-A")
    codigo, salida = git(workspace, "commit", "-m",
                         f"Método actualizado desde la herramienta ({len(cambios)} ficheros)")
    print(f"\n    {len(cambios)} fichero(s) sobrescritos"
          f"{' y commiteados' if codigo == 0 else f' (el commit falló: {salida})'}.")
    print(f"    Para volver atrás:  git -C {workspace} checkout {sha[:8]}")
    print(f"    Queda anotado en:   {HISTORIAL}")
    pasar_linter(workspace)
    return 0


SALTAR = {"node_modules", "__pycache__", "Library", "Applications", ".git", ".venv",
          "venv", "worktrees", "main", "dist", "build", ".Trash", "System", "vendor"}
RAICES_HABITUALES = ("Project", "Projects", "Proyectos", "Developer", "dev", "code",
                     "Documents", "Desktop", "repos", "src", "work")


def es_workspace(ruta):
    """AGENTS.md + los planos dentro. Nunca dentro de la propia herramienta: la regla 2 de
    su AGENTS.md prohíbe guardar proyectos aquí, así que tampoco se registran."""
    ruta = ruta.resolve()
    if ruta == HERRAMIENTA or HERRAMIENTA in ruta.parents:
        return False
    return ((ruta / "AGENTS.md").is_file()
            and (ruta / "docs/02-flujos/planos/planos.json").is_file())


def buscar(raices, profundidad=3):
    """Rastrea el disco buscando workspaces de esta herramienta y devuelve sus rutas.

    Existe porque el registro local solo conoce lo que se creó en ESTA máquina con esta
    herramienta: un workspace clonado de GitHub, movido de sitio o creado en el portátil de
    al lado no está en él, y sin esto habría que registrarlo a mano uno por uno.
    """
    encontrados, vistos = [], set()

    def recorrer(ruta, resto):
        try:
            hijos = sorted(p for p in ruta.iterdir() if p.is_dir())
        except (OSError, PermissionError):
            return
        for hijo in hijos:
            if hijo.name.startswith(".") or hijo.name in SALTAR or hijo.is_symlink():
                continue
            real = hijo.resolve()
            if real in vistos:
                continue
            vistos.add(real)
            if es_workspace(hijo):
                encontrados.append(hijo.resolve())
                continue                       # dentro de un workspace no hay otro
            if resto:
                recorrer(hijo, resto - 1)

    for raiz in raices:
        raiz = Path(raiz).expanduser()
        if raiz.is_dir():
            if es_workspace(raiz):
                encontrados.append(raiz.resolve())
            else:
                recorrer(raiz, profundidad)
    return sorted(set(encontrados))


def raices_por_defecto():
    """Dónde mirar si el usuario no dice: su carpeta de usuario, las carpetas de trabajo
    típicas, y el vecindario de los proyectos que ya conocemos."""
    casa = Path.home()
    raices = [casa] + [casa / nombre for nombre in RAICES_HABITUALES]
    for p in proyectos.cargar()["proyectos"]:
        padre = Path(p["ruta"]).parent
        if padre.is_dir():
            raices.append(padre)
    return raices


def cmd_buscar(args):
    raices = args.en or raices_por_defecto()
    print("Buscando workspaces (carpetas con AGENTS.md y planos dentro) en:")
    for r in raices[:8]:
        print(f"    {r}")
    if len(raices) > 8:
        print(f"    … y {len(raices) - 8} sitio(s) más")
    hallados = buscar(raices, profundidad=args.profundidad)
    conocidos = {p["ruta"] for p in proyectos.cargar()["proyectos"]}
    nuevos = [h for h in hallados if str(h) not in conocidos]
    print(f"\n{len(hallados)} workspace(s) encontrados · {len(nuevos)} sin registrar.")
    for h in hallados:
        print(f"    [{'NUEVO' if h in nuevos else 'ya registrado'}] {h}")
    for h in nuevos:
        proyectos.registrar(h)
    if nuevos:
        print(f"\nRegistrados {len(nuevos)}. Ahora: python visor/actualizar.py revisar --todos")
    elif not hallados:
        print("\nNinguno. Si están en otro sitio: "
              "python visor/actualizar.py buscar --en /ruta/donde/estan")
    return 0


def objetivos(args):
    datos = proyectos.cargar()["proyectos"]
    if args.todos:
        return datos
    ruta = str(Path(args.ruta).expanduser().resolve())
    encontrados = [p for p in datos if p.get("ruta") == ruta]
    return encontrados or [{"ruta": ruta, "titulo": Path(ruta).name}]


def main():
    ap = argparse.ArgumentParser(
        description="Lleva el método de esta herramienta a los workspaces ya creados.")
    sub = ap.add_subparsers(dest="orden", required=True)
    p_buscar = sub.add_parser("buscar",
                              help="rastrea el disco, encuentra workspaces y los registra")
    p_buscar.add_argument("--en", nargs="*", metavar="RUTA",
                          help="dónde mirar (por defecto: tu carpeta de usuario y las de "
                               "trabajo habituales)")
    p_buscar.add_argument("--profundidad", type=int, default=3,
                          help="cuántas carpetas hacia dentro (defecto: 3)")
    p_buscar.set_defaults(func=cmd_buscar)
    for nombre, ayuda in (("revisar", "informe; no toca nada"),
                          ("aplicar", "sobrescribe el método, con punto de retorno en git")):
        p = sub.add_parser(nombre, help=ayuda)
        grupo = p.add_mutually_exclusive_group(required=True)
        grupo.add_argument("ruta", nargs="?", help="carpeta del workspace <proyecto>-agents")
        grupo.add_argument("--todos", action="store_true", help="todos los registrados")
    args = ap.parse_args()
    if args.orden == "buscar":
        return args.func(args)

    lista = objetivos(args)
    if not lista:
        print("No hay proyectos registrados. Regístralos con "
              "`python visor/proyectos.py registrar RUTA`.")
        return 0
    print(f"Método de esta herramienta: huella {bootstrap.huella_plantilla()[:12]}…")
    salida, pendientes = 0, 0
    for entrada in lista:
        ruta = Path(entrada["ruta"])
        titulo = entrada.get("titulo", ruta.name)
        if not ruta.is_dir():
            print(f"\n=== {titulo} ===\n    {ruta}\n    NO ENCONTRADO (¿movido o borrado?)")
            continue
        try:
            if args.orden == "revisar":
                esperado, avisos = contenido_esperado(ruta)
                cambios, sobrantes = diferencias(ruta, esperado)
                informe(ruta, titulo, cambios, sobrantes, avisos)
                pendientes += 1 if cambios else 0
            else:
                salida |= aplicar(ruta, titulo)
        except OSError as e:
            # Un proyecto roto no puede llevarse por delante la revisión de los demás.
            print(f"\n=== {titulo} ===\n    {ruta}\n    NO PUDE LEERLO: {e}")
            salida = 1
    if args.orden == "revisar":
        print(f"\n{pendientes} proyecto(s) con cambios pendientes de {len(lista)} revisado(s).")
        if pendientes:
            print("Para aplicarlos: python visor/actualizar.py aplicar --todos "
                  "(o con la ruta de uno). Antes de tocar nada commitea el estado actual, "
                  "así que se deshace con un checkout.")
    return salida


if __name__ == "__main__":
    sys.exit(main())
