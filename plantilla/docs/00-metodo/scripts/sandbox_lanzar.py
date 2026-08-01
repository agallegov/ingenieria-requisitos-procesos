#!/usr/bin/env python3
"""Envuelve el lanzamiento de un constructor en un sandbox de SO, por worktree.

Uso:
  python docs/00-metodo/scripts/sandbox_lanzar.py --worktree <ruta> --cmd "<comando>"
  ... [--red <dominio> ...] [--git-compartido] [--solo-lectura] [--ejecutar] [--permitir-sin-sandbox]

Qué hace: dado el worktree de una unidad y el comando que lanza al constructor,
construye el comando EQUIVALENTE ya confinado por el sistema operativo, con la política
correcta para un flujo de git worktrees:
  - escritura permitida SOLO al worktree, a su gitdir de respaldo (main/.git/worktrees/<name>,
    resuelto leyendo el fichero `.git` del worktree) y a /tmp — si no, `git commit` falla;

Perfil --solo-lectura (AUDITOR): solicita un entorno sin rutas escribibles. Hay que comprobar
en cada máquina que el mecanismo elegido aplica de verdad esa política antes de confiar en él.
  - escritura DENEGADA a los sinks de ejecución del `.git` compartido (`hooks/`, `config`) y
    a los candados del harness commiteados en el worktree (`.claude/settings*.json`), para que
    el constructor no pueda auto-des-confinarse (vector del CVE-2026-55607);
  - lectura denegada a credenciales (`~/.ssh`, `~/.aws`);
  - red denegada por defecto (allowlist explícita con --red; solo srt la aplica de verdad).

Detecta el mecanismo disponible en este orden: `srt` (sandbox-runtime de Anthropic, la pieza
agente-agnóstica recomendada) → `sandbox-exec` (Seatbelt, macOS) → `bwrap` (bubblewrap, Linux).
Si NO hay ninguno: AVISA de que lanzaría SIN confinamiento físico y SE NIEGA (exit != 0), salvo
que se pase --permitir-sin-sandbox. Filosofía: mejor negarse a lanzar que fingir un candado.

Por defecto imprime el comando (dry-run); con --ejecutar lo lanza de verdad.

Las variantes dependen de programas externos y pueden cambiar. Antes de usarlas hay que
verificar empíricamente que escribir fuera falla y que la operación Git permitida funciona.
Consulta `docs/00-metodo/sandbox.md`; este programa no declara validado el ordenador actual.

Sin dependencias: solo stdlib. Este script solo CONSTRUYE el comando; no toca git ni ficheros
del repo (salvo escribir el fichero de settings/perfil temporal del sandbox).
"""
import argparse
import json
import os
import platform
import re
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

# Marcador que deja claro que un valor no se pudo resolver y hay que rellenarlo a mano.
PLACEHOLDER = "<RESOLVER-A-MANO>"


def avisar(msg):
    print(f"sandbox_lanzar: AVISO: {msg}", file=sys.stderr)


def morir(msg, codigo=2):
    print(f"sandbox_lanzar: {msg}", file=sys.stderr)
    sys.exit(codigo)


def resolver_gitdir(worktree: Path):
    """Gitdir de respaldo de un worktree enlazado, leyendo su fichero `.git`.

    En un worktree enlazado, `<worktree>/.git` es un FICHERO con `gitdir: <ruta absoluta>`
    (p.ej. main/.git/worktrees/<name>). Devuelve esa ruta, o None si no se puede resolver
    (worktree aún no creado, o es el checkout principal donde `.git` es un directorio).
    """
    dotgit = worktree / ".git"
    if dotgit.is_file():
        try:
            m = re.search(r"gitdir:\s*(.+)", dotgit.read_text(encoding="utf-8"))
        except OSError:
            return None
        if m:
            # .resolve() para dar la ruta REAL: macOS matchea la política contra el path
            # con los symlinks ya resueltos (mismo motivo que /tmp → /private/tmp).
            return Path(m.group(1).strip()).resolve()
    return None


