#!/usr/bin/env python3
"""E2E obligatorio del menú lateral del visor para v3 (planificación empresarial).

Levanta el servidor real, abre Chrome mediante Playwright y comprueba que el
lateral existe, permanece a la izquierda y permite navegar por todas las
secciones v3: acciones, entregables, cumplimiento, distribución, etc.
Sale con código 1 ante cualquier incumplimiento.

Schema v3: planificación empresarial (version 3).

Uso:
    python visor/validar_web_v3.py --datos /ruta/planos.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
REQUISITOS = next(
    (ruta for ruta in (BASE / "requirements-dev.txt", BASE.parent / "requirements-dev.txt")
     if ruta.is_file()),
    BASE / "requirements-dev.txt",
)

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit(
        "ERROR: falta Playwright. Instala las dependencias E2E con "
        f"`python -m pip install -r \"{REQUISITOS}\"` "
        "y después `python -m playwright install chromium`."
    )


SERVIR = BASE / "servir.py"
ANCHOS = (1280, 700)


def encontrar_chrome():
    candidatas = [
        os.environ.get("CHROME_BIN"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        str(
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
            / "Google/Chrome/Application/chrome.exe"
        ),
        str(
            Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
            / "Google/Chrome/Application/chrome.exe"
        ),
        str(
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Google/Chrome/Application/chrome.exe"
        ),
    ]
    for candidata in candidatas:
        if candidata and Path(candidata).is_file():
            return candidata
    return None


def arrancar_visor(datos):
    proceso = subprocess.Popen(
        [
            sys.executable,
            str(SERVIR),
            "--datos",
            str(datos),
            "--minutos",
            "2",
            "--puerto",
            "0",
            "--sin-navegador",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for _ in range(20):
        linea = proceso.stdout.readline()
        encontrada = re.search(r"Visor levantado: (http://\S+/)", linea)
        if encontrada:
            return proceso, encontrada.group(1)
        if proceso.poll() is not None:
            break
    salida = proceso.stdout.read()
    proceso.terminate()
    raise RuntimeError("el visor no arrancó: " + salida)


def comprobar_lateral_v3(page, datos, ancho):
    """Comprueba que el lateral v3 muestra las secciones empresariales correctas."""
    page.goto(page.url.split("#")[0] + "#resumen")
    page.wait_for_function(
        """() => document.querySelector('#titulo').textContent !==
                 'Cargando…'"""
    )
    menu = page.locator("#menuIzq")
    panel = page.locator(".panel")
    if not menu.is_visible():
        raise AssertionError("el menú lateral está oculto a %d px" % ancho)
    caja_menu = menu.bounding_box()
    caja_panel = panel.bounding_box()
    if caja_menu["x"] + caja_menu["width"] > caja_panel["x"] + 1:
        raise AssertionError(
            "el menú no está a la izquierda del contenido a %d px" % ancho
        )

    # En v3, el lateral muestra las secciones principales del schema empresarial.
    secciones_esperadas = ["🗺 El mapa"]
    datos_acciones = datos.get("acciones") or []
    datos_entregables = datos.get("entregables") or []
    datos_cumplimiento = datos.get("cumplimiento") or []
    datos_distribucion = datos.get("distribucion") or {}
    datos_presupuesto = datos.get("presupuesto") or {}
    datos_estructura = datos.get("estructura_organizativa") or []
    datos_flujos = datos.get("flujos") or []
    datos_actores = datos.get("actores") or []
    datos_metricas = datos.get("metricas") or []
    datos_calidad = datos.get("calidad") or []
    datos_normas = datos.get("normas") or []
    datos_proveedores = datos.get("proveedores") or []
    datos_glosario = datos.get("glosario") or []

    if datos_estructura:
        secciones_esperadas.append("Estructura organizativa")
    if datos_flujos:
        secciones_esperadas.append("Flujos")
    if datos_acciones:
        secciones_esperadas.append("Acciones")
    if datos_entregables:
        secciones_esperadas.append("Entregables")
    if datos_cumplimiento:
        secciones_esperadas.append("Cumplimiento")
    if datos_presupuesto.get("items"):
        secciones_esperadas.append("Presupuesto")
    if datos_proveedores:
        secciones_esperadas.append("Proveedores")
    if datos_distribucion.get("entregas") or datos_distribucion.get("permisos"):
        secciones_esperadas.append("Distribución")
    if datos_calidad:
        secciones_esperadas.append("Calidad")
    if datos_glosario:
        secciones_esperadas.append("Glosario")

    textos = page.locator("#menuIzq button").all_inner_texts()
    if textos != secciones_esperadas:
        raise AssertionError(
            "secciones del lateral v3 distintas: %r != %r"
            % (textos, secciones_esperadas)
        )

    # Navegar por cada sección verificando que el botón funciona.
    for seccion in secciones_esperadas:
        print(
            "E2E %d px · sección v3: %s" % (ancho, seccion),
            flush=True,
        )
        try:
            page.get_by_role("button", name=seccion, exact=True).click()
            page.wait_for_timeout(300)
        except Exception:
            raise AssertionError("no pude navegar a la sección: %s" % seccion)


def main():
    parser = argparse.ArgumentParser(
        description="Valida con navegador real el lateral del visor (v3 empresarial)"
    )
    parser.add_argument("--datos", required=True)
    args = parser.parse_args()
    ruta = Path(args.datos).resolve()
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        chrome = encontrar_chrome()
        proceso, url = arrancar_visor(ruta)
        try:
            with sync_playwright() as playwright:
                opciones = {"headless": True}
                if chrome:
                    opciones["executable_path"] = chrome
                browser = playwright.chromium.launch(**opciones)
                try:
                    for ancho in ANCHOS:
                        page = browser.new_page(
                            viewport={"width": ancho, "height": 900}
                        )
                        page.set_default_timeout(8000)
                        page.goto(url + "#resumen")
                        comprobar_lateral_v3(page, datos, ancho)
                        page.close()
                finally:
                    browser.close()
        finally:
            if proceso.poll() is None:
                proceso.terminate()
                proceso.wait(timeout=5)
    except (
        OSError,
        ValueError,
        RuntimeError,
        AssertionError,
        PlaywrightError,
    ) as exc:
        sys.exit("ERROR: menú lateral v3 inválido: %s" % exc)

    cantidad = len(
        datos.get("acciones")
        or datos.get("entregables")
        or datos.get("cumplimiento")
        or datos.get("flujos")
        or []
    )
    print(
        "OK: menú lateral v3 visible y navegable "
        "(%d entradas, anchos %s)." %
        (cantidad, ", ".join(str(x) for x in ANCHOS))
    )


if __name__ == "__main__":
    main()
