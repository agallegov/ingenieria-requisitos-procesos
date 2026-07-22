#!/usr/bin/env python3
"""Visor local de idea-a-spec.

Sirve la plantilla fija (plantilla.html, junto a este script) y los datos del
proyecto (proceso.json) en 127.0.0.1, en un puerto libre, y se apaga solo
pasados N minutos (15 por defecto). Solo biblioteca estándar.

Uso:
    python3 servir.py --datos <ruta/proceso.json> [--minutos 15] [--sin-navegador]
"""

import argparse
import http.server
import json
import os
import sys
import threading
import time
import webbrowser

BASE = os.path.dirname(os.path.abspath(__file__))
PLANTILLA = os.path.join(BASE, "plantilla.html")


def hacer_handler(ruta_datos):
    class Visor(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._fichero(PLANTILLA, "text/html; charset=utf-8")
            elif self.path == "/datos.json":
                # Se relee en cada petición: editar el json + recargar basta.
                self._fichero(ruta_datos, "application/json; charset=utf-8")
            elif self.path in ("/spec.md", "/encargo.md"):
                # Documentos de salida, si ya existen junto a los datos.
                ruta = os.path.join(os.path.dirname(ruta_datos), self.path.lstrip("/"))
                if os.path.isfile(ruta):
                    self._fichero(ruta, "text/plain; charset=utf-8")
                else:
                    self.send_error(404, "Aún no se ha generado " + self.path.lstrip("/"))
            else:
                self.send_error(404, "Este visor solo sirve /, /datos.json, /spec.md y /encargo.md")

        def _fichero(self, ruta, tipo):
            try:
                with open(ruta, "rb") as f:
                    cuerpo = f.read()
            except OSError:
                self.send_error(500, "No se pudo leer " + os.path.basename(ruta))
                return
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, *args):
            pass

    return Visor


def main():
    p = argparse.ArgumentParser(description="Visor local de idea-a-spec")
    p.add_argument("--datos", required=True, help="Ruta al proceso.json del proyecto")
    p.add_argument("--minutos", type=float, default=15, help="Vida del servidor (defecto: 15)")
    p.add_argument("--sin-navegador", action="store_true", help="No abrir el navegador")
    args = p.parse_args()

    ruta_datos = os.path.abspath(args.datos)
    if not os.path.isfile(ruta_datos):
        sys.exit("No existe el fichero de datos: " + ruta_datos)
    if not os.path.isfile(PLANTILLA):
        sys.exit("Falta la plantilla fija: " + PLANTILLA)
    try:
        with open(ruta_datos, "r", encoding="utf-8") as f:
            json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("El fichero de datos no es JSON válido: " + str(e))

    # Puerto 0: el sistema asigna uno libre, sin carreras.
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), hacer_handler(ruta_datos))
    puerto = servidor.server_address[1]
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()

    url = "http://127.0.0.1:%d/" % puerto
    print("Visor levantado: %s" % url, flush=True)
    print("Datos: %s (se releen al recargar la página)" % ruta_datos, flush=True)
    print("Se apaga solo en %g minutos." % args.minutos, flush=True)
    if not args.sin_navegador:
        webbrowser.open(url)

    try:
        time.sleep(args.minutos * 60)
    except KeyboardInterrupt:
        pass
    servidor.shutdown()
    print("Visor cerrado. Para volver a verlo, lanza este comando otra vez.", flush=True)


if __name__ == "__main__":
    main()