def resolver_commondir(gitdir):
    """El `.git` compartido (common dir) desde el gitdir de respaldo.

    El gitdir de respaldo tiene un fichero `commondir` (ruta, normalmente relativa: `../..`).
    Devuelve el common dir absoluto, o None si no se puede resolver.
    """
    if gitdir is None:
        return None
    commondir_file = gitdir / "commondir"
    if commondir_file.is_file():
        try:
            rel = commondir_file.read_text(encoding="utf-8").strip()
        except OSError:
            rel = ""
        if rel:
            return (gitdir / rel).resolve()
    # Heurística de respaldo: main/.git/worktrees/<name> → main/.git
    if gitdir.parent.name == "worktrees":
        return gitdir.parent.parent
    return None


def construir_politica(worktree: Path, gitdir, commondir, git_compartido, dominios, home,
                       solo_lectura=False):
    """La política de confinamiento común a todos los mecanismos.

    Devuelve (allow_write, deny_write, deny_read, allow_domains). Las rutas son strings
    absolutos; donde algo no se pudo resolver, aparece el PLACEHOLDER.

    Con `solo_lectura` (perfil de AUDITOR): NINGUNA ruta escribible — ni el worktree, ni el
    gitdir de respaldo, ni /tmp. Todo el filesystem queda en solo lectura (un auditor lee y no
    escribe: sus hallazgos paren unidades, no tocan disco). Se deniega la raíz entera para que
    el read-only no dependa del default del mecanismo, y se mantiene la denegación de lectura
    de credenciales (~/.ssh, ~/.aws). El opt-in --git-compartido se ignora aquí (no hay commit).
    """
    if solo_lectura:
        return [], ["/"], [str(home / ".ssh"), str(home / ".aws")], list(dominios)

    gitdir_s = str(gitdir) if gitdir else f"{PLACEHOLDER} (gitdir de respaldo: main/.git/worktrees/<name>)"
    common_s = str(commondir) if commondir else PLACEHOLDER

    # macOS resuelve symlinks al aplicar la política: `/tmp` (→ `/private/tmp`) NO matchea si
    # lo pasas literal. Hay que dar la ruta REAL. Igual con $TMPDIR. El worktree ya viene
    # resuelto (Path.resolve en main).
    allow_write = [str(worktree), gitdir_s, os.path.realpath("/tmp")]
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        allow_write.append(os.path.realpath(tmpdir.rstrip("/")))
    # Los refs/logs de un worktree pueden vivir en el .git COMPARTIDO (common dir). Si un
    # `git commit` falla por refs, hay que ensanchar la escritura al common dir (menos
    # hooks/config). Opt-in porque expone refs de otros worktrees: usar solo si hace falta.
    if git_compartido and commondir:
        allow_write.append(common_s)

    deny_write = [
        # Sinks de ejecución del .git compartido: el vector del CVE-2026-55607. Permitimos
        # el resto del .git para poder commitear, pero NUNCA hooks/config.
        f"{common_s}/hooks",
        f"{common_s}/config",
        # Candados del harness commiteados en el worktree: que el constructor no reescriba
        # su propia política de sandbox/permisos (auto-des-confinamiento).
        str(worktree / ".claude" / "settings.json"),
        str(worktree / ".claude" / "settings.local.json"),
    ]
    deny_read = [str(home / ".ssh"), str(home / ".aws")]
    return allow_write, deny_write, deny_read, list(dominios)


# --------------------------------------------------------------------------------------
# Construcción por mecanismo. Cada función devuelve (argv_a_ejecutar, texto_explicativo).
# --------------------------------------------------------------------------------------

