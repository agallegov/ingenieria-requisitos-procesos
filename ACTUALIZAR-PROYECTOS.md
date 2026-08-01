# Playbook — actualizar workspaces con un agente

Este proceso lo realiza el agente que está abierto en `ingenieria-requisitos`, siguiendo
el **Modo D** de `RUNBOOK.md`. `visor/actualizar.py` hace la parte mecánica —clasificar
cada fichero y escribir solo los que nadie tocó en ese workspace—; este playbook es el
criterio para la parte que NO es mecánica: los ficheros que ese proyecto adaptó a
propósito. Ningún script los sobrescribe.

## Entrada

1. `python visor/actualizar.py buscar` (encuentra los workspaces del disco y los
   registra; `--en RUTA` si están en un sitio poco habitual).
2. `python visor/actualizar.py revisar --todos`: qué se actualizaría solo, qué se
   añadiría, qué está **tocado** en ese workspace y qué **sobra**. No escribe nada.
3. Enséñaselo al usuario en cristiano y pregúntale cuáles quiere actualizar.
4. `python visor/actualizar.py aplicar RUTA` (o `--todos`): aplica lo seguro, deja
   `METODO.json` con la huella de cada fichero para la próxima vez, y lista lo que queda
   para ti. Si el workspace está sucio o tiene trabajo en vuelo, se niega.

## Límites duros

La actualización puede proponer cambios únicamente en:

- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` y `METODO.json`;
- `setup.py`, `.githooks/` y `.github/workflows/lint.yml`;
- `docs/00-metodo/`.

No toca `docs/01-constitucion/`, `docs/02-flujos/`, `docs/03-investigacion/`,
`docs/04-planificacion/`, `docs/05-trabajo/`, `docs/bugs/`,
`docs/conocimiento/`, `docs/decisiones/`, `repos.yaml`, `.private/`, `main/` ni
`worktrees/`. Tampoco crea, mueve o publica repositorios.

## Auditoría antes de editar

1. Comprueba que el meta-repo y `main/` están limpios.
2. Ejecuta `git -C main worktree list`; si hay una mesa adicional o una unidad
   abierta, detente.
3. Lee el router, los roles y los runbooks actuales del workspace. No juzgues un
   archivo solo por su nombre o antigüedad.
4. Compáralos con la plantilla actual y clasifica cada diferencia:
   - regla antigua que ya no se usa;
   - mejora nueva compatible;
   - personalización deliberada del proyecto;
   - duda que necesita decisión humana.
5. Presenta un resumen corto: qué conservar, qué cambiar, qué retirar y por qué.
   Si el usuario no había pedido aplicar directamente, espera su aprobación.

## Aplicación razonada

1. Guarda el estado con Git antes de editar; no uses limpieza destructiva.
2. Conserva las personalizaciones útiles y adapta las mejoras nuevas a ellas. No
   sustituyas el directorio completo a ciegas.
3. Mantén `CLAUDE.md` y `GEMINI.md` como puentes exactos a `AGENTS.md`.
4. Actualiza `METODO.json` con `{"formato": 1, "huella": HUELLA_ACTUAL}` solo
   después de completar y verificar la auditoría.
5. Ejecuta:
   - `python docs/00-metodo/scripts/lint_metodo.py`;
   - `python docs/00-metodo/requisitos/validar.py --datos docs/02-flujos/planos/planos.json --perfil borrador`;
   - las comprobaciones adicionales que exija el diff.
6. Demuestra con `git diff --stat` y `git status --short` que no se tocó ninguna
   ruta prohibida. Si se tocó, restaura solo ese cambio y vuelve a comprobar.
7. Enseña el diff al usuario. Commitea o publica únicamente si lo ha pedido.
8. Al terminar, ejecuta `python RUTA_LANZADERA/visor/proyectos.py registrar RUTA`
   para actualizar la memoria local.

## Regla final

Una huella distinta significa «hay que mirar», no «hay que sobrescribir». El agente
es responsable de entender el workspace real y conservar su intención vigente.
