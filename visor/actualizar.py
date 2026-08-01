#!/usr/bin/env python3
"""actualizar.py — lleva el método de esta herramienta a los workspaces ya creados.

    python visor/actualizar.py revisar --todos          informe de todos (no toca nada)
    python visor/actualizar.py revisar RUTA             informe de uno
    python visor/actualizar.py aplicar RUTA             aplica lo seguro y deja lo demás
    python visor/actualizar.py aplicar --todos          lo mismo, proyecto por proyecto

POR QUÉ NO ES UN `git pull`: el workspace es OTRO repositorio, con su propio remoto. Su
copia del método salió de aquí por copia de ficheros al hacer el bootstrap; no hay
submódulo, ni subtree, ni remoto compartido. `git pull` allí trae el historial de ESE
proyecto y del método no se entera.

POR QUÉ NO SE SOBRESCRIBE A CIEGAS: un workspace vivo puede haber adaptado su método a
propósito. Por eso cada fichero se clasifica antes de tocarlo:

    al día     idéntico al de la herramienta            → nada que hacer
    nuevo      la herramienta lo tiene y el workspace no → se añade (seguro)
    pendiente  distinto, y NADIE lo tocó allí            → se reemplaza (seguro)
    tocado     distinto Y modificado en el workspace     → NO se toca: lo juzga el agente
    sobrante   está allí y ya no en la herramienta       → se avisa, jamás se borra solo

DATOS PARA LA PRÓXIMA: al aplicar, `METODO.json` pasa a formato 2 y guarda la huella de
CADA fichero instalado. A partir de ahí, "¿lo tocaron aquí?" se responde comparando
huellas, sin arqueología de git. Los workspaces antiguos (formato 1) se resuelven mirando
el historial: un fichero con un solo commit —el del bootstrap— está intacto.

Solo stdlib. `revisar` no escribe nada. `aplicar` exige árbol limpio y nunca sale de las
rutas permitidas por `ACTUALIZAR-PROYECTOS.md`.
"""
import argparse
import datetime
import hashlib
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
PLANTILLA = BASE.parent / "plantilla"
HOY = datetime.date.today().isoformat()
FORMATO_MARCA = 2

RE_TITULO = re.compile(r"^#\s*AGENTS\.md\s*—\s*(.+?)\s*\(meta-repo\)", re.M)