def construir_srt(cmd, allow_write, deny_write, deny_read, dominios, name):
    """srt (sandbox-runtime de Anthropic): la vía agente-agnóstica recomendada.

    La configuración se imprime antes de ejecutar. Confirma la CLI y el esquema contra la
    versión instalada y ejecuta la prueba negativa descrita en sandbox.md.
    """
    settings = {
        "filesystem": {
            "allowWrite": allow_write,
            "denyWrite": deny_write,
            "denyRead": deny_read,
        },
        "network": {
            # Deny-all por defecto en srt. Sin dominios, el agente no llega ni al modelo:
            # el orquestador DEBE pasar --red con el endpoint del modelo y el git remoto.
            "allowedDomains": dominios,
        },
    }
    ruta = Path(tempfile.gettempdir()) / f"srt-{name}.json"
    ruta.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # `--` separa los flags de srt del comando del constructor.
    argv = ["srt", "--settings", str(ruta), "--", "/bin/sh", "-c", cmd]
    texto = (
        f"  mecanismo : srt (sandbox-runtime, Seatbelt en macOS / bubblewrap en Linux)\n"
        f"  settings  : {ruta}\n"
        f"{textwrap_indent(json.dumps(settings, indent=2, ensure_ascii=False), '    ')}\n"
        f"  VERIFICA  : CLI, esquema y prueba negativa en esta máquina antes de confiar."
    )
    return argv, texto


def construir_seatbelt(cmd, allow_write, deny_write, deny_read, name):
    """sandbox-exec / Seatbelt (macOS). PLANTILLA: SBPL está deprecado y sin doc oficial.

    Semántica SBPL: gana la ÚLTIMA regla que aplica, así que los `deny` van DESPUÉS de los
    `allow` que quieren recortar. No filtra red por dominio (para eso está el proxy de srt):
    aquí la red queda abierta y se marca como carencia.
    """
    def subpaths(rutas):
        # Se omiten los PLACEHOLDER: una ruta sin resolver no debe entrar cruda en el perfil.
        vals = [r for r in rutas if PLACEHOLDER not in r]
        return " ".join(f'(subpath "{r}")' for r in vals) if vals else ""

    aw, dw, dr = subpaths(allow_write), subpaths(deny_write), subpaths(deny_read)
    perfil = f"""(version 1)
(deny default)
(allow process*)
(allow sysctl-read)
(allow file-read*)
{f"(deny file-read* {dr})" if dr else ";; (sin denegación de lectura resuelta)"}
{f"(allow file-write* {aw})" if aw else ";; (sin escritura permitida resuelta)"}
{f"(deny file-write* {dw})" if dw else ";; (sin denegación de escritura resuelta)"}
;; TODO red: SBPL no hace allowlist por DOMINIO. Aquí la red queda abierta (riesgo de
;; exfiltración). Para control de red por dominio, usar srt (añade un proxy).
(allow network*)
"""
    ruta = Path(tempfile.gettempdir()) / f"seatbelt-{name}.sb"
    ruta.write_text(perfil, encoding="utf-8")
    argv = ["sandbox-exec", "-f", str(ruta), "/bin/sh", "-c", cmd]
    texto = (
        f"  mecanismo : sandbox-exec / Seatbelt (macOS) — PLANTILLA (SBPL deprecado, sin doc oficial)\n"
        f"  perfil    : {ruta}\n"
        f"{textwrap_indent(perfil.rstrip(), '    ')}\n"
        f"  TODO      : SBPL no está documentado por Apple y `sandbox-exec` está DEPRECATED. "
        f"Verificar el perfil empíricamente (escribir fuera → debe fallar; git commit → debe ir). "
        f"La red NO se filtra por dominio: preferir srt."
    )
    return argv, texto


