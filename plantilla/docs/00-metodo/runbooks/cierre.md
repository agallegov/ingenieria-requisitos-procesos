# Runbook · CIERRE (el padre, a petición del usuario)

**Cuándo:** una unidad de CUALQUIER tipo está terminada y el usuario pide cerrarla.
**Vale para todos los runbooks:** `feature`, `bug`, `refactor`, `migracion`, `documentacion`,
`auditoria`, `investigacion`, `hotfix` y `expres` cierran POR AQUÍ. Su runbook describe lo
específico de su tipo; el cierre es este y es el mismo para todos.
**Contrato de cierre:** el trabajo está fusionado en la rama principal, revisado por alguien
distinto de quien lo hizo, y el usuario lo ha probado sobre la app corriendo.

## Los dos caminos (los decide el doctor, no el paso 7)

`python docs/00-metodo/scripts/doctor.py` dice si esta máquina tiene `gh`. **Se mira al
arrancar el proyecto, no al llegar aquí**: descubrir en el paso del pull request que no hay
GitHub es descubrirlo con el código ya terminado.

| | **Camino A — con `gh`** (lo normal) | **Camino B — sin `gh`** (o sin GitHub) |
|---|---|---|
| Dónde termina el constructor | pull request abierto, rama empujada | rama local (o empujada, si hay remoto) |
| Qué mira el revisor | el diff del PR | `git -C main diff main..NNN-slug` |
| Dónde queda el veredicto | sección **Revisión** de `hallazgos.md` | igual: sección **Revisión** de `hallazgos.md` |
| Quién fusiona y cómo | el padre: `gh pr merge NNN-slug` | el padre: `git -C main merge --ff-only NNN-slug` **y después `git -C main push origin main`** |

**Camino B: el push de la rama principal NO es opcional.** Al despachar, la rama de cada
unidad nace de `origin/<principal>`. Si el merge se queda en local, la siguiente unidad parte
de una base vieja y su merge ya no será un fast-forward: a partir de ahí cada cierre pelea con
git. Si el proyecto no tiene remoto, no hay nada que empujar y esto no aplica.

**La excepción nombrada de `main/`.** La regla es que `main/` es de solo lectura
(`AGENTS.md`). El camino B la rompe una vez, a propósito y con nombre: **el merge del paso 3
de este ritual, y nada más**. Ni editar ficheros, ni crear ramas, ni commitear a mano allí.
Sin esta excepción escrita, el método obligaba a improvisar justo en el paso más delicado.

## El ritual (indivisible: no existe "fusionado pero sin cerrar")

**Se escribe según se hace.** Cada paso se marca en la §Bitácora del cierre de `hallazgos.md`
NADA MÁS terminarlo, con fecha y con quién lo hizo. Indivisible no significa que la sesión no
se pueda morir a mitad: significa que si se muere, la siguiente lo retoma leyendo esas
casillas — lo marcado no se repite, lo no marcado no se da por hecho— en vez de deducir de
`git log` qué pasó. Lo que solo está en el contexto de la sesión, está perdido.

1. **Verificar con evidencia.** El output real de los checks pegado en `hallazgos.md`
   (o en la ficha, si es un bug). "Hecho" sin output no es hecho.
2. **Revisor fresco.** Sesión o subagente NUEVO, solo lectura, con el diff y la
   especificación delante: cada criterio implementado, casos límite con test, nada fuera de
   los ficheros declarados, los tests no tocados después de crearse, y ningún módulo
   duplicado de lo que ya existía. Su veredicto va a la sección **Revisión** de
   `hallazgos.md`, y su nombre y la fecha al frontmatter (`revisor:`, `revisado:`) **en la
   misma escritura que el veredicto** — es el único que sabe quién es; el despacho del revisor
   se lo pide con esas palabras.
   `<HARD-GATE>` **El revisor no puede ser quien construyó.**
   `<HARD-GATE>` **Una firma que falta no se rellena después.** Si al cerrar `revisor:` sigue
   vacío, ya nadie puede saber quién revisó: se vuelve a revisar con un agente fresco. El padre
   escribiendo un nombre plausible es justo el auto-sello que este campo existe para impedir.

   **Frontera del revisor (regla, no preferencia).** Devuelven el trabajo al constructor, y
   solo ellos: los incumplimientos del contrato de ESTA unidad, los fallos de seguridad y
   todo lo que pierda datos. Un riesgo de un flujo futuro, una mejora, un "convendría dejarlo
   preparado para cuando…" **no reabren la unidad**: se anotan como trabajo descubierto y
   siguen su camino. Una segunda ronda de revisión solo la abre un fallo crítico. Preparar
   hoy problemas que aún no existen retrasa lo único que enseña de verdad: que el usuario use
   la app.
