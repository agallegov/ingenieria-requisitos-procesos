# Aislamiento opcional de constructores

`scripts/sandbox_lanzar.py` es una ayuda avanzada para envolver el proceso de un
constructor y limitar las rutas en las que puede escribir. No se ejecuta
automáticamente, no sustituye los permisos del sistema y no constituye por sí solo
una garantía de seguridad.

## Uso seguro

1. Crea la unidad y su worktree mediante `unidad.py`.
2. Ejecuta primero `sandbox_lanzar.py` sin `--ejecutar` y revisa el mecanismo y las
   rutas que muestra.
3. En esa máquina concreta, comprueba con un comando inocuo que escribir fuera del
   worktree falla y que el trabajo Git permitido sigue funcionando.
4. Solo después usa `--ejecutar`. Si cambia el sistema operativo o la herramienta de
   aislamiento, repite la comprobación.

Mecanismos por plataforma, en el orden real del código: en macOS, `sandbox-exec` (Seatbelt) y
después `srt`; en Linux, `bwrap` y después `srt`. Un `srt` que no sea propiedad de root se
rechaza (`EXIGIR_OWNER_SISTEMA`): un binario que puede reemplazar el mismo usuario no es una
frontera. Consecuencia honesta: en un macOS típico el mecanismo será Seatbelt, cuyo perfil NO
limita la red. Si no encuentra ningún mecanismo se niega a ejecutar. No hay bypass ni modo que
solo imprima un perfil.

## Límites que intenta aplicar

- Escritura en el worktree y en las zonas Git necesarias para guardar un commit.
- Bloqueo de los puntos de configuración y hooks compartidos de Git.
- Bloqueo de lectura de directorios habituales de credenciales.
- Red denegada o limitada cuando el mecanismo elegido puede aplicarlo realmente.

Los worktrees comparten parte del repositorio Git. Por eso ampliar permisos al Git
común es una decisión explícita (`--git-compartido`) y debe evitarse si no hace falta.
Las ramas alternativas de sistema operativo pueden tener limitaciones distintas; el
resultado impreso por el programa es la fuente que se debe revisar antes de lanzar.

Para código hostil o ejecución desatendida se necesita además una frontera administrada por el
dueño de la máquina. Seatbelt está deprecado y ni Seatbelt ni bwrap filtran red por dominio;
esa garantía solo la da un `srt` propiedad de root o un contenedor con política de red
validada — y en su ausencia este método NO promete red limitada: lo dice el recibo de la
ejecución, no lo disimula.
La ruta y el SHA-256 no protegen frente a un atacante con el mismo UID que pueda sustituir el
wrapper justo antes de `exec`; ese caso necesita aislamiento administrado por otro principal.
