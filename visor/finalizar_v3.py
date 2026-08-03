#!/usr/bin/env python3
"""Congela un workspace aprobado y, opcionalmente, publica sus dos repos.

La operación se hace sobre el mismo ``<nombre>-agents`` creado por
``iniciar_v3.py``: valida los planos completos, prueba el visor real, conserva
``main/`` y deja ambos repos enlazados.

Schema v3: planificación empresarial (version 3).
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from . import revision
except ImportError:
    import revision

BASE = Path(__file__).resolve().parent


def morir(mensaje):
    raise SystemExit("finalizar_v3: %s" % mensaje)


def ejecutar(comando, cwd=None):
    return subprocess.run(
        comando,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def exigir_verde(comando, etiqueta, cwd=None):
    r = ejecutar(comando, cwd=cwd)
    if r.returncode:
        morir("%s falló:\n%s" % (etiqueta, r.stdout))
    print(r.stdout, end="")


def rutas_planos_v3(mapa):
    """Los planos v3 no tienen actividades anidadas, solo el plano raíz."""
    yield mapa


def congelar_planos(mapa):
    datos_mapa = json.loads(mapa.read_text(encoding="utf-8"))
    for ruta in rutas_planos_v3(mapa):
        if not ruta.is_file():
            morir("falta el plano %s" % ruta)
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        definicion = datos.get("definicion") or {}
        if definicion.get("estado") not in ("aprobado", "congelado"):
            morir(
                "%s no está aprobado por el usuario (definicion.estado=%r)"
                % (ruta, definicion.get("estado"))
            )
        definicion["estado"] = "congelado"
        datos["definicion"] = definicion
        ruta.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def copiar_documentacion_workspace(workspace, entrega):
    """Copia la documentación generada al workspace para registro."""
    if entrega.exists():
        for documento in entrega.rglob("*.md"):
            nombre = documento.name
            destino = workspace / "docs" / "01-entregables" / nombre
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(documento, destino)


def commit_si_hay_cambios(repo, mensaje, incluir_todo=False):
    if incluir_todo:
        ejecutar(["git", "add", "-A"], cwd=repo)
    estado = ejecutar(["git", "status", "--porcelain=v1"], cwd=repo)
    if estado.returncode:
        morir("%s no es un repositorio git:\n%s" % (repo, estado.stdout))
    if estado.stdout.strip():
        r = ejecutar(["git", "commit", "-m", mensaje], cwd=repo)
        if r.returncode:
            morir("no pude crear el commit en %s:\n%s" % (repo, r.stdout))


def repo_github(owner, nombre):
    if not shutil.which("gh"):
        morir("falta GitHub CLI (`gh`) para publicar repositorios")
    existe = ejecutar(["gh", "repo", "view", "%s/%s" % (owner, nombre), "--json", "name"])
    if existe.returncode:
        creado = ejecutar(
            ["gh", "repo", "create", "%s/%s" % (owner, nombre), "--private"]
        )
        if creado.returncode:
            morir("no pude crear %s/%s:\n%s" % (owner, nombre, creado.stdout))
    return "https://github.com/%s/%s.git" % (owner, nombre)


def configurar_remoto(repo, url):
    actual = ejecutar(["git", "remote", "get-url", "origin"], cwd=repo)
    if actual.returncode:
        r = ejecutar(["git", "remote", "add", "origin", url], cwd=repo)
    else:
        r = ejecutar(["git", "remote", "set-url", "origin", url], cwd=repo)
    if r.returncode:
        morir("no pude configurar origin en %s:\n%s" % (repo, r.stdout))


def publicar_github(workspace, owner, nombre):
    main = workspace / "main"
    nombre_meta = nombre + "-agents"
    url_codigo = repo_github(owner, nombre)
    url_meta = repo_github(owner, nombre_meta)

    commit_si_hay_cambios(main, "Importa el estado inicial del código", incluir_todo=True)
    configurar_remoto(main, url_codigo)
    subida = ejecutar(["git", "push", "-u", "origin", "HEAD:main"], cwd=main)
    if subida.returncode:
        morir("no pude publicar el repo de código:\n%s" % subida.stdout)

    repos = workspace / "repos.yaml"
    if repos.exists():
        texto = repos.read_text(encoding="utf-8")
        texto = texto.replace(
            "PENDIENTE  # crear el remoto del repo de código y poner aquí su URL",
            url_codigo,
        )
        repos.write_text(texto, encoding="utf-8")
        ejecutar(["git", "add", "repos.yaml"], cwd=workspace)
        commit_si_hay_cambios(workspace, "Configura los dos repositorios independientes")
    configurar_remoto(workspace, url_meta)
    subida = ejecutar(["git", "push", "-u", "origin", "main"], cwd=workspace)
    if subida.returncode:
        morir("no pude publicar el meta-repo:\n%s" % subida.stdout)
    print("GitHub: %s/%s y %s/%s" % (owner, nombre, owner, nombre_meta))


def main():
    ap = argparse.ArgumentParser(
        description="Valida, congela y finaliza un workspace de planificación empresarial."
    )
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--nombre", help="nombre final del repo; por defecto el del workspace")
    destino = ap.add_mutually_exclusive_group(required=True)
    destino.add_argument("--github", metavar="CUENTA",
                         help="crea/publica los dos repos privados en esa cuenta")
    destino.add_argument("--sin-github", action="store_true",
                         help="el usuario ha dicho que NO quiere GitHub: todo queda en este "
                              "ordenador, sin copia de seguridad, y se le advierte")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not (workspace / ".git").exists() or not (workspace / "main" / ".git").exists():
        morir("no es un workspace válido creado por iniciar_v3.py: %s" % workspace)
    mapa = workspace / "docs" / "01-entregables" / "planos" / "planos.json"
    if not mapa.is_file():
        morir("no encuentro los planos canónicos: %s" % mapa)

    # No basta con escribir "aprobado" en el JSON: el recibo firmado desde
    # la revisión web debe coincidir byte a byte con la versión actual.
    if not revision.aprobacion_vigente(mapa):
        morir(
            "no hay una aprobación vigente para estos planos; ábrelos con "
            "requisitos.py, resuelve el feedback y aprueba esa versión"
        )

    exigir_verde(
        [sys.executable, str(BASE / "validar.py"), "--datos", str(mapa),
         "--perfil", "congelado"],
        "validación de congelación",
    )
    exigir_verde(
        [sys.executable, str(BASE / "validar_web_v3.py"), "--datos", str(mapa)],
        "E2E del visor v3",
    )
    congelar_planos(mapa)
    exigir_verde(
        [sys.executable, str(BASE / "validar.py"), "--datos", str(mapa),
         "--perfil", "congelado"],
        "validación final",
    )

    with tempfile.TemporaryDirectory(prefix="ingenieria-requisitos-final-v3-") as temporal:
        salida = Path(temporal) / "entregables"
        # compilar.py es compatible con v3 (verificado en plan)
        exigir_verde(
            [sys.executable, str(BASE / "compilar.py"), "--mapa", str(mapa),
             "--salida", str(salida)],
            "compilación",
        )
        copiar_documentacion_workspace(workspace, salida)

    estado = workspace / "docs" / "05-trabajo" / "ESTADO.md"
    estado.write_text(
        "# ESTADO — planificación congelada\n\n"
        "- Los planos fueron aprobados y pasaron validación estructural y E2E.\n"
        "- Siguiente fase: ejecución de acciones, seguimiento de entregables y cumplimiento.\n",
        encoding="utf-8",
    )
    ejecutar(["git", "add", "docs"], cwd=workspace)
    commit_si_hay_cambios(workspace, "Congela planos aprobados y documentación")

    nombre = args.nombre or workspace.name.removesuffix("-agents")
    if args.github:
        publicar_github(workspace, args.github, nombre)
    print("Planificación finalizada en %s" % workspace)
    print("Carpeta de trabajo conservada en %s" % (workspace / "main"))
    if args.sin_github:
        print(
            "\n" + "=" * 70 + "\n"
            "AVISO: este proyecto existe SOLO en este ordenador.\n"
            "No hay copia en ningún otro sitio: si se rompe el disco, se pierde todo —\n"
            "los planos y el historial. Díselo al usuario con estas palabras.\n"
            "Cuando quiera publicarlo, se ejecuta esto mismo con --github <su-cuenta>.\n"
            + "=" * 70
        )


if __name__ == "__main__":
    main()