3. **Fusionar** por el camino A o el B (tabla de arriba).
4. **Suite end-to-end completa sobre la rama principal**, con los comandos del `AGENTS.md`
   del repo de código.
5. **Lanzar una instancia de la app y que el usuario la pruebe** (mismo `AGENTS.md`), con los
   ejemplos reales de sus criterios. `<HARD-GATE>` **Sin su OK no hay cierre**; "no es lo que
   pedí" no se discute: se abre una unidad tipo `bug`. La fecha de ese OK es lo que se le
   pasa al comando del paso 6.

   **Lo que se le pega en la conversación** (esto, y nada más):

   | unidad | qué se hizo | estado |
   |---|---|---|
   | 007-albaranes | editar un albarán facturado recalcula el total | listo, esperando tu OK |

   App corriendo en: `<enlace>` · Ficha: `docs/05-trabajo/007-albaranes/especificacion.md`

   …y debajo, la tabla **"Cómo lo pruebas tú"** de esa especificación (o la §6 de la ficha,
   si es un bug), tal cual. Si está en blanco, se escribe ANTES de llamarlo: sin ella el
   usuario devuelve un "me parece bien" que firma una entrega sin haber comprobado nada.

   **Si el usuario no está disponible ahora** (ADR-010): ejecuta el paso 6 SIN `--ok-usuario`.
   Aplica todas las demás puertas y, si están en verde, deja la unidad en `en_validacion`:
   fusionada y terminada, esperando solo a una persona. Deja de contar para el tope de trabajo
   en vuelo —puedes despachar otra— pero NO está cerrada: no se archiva, no se borra worktree
   ni rama, y el linter la recuerda en cada arranque. Cuando llegue el OK, el mismo comando
   con su fecha termina el ritual.
6. **Los pasos mecánicos, con el script:**

   `python docs/00-metodo/scripts/unidad.py cerrar NNN-slug --ok-usuario YYYY-MM-DD`

   Comprueba lo que no se puede saltar (OK del usuario con fecha real, revisión con veredicto
   y firma, worktree sin nada sin guardar, rama de verdad fusionada) y solo entonces hace lo
   mecánico: deja escrito el OK, anota en la ficha el commit con el que entró el trabajo
   (`fusion:`), pone la unidad en `mergeada`, borra el worktree y la rama **local**, archiva
   la unidad (los bugs no se archivan, ADR-006) y pasa el linter. Si algo falla, dice cuál y
   no toca nada.

   **La rama remota NO se borra.** `origin/NNN-slug` es la única copia del trabajo que no vive
   en este disco: se queda para siempre, y es lo que mira el cierre cuando la rama local ya no
   está. Una rama que no existe no prueba que se fusionara — prueba que alguien la borró — y
   ese es el único camino por el que este método puede perder trabajo entregado. Si no queda
   ningún rastro (proyecto sin remoto, rama borrada y ficha sin `fusion:`), el cierre BLOQUEA
   y solo se desatasca con `--fusion <sha>`, que exige un commit que exista y esté de verdad
   dentro de la principal.
7. **Lo que el script no hace, porque es criterio y no mecánica:** aplicar los deltas
   declarados a `02-flujos/` y pasar el flujo a `entregada` · promover los hallazgos a
   `conocimiento/`, `decisiones/` o al ROADMAP · actualizar `ESTADO.md` (e `INDICE.md` si es
   un bug).

## Puertas que no se negocian

- Sin OK del usuario sobre la app corriendo, no hay cierre. Ni con los tests en verde. Lo que
  `en_validacion` permite es seguir trabajando mientras se espera, no dar por cerrado.
- Sin revisor distinto del constructor, no hay cierre.
- Nada sin guardar en el worktree: es lo único del método que no respalda nadie.
- Nada se cierra sin estar fusionado en la rama principal.
- Sin un resumen que el usuario entienda, no hay cierre: si para pedirle el OK hay que
  explicarle el método, el mensaje está mal escrito (`00-metodo/comunicacion.md`).