def construir_bwrap(cmd, worktree, gitdir, commondir, name, solo_lectura=False):
    """bubblewrap (Linux). PLANTILLA: la protección depende enteramente de los argumentos.

    Modo normal: monta todo read-only y re-monta escribibles SOLO worktree + gitdir de respaldo
    + /tmp; hooks/config del common dir se dejan read-only. Modo solo-lectura (auditor): monta
    TODO read-only y NO re-bindea nada escribible — ni worktree, ni gitdir, ni /tmp (sin tmpfs).
    /dev y /proc se montan igual porque no son el filesystem (devtmpfs/procfs, no ficheros
    reales). bwrap por sí solo NO filtra red por dominio (para eso, el proxy de srt): aquí se
    comparte la red del host y se marca.
    """
    if solo_lectura:
        binds = ["--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc"]
        argv = ["bwrap", *binds, "--unshare-all", "--share-net", "--", "/bin/sh", "-c", cmd]
        texto = (
            "  mecanismo : bwrap / bubblewrap (Linux) — PLANTILLA · perfil SOLO LECTURA (auditor)\n"
            "  TODO      : todo el filesystem montado read-only (--ro-bind / /), sin ninguna ruta "
            "escribible (ni worktree, ni gitdir, ni /tmp). La red del host se comparte (--share-net) "
            "SIN filtro por dominio: para control de red, preferir srt. Verificar empíricamente "
            "(intentar escribir CUALQUIER fichero → debe fallar)."
        )
        return argv, texto
    binds = ["--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
             "--bind", str(worktree), str(worktree)]
    if gitdir:
        binds += ["--bind", str(gitdir), str(gitdir)]
    if commondir:
        binds += ["--ro-bind", str(commondir / "hooks"), str(commondir / "hooks"),
                  "--ro-bind", str(commondir / "config"), str(commondir / "config")]
    argv = ["bwrap", *binds, "--unshare-all", "--share-net", "--", "/bin/sh", "-c", cmd]
    faltan = []
    if not gitdir:
        faltan.append("gitdir de respaldo (main/.git/worktrees/<name>) sin resolver → git commit fallará")
    if not commondir:
        faltan.append("common dir sin resolver → no se protegen hooks/config")
    texto = (
        f"  mecanismo : bwrap / bubblewrap (Linux) — PLANTILLA\n"
        f"  TODO      : bubblewrap no es un sandbox llave-en-mano; la protección depende de "
        f"estos binds. La red del host se comparte (--share-net) SIN filtro por dominio: para "
        f"control de red, preferir srt (bwrap + proxy). Verificar empíricamente."
        + ("".join(f"\n  OJO       : {f}" for f in faltan))
    )
    return argv, texto


def textwrap_indent(texto, prefijo):
    return "\n".join(prefijo + l for l in texto.splitlines())


def detectar():
    """Mecanismo de sandbox disponible: srt > sandbox-exec (mac) > bwrap (linux), o None."""
    if shutil.which("srt"):
        return "srt"
    so = platform.system()
    if so == "Darwin" and shutil.which("sandbox-exec"):
        return "seatbelt"
    if so == "Linux" and shutil.which("bwrap"):
        return "bwrap"
    return None


