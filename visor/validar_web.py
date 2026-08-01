#!/usr/bin/env python3
"""E2E obligatorio del menú lateral del visor.

Levanta el servidor real, abre Chrome mediante Playwright y comprueba que el
lateral existe, permanece a la izquierda y permite navegar por todas las
actividades o flujos. Sale con código 1 ante cualquier incumplimiento.

Uso:
    python visor/validar_web.py --datos /ruta/planos.json
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


def comprobar_lateral(page, datos, ancho):
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

    actividades = datos.get("actividades") or []
    flujos = datos.get("flujos") or []
    textos = page.locator("#menuIzq button").all_inner_texts()
    if actividades:
        areas = []
        for actividad in actividades:
            if actividad["area"] not in areas:
                areas.append(actividad["area"])
        ordenadas = [
            actividad
            for area in areas
            for actividad in actividades
            if actividad["area"] == area
        ]
        esperados = ["🗺 El mapa"] + [x["nombre"] for x in ordenadas]
        if textos != esperados:
            raise AssertionError(
                "actividades del lateral distintas: %r != %r"
                % (textos, esperados)
            )
        for actividad in actividades:
            print(
                "E2E %d px · actividad: %s" %
                (ancho, actividad["nombre"]),
                flush=True,
            )
            page.get_by_role(
                "button", name=actividad["nombre"], exact=True
            ).click()
            page.wait_for_function(
                """titulo => Array.from(
                  document.querySelectorAll('#menuIzq button')
                ).some(b => b.textContent.trim() === titulo &&
                            b.classList.contains('activo'))""",
                arg=actividad["nombre"],
            )
    elif flujos:
        esperados = [x["titulo"] for x in flujos]
        if textos != esperados:
            raise AssertionError(
                "flujos del lateral distintos: %r != %r"
                % (textos, esperados)
            )
        for flujo in flujos:
            print(
                "E2E %d px · flujo: %s" % (ancho, flujo["titulo"]),
                flush=True,
            )
            page.get_by_role(
                "button", name=flujo["titulo"], exact=True
            ).click()
            page.wait_for_function(
                """id => {
                  const flujo = document.querySelector('#flujo-' + id);
                  return flujo && flujo.offsetParent !== null &&
                    flujo.closest('section').classList.contains('activa');
                }""",
                arg=flujo["id"],
            )
    elif not page.locator("#menuIzq .menu-vacio").is_visible():
        raise AssertionError(
            "el lateral vacío no explica que todavía no hay flujos"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Valida con navegador real el lateral del visor"
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
                        comprobar_lateral(page, datos, ancho)
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
        sys.exit("ERROR: menú lateral inválido: %s" % exc)

    cantidad = len(datos.get("actividades") or datos.get("flujos") or [])
    print(
        "OK: menú lateral visible y navegable "
        "(%d entradas, anchos %s)." %
        (cantidad, ", ".join(str(x) for x in ANCHOS))
    )


if __name__ == "__main__":
    main()
