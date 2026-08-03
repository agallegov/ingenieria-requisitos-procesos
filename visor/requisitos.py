#!/usr/bin/env python3
"""Punto de entrada humano para revisar requisitos dentro de un workspace.

Uso desde la raíz de ``<nombre>-agents``:

    python docs/00-metodo/requisitos/requisitos.py abrir
    python docs/00-metodo/requisitos/requisitos.py estado
    python docs/00-metodo/requisitos/requisitos.py aprobar --por "Nombre"
    python docs/00-metodo/requisitos/requisitos.py solicitar-cambios --texto "..."
    python docs/00-metodo/requisitos/requisitos.py resolver FB-1
"""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

try:
    from . import revision
except ImportError:
    import revision

BASE = Path(__file__).resolve().parent


def mapa_workspace(workspace):
    workspace = Path(workspace).expanduser().resolve()
    # Soporte dual: v2 (software) y v3 (planificación empresarial)
    ruta_v2 = workspace / "docs" / "02-flujos" / "planos" / "planos.json"
    ruta_v3 = workspace / "docs" / "01-entregables" / "planos" / "planos.json"
    if ruta_v2.is_file():
        return workspace, ruta_v2
    if ruta_v3.is_file():
        return workspace, ruta_v3
    raise ValueError(
        "no encuentro planos canónicos en %s ni %s"
        % (ruta_v2, ruta_v3)
    )


def puerto_determinista(workspace):
    huella = hashlib.sha256(
        str(Path(workspace).expanduser().resolve()).encode("utf-8")
    ).hexdigest()
    return 8766 + (int(huella[:8], 16) % 1000)


def puerto_ocupado(puerto):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexion:
        conexion.settimeout(0.2)
        return conexion.connect_ex(("127.0.0.1", puerto)) == 0


def meta_puerto(puerto):
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:%d/meta.json" % puerto, timeout=0.5
        ) as respuesta:
            return json.loads(respuesta.read())
    except (OSError, ValueError, urllib.error.URLError):
        return None


def elegir_puerto(workspace, mapa, pedido=None):
    if pedido is not None:
        if pedido == 0:
            return 0, False
        meta = meta_puerto(pedido)
        if meta and Path(meta.get("datos", "")).resolve() == mapa.resolve():
            return pedido, True
        if puerto_ocupado(pedido):
            raise ValueError("el puerto %d ya lo usa otro servicio" % pedido)
        return pedido, False

    candidatos = [8765, puerto_determinista(workspace)]
    candidatos += [
        puerto_determinista(workspace) + desplazamiento
        for desplazamiento in range(1, 50)
    ]
    for puerto in candidatos:
        meta = meta_puerto(puerto)
        if meta and Path(meta.get("datos", "")).resolve() == mapa.resolve():
            return puerto, True
        if not puerto_ocupado(puerto):
            return puerto, False
    raise ValueError("no encontré un puerto local libre para el visor")


def cmd_estado(mapa):
    estado = revision.estado_revision(mapa)
    if estado["listo"]:
        print("LISTO PARA REVISAR")
        if estado["aprobacion_vigente"]:
            print("La aprobación vigente coincide con estos planos.")
        return 0
    print("NO LISTO PARA REVISAR")
    if estado["feedback_pendiente"]:
        print(
            "%d comentario(s) pendiente(s)." % estado["feedback_pendiente"]
        )
    for bloqueo in estado["bloqueos"]:
        print("- %s" % bloqueo)
    return 1


def cmd_abrir(workspace, mapa, args):
    puerto, reutilizado = elegir_puerto(
        workspace, mapa, getattr(args, "puerto", None)
    )
    if reutilizado:
        url = "http://127.0.0.1:%d/" % puerto
        print("Visor ya activo: %s" % url)
        if not args.sin_navegador:
            webbrowser.open(url)
        return 0
    comando = [
        sys.executable,
        str(BASE / "servir.py"),
        "--datos",
        str(mapa),
        "--puerto",
        str(puerto),
        "--minutos",
        str(args.minutos),
    ]
    if args.sin_navegador:
        comando.append("--sin-navegador")
    return subprocess.call(comando, cwd=workspace)


def main():
    ap = argparse.ArgumentParser(description="Abre y gestiona la revisión de planos")
    sub = ap.add_subparsers(dest="comando", required=True)

    abrir = sub.add_parser("abrir", help="abre o reutiliza el visor estable")
    abrir.add_argument("--workspace", default=".")
    abrir.add_argument("--puerto", type=int)
    abrir.add_argument("--minutos", type=float, default=0)
    abrir.add_argument("--sin-navegador", action="store_true")

    estado = sub.add_parser("estado", help="muestra si se puede pedir aprobación")
    estado.add_argument("--workspace", default=".")

    resolver = sub.add_parser("resolver", help="marca un feedback como resuelto")
    resolver.add_argument("id")
    resolver.add_argument("--workspace", default=".")

    aprobar = sub.add_parser(
        "aprobar", help="registra por CLI la aprobación de esta versión"
    )
    aprobar.add_argument("--por", required=True)
    aprobar.add_argument("--confirmar-supuestos", action="store_true")
    aprobar.add_argument("--workspace", default=".")

    cambios = sub.add_parser(
        "solicitar-cambios", help="reabre los planos y registra el motivo"
    )
    cambios.add_argument("--texto", required=True)
    cambios.add_argument("--workspace", default=".")

    args = ap.parse_args()
    try:
        workspace, mapa = mapa_workspace(args.workspace)
        if args.comando == "estado":
            return cmd_estado(mapa)
        if args.comando == "resolver":
            revision.resolver_feedback(mapa, args.id)
            print("%s resuelto." % args.id)
            return 0
        if args.comando == "aprobar":
            recibo = revision.aprobar(
                mapa, args.por, args.confirmar_supuestos
            )
            print(
                "Versión %d aprobada por %s."
                % (recibo["version"], recibo["por"])
            )
            return 0
        if args.comando == "solicitar-cambios":
            comentario = revision.solicitar_cambios(
                mapa, args.texto, {"canal": "agente-cli"}
            )
            print("Cambios solicitados (%s)." % comentario["id"])
            return 0
        return cmd_abrir(workspace, mapa, args)
    except (OSError, ValueError) as exc:
        print("ERROR: %s" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
