#!/usr/bin/env python3
"""Gate de pre-despliegue: nada se despliega sin plan de backups, script de deploy,
repo de código limpio, auditoría de seguridad archivada y observabilidad declarada.

Uso: python docs/00-metodo/scripts/lint_deploy.py   (desde la raíz del workspace)
Salida: OK/WARN/FAIL por comprobación. Exit 0 si no hay FAIL; exit 1 si hay alguno.
Se ejecuta: como paso 1 del runbook de deploy (docs/00-metodo/runbooks/deploy.md).

A diferencia del linter del método, aquí SÍ se es estricto: desplegar es el acto
peligroso, y un FAIL BLOQUEA el deploy. Sin verde no hay deploy, jamás.
Sin dependencias: solo stdlib. El disco es la verdad; este script solo la comprueba.
"""
import re
import subprocess
import sys
import time
from fnmatch import fnmatchcase
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
fallos, avisos = [], []


def ok(msg):
    print(f"  OK   {msg}")


def warn(msg):
    avisos.append(msg)
    print(f"  WARN {msg}")


def fail(msg):
    fallos.append(msg)
    print(f"  FAIL {msg}")


# Las 5 secciones obligatorias de DESPLIEGUE.md (plantilla: 00-metodo/plantillas/despliegue.md)
SECCIONES = ["Backups", "Deploy", "Auditoría de seguridad", "Observabilidad",
             "Registro de errores"]
MINIMO_PROSA = 120  # caracteres de prosa real por sección (sin cabeceras ni huecos <...>)

# Artefactos de agentes que JAMÁS viven en el repo de código (regla dura: los agentes
# no le escriben sus cosas dentro — todo el pensamiento vive en el meta-repo).
ARTEFACTOS_DIR = {".claude", ".cursor", "planning"}
ARTEFACTOS_FICHERO = ["CLAUDE.md", "AGENTS.md", ".cursorrules", "PLAN.md", "plan.md",
                      "TODO.md", "especificacion*.md", "tareas*.md", "hallazgos*.md"]
NO_ESCANEAR = {".git", ".github", "tests"}  # infra legítima del repo: no se marca

DIAS_AUDITORIA = 60  # antigüedad máxima de la auditoría de seguridad sin avisar


def prosa_real(lineas):
    """Caracteres de prosa de una sección: fuera cabeceras y huecos de plantilla <...>."""
    texto = "\n".join(l for l in lineas if not l.lstrip().startswith("#"))
    texto = re.sub(r"<[^>]*>", "", texto)          # huecos de plantilla, también multilínea
    return len(re.sub(r"\s+", " ", texto).strip())


def secciones_de(path):
    """Divide el markdown en secciones por cabecera '## Título' -> {titulo: [lineas]}."""
    actual, resultado = None, {}
    for linea in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", linea)
        if m:
            actual = m.group(1)
            resultado.setdefault(actual, [])
        elif actual is not None:
            resultado[actual].append(linea)
    return resultado


print("== Gate de pre-despliegue ==")

# --- f) Precondición: esto se corre en el workspace completo ---
main_dir = RAIZ / "main"
if not main_dir.is_dir():
    fail("main/ no existe: este gate se corre en el workspace completo (meta-repo con "
         "main/ dentro), no en el repo de código suelto")

# --- a) DESPLIEGUE.md: existe y sus 5 secciones tienen prosa real ---
despliegue = RAIZ / "docs/04-planificacion/DESPLIEGUE.md"
if not despliegue.is_file():
    fail("docs/04-planificacion/DESPLIEGUE.md no existe (copiar "
         "docs/00-metodo/plantillas/despliegue.md y rellenarlo)")
else:
    encontradas = secciones_de(despliegue)
    flojas = []
    for s in SECCIONES:
        if s not in encontradas:
            flojas.append(f"'## {s}' AUSENTE")
        elif (n := prosa_real(encontradas[s])) < MINIMO_PROSA:
            flojas.append(f"'## {s}' floja ({n} caracteres de prosa < {MINIMO_PROSA}: "
                          "huecos <...> de plantilla no cuentan)")
    if flojas:
        fail(f"DESPLIEGUE.md incompleto: {'; '.join(flojas)}")
    else:
        ok(f"DESPLIEGUE.md con sus {len(SECCIONES)} secciones obligatorias rellenas")