def sha(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def git(repo, *args):
    try:
        p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", check=False)
    except OSError:
        return 1, ""
    return p.returncode, (p.stdout + p.stderr).strip()


def contenido_esperado(workspace):
    """{ruta relativa en el workspace: contenido que debería tener}. Mismas fuentes que el
    bootstrap: si el bootstrap lo coloca, esto lo actualiza; si no, ni se mira."""
    esperado = {}
    for relativo in bootstrap.ARCHIVOS_METODO:
        origen = PLANTILLA / "docs" / "00-metodo" / relativo
        esperado[f"docs/00-metodo/{relativo}"] = origen.read_text(encoding="utf-8")
    for nombre in bootstrap.ARCHIVOS_REQUISITOS:
        origen = (BASE.parent / nombre
                  if nombre in ("RUNBOOK.md", "requirements-dev.txt") else BASE / nombre)
        esperado[f"docs/00-metodo/requisitos/{nombre}"] = origen.read_text(encoding="utf-8")
    for origen in sorted((PLANTILLA / "githooks").rglob("*")):
        if origen.is_file():
            rel = origen.relative_to(PLANTILLA / "githooks")
            esperado[f".githooks/{rel}"] = origen.read_text(encoding="utf-8")
    esperado["setup.py"] = (PLANTILLA / "setup.py").read_text(encoding="utf-8")
    esperado[".github/workflows/lint.yml"] = bootstrap.generar_ci()
    for puente in ("CLAUDE.md", "GEMINI.md"):
        esperado[puente] = "@AGENTS.md\n"

    # AGENTS.md lleva el título del proyecto sustituido: se compara contra la plantilla
    # rellenada con SU título, o no se compara (y entonces lo juzga el agente).
    plantilla_agents = (PLANTILLA / "AGENTS.md").read_text(encoding="utf-8")
    actual = workspace / "AGENTS.md"
    if actual.is_file():
        m = RE_TITULO.search(actual.read_text(encoding="utf-8"))
        if m:
            esperado["AGENTS.md"] = plantilla_agents.replace("{{TITULO}}", m.group(1))
    return esperado


def origen_de(relativo):
    """Ruta en ESTA herramienta del fichero que corresponde, para poder compararlos.

    Devuelve None para los que se generan (la CI del meta) y no viven en un fichero.
    """
    if relativo.startswith("docs/00-metodo/requisitos/"):
        nombre = relativo.split("/")[-1]
        return (BASE.parent / nombre
                if nombre in ("RUNBOOK.md", "requirements-dev.txt") else BASE / nombre)
    if relativo.startswith("docs/00-metodo/"):
        return PLANTILLA / "docs" / "00-metodo" / relativo[len("docs/00-metodo/"):]
    if relativo.startswith(".githooks/"):
        return PLANTILLA / "githooks" / relativo[len(".githooks/"):]
    if relativo in ("setup.py", "AGENTS.md"):
        return PLANTILLA / relativo
    return None


def marca(workspace):
    try:
        return json.loads((workspace / "METODO.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def intacto(workspace, relativo, texto_actual, registradas):
    """¿El workspace NO ha tocado este fichero desde que se instaló?

    Formato 2: comparación de huellas, exacta y barata. Formato 1 o sin registro: se mira el
    historial de git —un fichero con un solo commit es el que dejó el bootstrap—. Sin git no
    hay forma de saberlo, y entonces se asume tocado: equivocarse hacia no pisar nada.
    """
    if relativo in registradas:
        return sha(texto_actual) == registradas[relativo]
    codigo, salida = git(workspace, "log", "--format=%H", "--", relativo)
    if codigo != 0:
        return False
    commits = [l for l in salida.splitlines() if l.strip()]
    return len(commits) == 1


def revisar(workspace):
    """Clasifica cada fichero del método. No escribe nada."""
    esperado = contenido_esperado(workspace)
    registradas = marca(workspace).get("ficheros", {})
    grupos = {"al dia": [], "nuevo": [], "pendiente": [], "tocado": []}
    for relativo, texto in sorted(esperado.items()):
        destino = workspace / relativo
        if not destino.is_file():
            grupos["nuevo"].append(relativo)
            continue
        actual = destino.read_text(encoding="utf-8")
        if actual == texto:
            grupos["al dia"].append(relativo)
        elif intacto(workspace, relativo, actual, registradas):
            grupos["pendiente"].append(relativo)
        else:
            grupos["tocado"].append(relativo)

    # Lo que sobra: ficheros del método que la herramienta ya no publica.
    sobrantes = []
    metodo = workspace / "docs" / "00-metodo"
    if metodo.is_dir():
        for ruta in sorted(metodo.rglob("*")):
            if not ruta.is_file() or "__pycache__" in ruta.parts:
                continue
            relativo = str(ruta.relative_to(workspace)).replace("\\", "/")
            if relativo not in esperado:
                sobrantes.append(relativo)
    grupos["sobrante"] = sobrantes
    return grupos, esperado


def al_dia(grupos):
    return not (grupos["nuevo"] or grupos["pendiente"] or grupos["tocado"])


def informe(ruta, titulo, grupos):
    print(f"\n=== {titulo} ===\n    {ruta}")
    if al_dia(grupos):
        print("    Al día: nada que actualizar.")
    else:
        for clave, etiqueta in (("pendiente", "se actualizan solos"),
                                ("nuevo", "se añaden"),
                                ("tocado", "MODIFICADOS AQUÍ: los juzga el agente"),
                                ("sobrante", "ya no forman parte del método (no se borran)")):
            if grupos[clave]:
                print(f"    {len(grupos[clave]):3} {clave:10} ({etiqueta})")
                for f in grupos[clave]:
                    print(f"          {f}")
    print(f"    {len(grupos['al dia'])} ficheros ya al día.")


def puertas(workspace):
    """Lo que exige ACTUALIZAR-PROYECTOS.md antes de editar. Devuelve lista de problemas."""
    problemas = []
    if not (workspace / "AGENTS.md").is_file():
        problemas.append(f"{workspace} no parece un workspace generado (falta AGENTS.md)")
        return problemas
    codigo, salida = git(workspace, "status", "--porcelain")
    if codigo != 0:
        problemas.append("el meta-repo no es un repositorio git: no puedo dejar rastro "
                         "reversible de lo que cambie")
    elif salida:
        problemas.append(f"el meta-repo tiene {len(salida.splitlines())} cambio(s) sin "
                         f"commitear: commitea o descarta antes, para que el diff de la "
                         f"actualización se lea limpio")
    worktrees = workspace / "worktrees"
    vivos = [p.name for p in worktrees.iterdir()
             if p.is_dir() and p.name != "README.md"] if worktrees.is_dir() else []
    if vivos:
        problemas.append(f"hay trabajo en vuelo ({', '.join(vivos)}): cierra la unidad antes "
                         f"de cambiarle el método por debajo")
    return problemas


def aplicar(workspace, titulo):
    grupos, esperado = revisar(workspace)
    informe(workspace, titulo, grupos)
    if al_dia(grupos):
        return 0
    problemas = puertas(workspace)
    if problemas:
        print("\n    NO APLICO:")
        for p in problemas:
            print(f"      · {p}")
        return 1

    escritos = []
    for relativo in grupos["pendiente"] + grupos["nuevo"]:
        destino = workspace / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(esperado[relativo], encoding="utf-8")
        if destino.suffix == ".py" or destino.parent.name == ".githooks":
            destino.chmod(0o755)
        escritos.append(relativo)
    print(f"\n    Escritos {len(escritos)} fichero(s).")

    # Los datos para la PRÓXIMA actualización. Se guarda la huella de lo que ESTA herramienta
    # considera canónico, no la del fichero que hay en el disco. La diferencia importa justo
    # en los 'tocado': si guardáramos su contenido real, la próxima vez parecerían intactos y
    # se pisaría la personalización de ese proyecto sin que nadie se enterase. Guardando lo
    # canónico, un fichero adaptado sigue constando como suyo mientras difiera — y vuelve al
    # redil solo si algún día adopta la versión de la herramienta.
    huellas = {relativo: sha(texto) for relativo, texto in esperado.items()
               if (workspace / relativo).is_file()}
    (workspace / "METODO.json").write_text(
        json.dumps({"formato": FORMATO_MARCA,
                    "huella": bootstrap.huella_plantilla(),
                    "actualizado": HOY,
                    "ficheros": huellas},
                   ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("    METODO.json actualizado (formato 2: huella por fichero para la próxima vez).")

    linter = workspace / "docs/00-metodo/scripts/lint_metodo.py"
    if linter.is_file():
        print("\n    -- linter del método en el workspace --")
        r = subprocess.run([sys.executable, str(linter)], cwd=str(workspace),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        for linea in r.stdout.splitlines():
            if linea.strip().startswith(("FAIL", "WARN")) or "FAIL ·" in linea:
                print(f"      {linea.strip()}")
        if r.returncode:
            print("      El workspace NO pasa el linter: míralo antes de commitear.")

    if grupos["tocado"]:
        print(f"\n    QUEDAN {len(grupos['tocado'])} fichero(s) modificados en este workspace.")
        print("    No los he pisado. Para cada uno, el agente compara y decide:")
        for f in grupos["tocado"]:
            origen = origen_de(f)
            if origen:
                print(f"      diff -u '{origen}' '{workspace / f}'")
            else:
                print(f"      (generado por la herramienta) {f}")
        print("    Criterio (ACTUALIZAR-PROYECTOS.md): personalización deliberada se conserva")
        print("    y se le adapta la mejora; regla vieja se retira; duda, se pregunta.")
    print(f"\n    Revisa el diff y commitea tú: git -C {workspace} diff")
    return 0


SALTAR = {"node_modules", "__pycache__", "Library", "Applications", ".git", ".venv",
          "venv", "worktrees", "main", "dist", "build", ".Trash", "System", "vendor"}
RAICES_HABITUALES = ("Project", "Projects", "Proyectos", "Developer", "dev", "code",
                     "Documents", "Desktop", "repos", "src", "work")


def es_workspace(ruta):
    """La misma prueba que usa el registro: AGENTS.md + los planos dentro."""
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
        print(f"    [{'NUEVO' if str(h) in {str(n) for n in nuevos} else 'ya registrado'}] {h}")
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
                          ("aplicar", "aplica lo seguro y deja lo modificado al agente")):
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
    salida = 0
    pendientes = 0
    for entrada in lista:
        ruta = Path(entrada["ruta"])
        titulo = entrada.get("titulo", ruta.name)
        if not ruta.is_dir():
            print(f"\n=== {titulo} ===\n    {ruta}\n    NO ENCONTRADO (¿movido o borrado?)")
            continue
        if args.orden == "revisar":
            grupos, _ = revisar(ruta)
            informe(ruta, titulo, grupos)
            pendientes += 0 if al_dia(grupos) else 1
        else:
            salida |= aplicar(ruta, titulo)
    if args.orden == "revisar":
        print(f"\n{pendientes} proyecto(s) con cambios pendientes de {len(lista)} revisado(s).")
        if pendientes:
            print("Para aplicarlos: python visor/actualizar.py aplicar --todos "
                  "(o con la ruta de uno).")
    return salida


if __name__ == "__main__":
    sys.exit(main())