def main():
    ap = argparse.ArgumentParser(
        description="Construye el comando de lanzamiento SANDBOXEADO de un constructor por worktree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--worktree", required=True, help="ruta del worktree del constructor")
    ap.add_argument("--cmd", required=True, help="comando que lanza al constructor (entre comillas)")
    ap.add_argument("--red", action="append", default=[], metavar="DOMINIO",
                    help="dominio permitido para la red (repetible; solo srt lo aplica). "
                         "Sin ninguno: red denegada.")
    ap.add_argument("--git-compartido", action="store_true",
                    help="ensancha la escritura al .git compartido (menos hooks/config); "
                         "usar solo si git commit falla por refs del common dir")
    ap.add_argument("--solo-lectura", action="store_true",
                    help="perfil de AUDITOR: NINGUNA ruta escribible (todo el filesystem "
                         "read-only; ni worktree, ni gitdir, ni /tmp). --worktree se usa solo "
                         "para nombrar el perfil (pásale la raíz del workspace o main/).")
    ap.add_argument("--ejecutar", action="store_true",
                    help="ejecuta el comando envuelto (por defecto solo lo imprime)")
    ap.add_argument("--permitir-sin-sandbox", action="store_true",
                    help="permite lanzar SIN confinamiento si no hay ninguna herramienta "
                         "de sandbox (por defecto: se NIEGA)")
    a = ap.parse_args()

    worktree = Path(a.worktree).resolve()
    if not worktree.exists():
        avisar(f"el worktree {worktree} no existe todavía: las rutas se construyen igual, "
               "pero el gitdir de respaldo no se podrá resolver.")
    name = worktree.name
    home = Path(os.path.expanduser("~"))

    gitdir = resolver_gitdir(worktree)
    commondir = resolver_commondir(gitdir)
    # En solo-lectura no hay commit: el gitdir de respaldo es irrelevante (no se avisa).
    if gitdir is None and not a.solo_lectura:
        avisar(f"no pude resolver el gitdir de respaldo de {worktree} (no es un worktree "
               "enlazado o aún no existe). El comando queda como PLANTILLA: sin ese gitdir "
               "escribible, `git commit` fallará. Resuélvelo antes de usarlo de verdad.")

    allow_write, deny_write, deny_read, dominios = construir_politica(
        worktree, gitdir, commondir, a.git_compartido, a.red, home, solo_lectura=a.solo_lectura)

    if not dominios:
        avisar("red DENEGADA (sin --red): con srt el constructor no alcanzará ni el endpoint "
               "del modelo. Pasa --red con el modelo y el git remoto para uso real.")

    mecanismo = detectar()

    if mecanismo is None:
        avisar("NO hay ninguna herramienta de sandbox disponible (ni srt, ni sandbox-exec, "
               "ni bwrap). NO hay forma de imponer un límite FÍSICO de escritura.")
        if a.permitir_sin_sandbox:
            avisar("--permitir-sin-sandbox: se lanzaría SIN confinamiento. El comando de abajo "
                   "NO está sandboxeado; el constructor puede escribir en TODO el disco.")
            print(a.cmd)
            sys.exit(0)
        morir("me niego a lanzar sin confinamiento físico. Instala srt "
              "(`npm i -g @anthropic-ai/sandbox-runtime`) o usa --permitir-sin-sandbox "
              "bajo tu responsabilidad.", codigo=3)

    if mecanismo == "srt":
        argv, texto = construir_srt(a.cmd, allow_write, deny_write, deny_read, dominios, name)
    elif mecanismo == "seatbelt":
        argv, texto = construir_seatbelt(a.cmd, allow_write, deny_write, deny_read, name)
    else:
        argv, texto = construir_bwrap(a.cmd, worktree, gitdir, commondir, name,
                                      solo_lectura=a.solo_lectura)

    rotulo = "auditor SOLO LECTURA" if a.solo_lectura else "constructor"
    print(f"== Lanzamiento sandboxeado del {rotulo} ==")
    print(f"  worktree  : {worktree}")
    if a.solo_lectura:
        print("  perfil    : SOLO LECTURA — NINGUNA ruta escribible (ni worktree, ni gitdir, "
              "ni /tmp: todo el filesystem read-only)")
    else:
        print(f"  gitdir    : {gitdir if gitdir else PLACEHOLDER}")
        print(f"  común     : {commondir if commondir else PLACEHOLDER}")
    print(texto)
    print("\n  comando envuelto:")
    print("    " + " ".join(shlex.quote(x) for x in argv))

    if a.ejecutar:
        print("\n  --ejecutar: lanzando…")
        os.execvp(argv[0], argv)  # reemplaza este proceso; no vuelve si tiene éxito
    else:
        print("\n  (dry-run: usa --ejecutar para lanzarlo de verdad)")
    sys.exit(0)


if __name__ == "__main__":
    main()