if main_dir.is_dir():
    # --- b) Script de deploy REAL en el repo de código ---
    deploy_hallado = None
    for c in (main_dir / "deploy.py", main_dir / "scripts" / "deploy.py"):
        if c.exists():
            deploy_hallado = f"main/{c.relative_to(main_dir)}{'/' if c.is_dir() else ''}"
            break
    if deploy_hallado:
        ok(f"script de deploy: {deploy_hallado}")
    else:
        fail("sin script de deploy en el repo de código (se espera main/deploy.py "
             "o main/scripts/deploy.py) "
             "— desplegar a mano está prohibido")

    # --- c) Script/config de backup REAL ---
    backups = []
    if (main_dir / "backup.py").is_file():
        backups.append("main/backup.py")
    backups += sorted(f"main/scripts/{p.name}" for p in (main_dir / "scripts").glob("backup*.py")) \
        if (main_dir / "scripts").is_dir() else []
    composes = sorted(list(main_dir.glob("docker-compose*.y*ml")) +
                      list(main_dir.glob("compose*.y*ml")))
    backups += [f"main/{c.name} (pg_dump)" for c in composes
                if "pg_dump" in c.read_text(encoding="utf-8")]
    if backups:
        ok(f"backup encontrado: {', '.join(backups)}")
    else:
        fail("sin backup real en el repo de código (se espera main/backup.py, "
             "main/scripts/backup*.py, o un servicio/cron con pg_dump en algún "
             "docker-compose*.yml / compose*.yml) — autoalojar sin backup es innegociable")

    # --- d) Repo de código LIMPIO de artefactos de agentes ---
    def es_artefacto(entrada):
        if entrada.is_dir():
            return entrada.name in ARTEFACTOS_DIR
        return any(fnmatchcase(entrada.name, pat) for pat in ARTEFACTOS_FICHERO)

    sucios = []
    for entrada in sorted(main_dir.iterdir()):        # raíz…
        if entrada.name in NO_ESCANEAR:
            continue
        if es_artefacto(entrada):
            sucios.append(f"main/{entrada.name}{'/' if entrada.is_dir() else ''}")
        elif entrada.is_dir():                        # …y un nivel
            sucios += [f"main/{entrada.name}/{e.name}{'/' if e.is_dir() else ''}"
                       for e in sorted(entrada.iterdir()) if es_artefacto(e)]
    if sucios:
        fail(f"repo de código SUCIO de artefactos de agentes (viven en el meta-repo, "
             f"jamás en main/): {sucios}")
    else:
        ok("repo de código limpio de artefactos de agentes")

# --- e) Auditoría de seguridad hecha y archivada ---
archivo = RAIZ / "docs/05-trabajo/archivo"
unidades_auditoria = [p for p in sorted(archivo.iterdir())
                      if p.is_dir() and "auditoria" in p.name and "seguridad" in p.name] \
    if archivo.is_dir() else []
con_informe = [u for u in unidades_auditoria if any(u.rglob("*.md"))]
if not con_informe:
    fail("sin auditoría de seguridad archivada (docs/05-trabajo/archivo/*auditoria*"
         "seguridad*/ con informe): correr el playbook "
         "docs/00-metodo/auditoria-seguridad.md como unidad tipo auditoria antes de desplegar")
else:
    ultima = con_informe[-1]
    r = subprocess.run(["git", "log", "-1", "--format=%ct", "--",
                        str(ultima.relative_to(RAIZ))],
                       cwd=RAIZ, capture_output=True, text=True)
    ts = int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None
    if ts is None:
        ok(f"auditoría de seguridad archivada: {ultima.name} (antigüedad no verificable: "
           "sin commit aún)")
    elif (dias := int((time.time() - ts) / 86400)) > DIAS_AUDITORIA:
        warn(f"auditoría de seguridad {ultima.name} tiene {dias} días (> {DIAS_AUDITORIA}): "
             "el código ha seguido cambiando — considerar re-auditar antes de desplegar")
    else:
        ok(f"auditoría de seguridad archivada: {ultima.name} ({dias} días)")

# --- Resultado ---
print(f"\n{len(fallos)} FAIL · {len(avisos)} WARN")
print("GATE ABIERTO: se puede seguir con el runbook de deploy." if not fallos else
      "GATE CERRADO: NO se despliega hasta dejar esto en verde (sin verde no hay deploy).")
sys.exit(1 if fallos else 0)
