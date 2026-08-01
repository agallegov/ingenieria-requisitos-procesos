#!/usr/bin/env python3
"""Memoria local de workspaces creados por la lanzadera. Solo stdlib."""

import argparse
import json
import os
import tempfile
from pathlib import Path

import bootstrap

RAIZ = Path(__file__).resolve().parent.parent
REGISTRO = RAIZ / ".ingenieria-requisitos-local" / "registro.json"
FORMATO = 1


def cargar():
    if not REGISTRO.is_file():
        return {"formato": FORMATO, "proyectos": []}
    try:
        datos = json.loads(REGISTRO.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit("No puedo leer el registro local: %s" % exc)
    if datos.get("formato") != FORMATO:
        raise SystemExit("El registro es de otra versión de la lanzadera.")
    return datos


def guardar(datos):
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    fd, temporal = tempfile.mkstemp(dir=REGISTRO.parent, prefix="registro-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(temporal, REGISTRO)
    finally:
        if os.path.exists(temporal):
            os.unlink(temporal)


def leer_marca(workspace):
    ruta = workspace / "METODO.json"
    try:
        return json.loads(ruta.read_text(encoding="utf-8")).get("huella", "desconocida")
    except (OSError, ValueError):
        return "anterior-a-las-huellas"


def registrar(workspace):
    workspace = workspace.expanduser().resolve()
    planos = workspace / "docs/02-flujos/planos/planos.json"
    if not (workspace / "AGENTS.md").is_file() or not planos.is_file():
        raise SystemExit("No parece un workspace generado: %s" % workspace)
    try:
        titulo = json.loads(planos.read_text(encoding="utf-8")).get("titulo", workspace.name)
    except (OSError, ValueError):
        titulo = workspace.name
    datos = cargar()
    entrada = {"ruta": str(workspace), "titulo": titulo, "huella": leer_marca(workspace)}
    datos["proyectos"] = [p for p in datos["proyectos"] if p.get("ruta") != str(workspace)]
    datos["proyectos"].append(entrada)
    datos["proyectos"].sort(key=lambda p: p["ruta"])
    guardar(datos)
    print("Registrado: %s" % workspace)


def main():
    ap = argparse.ArgumentParser(description="Recuerda los workspaces de este ordenador.")
    sub = ap.add_subparsers(dest="orden", required=True)
    sub.add_parser("listar")
    reg = sub.add_parser("registrar")
    reg.add_argument("ruta")
    reg.add_argument("--generado", action="store_true", help=argparse.SUPPRESS)
    contexto = sub.add_parser("contexto", help="datos para el playbook de actualización")
    grupo = contexto.add_mutually_exclusive_group(required=True)
    grupo.add_argument("ruta", nargs="?")
    grupo.add_argument("--todos", action="store_true")
    args = ap.parse_args()

    if args.orden == "registrar":
        registrar(Path(args.ruta))
        return
    datos = cargar()
    proyectos = datos["proyectos"]
    if args.orden == "listar":
        if not proyectos:
            print("No hay proyectos registrados.")
        for p in proyectos:
            estado = "OK" if Path(p["ruta"]).is_dir() else "NO ENCONTRADO"
            print("[%s] %s — %s" % (estado, p["titulo"], p["ruta"]))
        return
    if not args.todos:
        objetivo = str(Path(args.ruta).expanduser().resolve())
        proyectos = [p for p in proyectos if p.get("ruta") == objetivo]
        if not proyectos:
            raise SystemExit("Proyecto no registrado: %s" % objetivo)
    print(json.dumps({
        "huella_actual": bootstrap.huella_plantilla(),
        "proyectos": proyectos,
    }, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
