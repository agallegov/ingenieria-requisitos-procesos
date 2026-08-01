# Runbook · FEATURE

**Cuándo:** el usuario entra en la carpeta, lanza su harness (rol CONSTRUCTOR por defecto,
según el router) y pide comportamiento nuevo: "quiero una feature: la aplicación debe hacer
esto, esto y esto".
**Plantilla:** `especificacion.md` (documento único: contrato + plan de trabajo — ADR-005).
**Contrato de cierre:** los criterios de aceptación de la spec en verde con evidencia + el
flujo del mapa en `entregada` + validación del usuario sobre la app corriendo.

## Regla de carril

Una feature cambia comportamiento → **nunca es exprés**. ¿Transversal, arriesgada o
territorio desconocido? → carril completo (`investigacion.md` de la unidad). Si no: normal.

## El flujo, paso a paso

(Pasos 1-4 = fase 5, especificar · paso 5 = fase 6, construir · paso 6 = fase 7, cerrar.)

1. **Encaje con los flujos de usuario (`02-flujos/`).** Tres casos: (a) encaja tal cual con
   los flujos actuales → seguir; (b) modifica un flujo existente → se habla con el usuario,
   se le plantea cómo quedaría el flujo nuevo (en la web de flujos) y se acuerda; (c) es un
   flujo nuevo → se añade y aparece en la web de flujos. Lo que se edita es SIEMPRE la fuente
   —`docs/02-flujos/planos/planos.json`, siguiendo el runbook de requisitos—, nunca los
   `.md` compilados a mano. Para enseñárselo: primero
   `python docs/00-metodo/requisitos/validar_web.py --datos docs/02-flujos/planos/planos.json`
   (si falla, no se da la URL ni se pide aprobación) y después
   `python docs/00-metodo/requisitos/servir.py --datos docs/02-flujos/planos/planos.json`
   → **http://127.0.0.1:8765/**, que se refresca sola cada 3 s: se edita el JSON y el usuario lo
   ve al momento en pantalla. El flujo acordado queda ESCRITO en el mapa con estado
   `especificada` (vocabulario del aparato, `00-metodo/README.md`); el cierre lo pasará a
   `entregada`.
   `<HARD-GATE>` **El flujo acordado queda ESCRITO en el mapa y APROBADO por el usuario sobre la
   web ANTES de especificar nada.** Sin eso no se pasa al paso 2: no se abre unidad, no se asigna
   `NNN`, no se escribe spec.
   (El aparato de flujos — runbook + web — viene heredado de la herramienta de ingeniería de
   requisitos; aquí no se reinventa, se usa.)
2. **¿Hace falta investigar?** Contra el stack actual (`01-constitucion/bias.md` +
   `03-investigacion/SINTESIS.md` — **ese fichero lo crea la fase 3**, `runbooks/investigacion.md`;
   aún no existe: si la feature depende de él, correr la fase 3 es el paso previo; si no, manda
   el bias a secas): ¿esto ya sabemos hacerlo? Cubierto → adelante sin
   investigación. Territorio nuevo → pequeña investigación primero (carril completo:
   plantilla `investigacion.md` de la unidad; si es un tema de proyecto, se añade a la
   fase 3 por su ritual).
3. **Planificación de la feature, debatiendo con el usuario.** En cristiano, mínimo lenguaje
   técnico ("aprovechando lo que ya usamos, crearía una tabla en la base de datos que guarde
   X…"). OBLIGATORIO en este paso: buscar en el código (`main/`) si ya existe otro
   componente/módulo que haga esto o algo parecido — NO se duplica código ni
   responsabilidades. Principios innegociables del diseño: Single Responsibility, KISS,
   clean code; encapsular por funcionalidades con capas de abstracción; los módulos se
   comunican entre ellos. Prioridad nº 1: que el discovery de código de los agentes sea lo
   más barato posible en tokens — una funcionalidad vive en SU módulo, no desperdigada por
   toda la app. Si la feature corresponde a módulos preexistentes → se encaja ahí
   (refactorizando si hace falta), JAMÁS duplicando sistemas.
   `<HARD-GATE>` **El usuario aprueba la planificación.**
4. **Spec file.** El padre crea la unidad **con el script, no a mano**:
   `python docs/00-metodo/scripts/unidad.py nueva feature <slug>` (asigna el siguiente `NNN`
   desde main y copia `plantillas/especificacion.md` a `docs/05-trabajo/NNN-slug/`).
   Rellena el contrato:
   **Qué** y **Criterios (R\*)** en idioma de negocio, con el vocabulario del mapa (cada
   criterio convertible en test, al menos un caso límite, datos reales del negocio);
   **Deltas al mapa** (el flujo acordado en el paso 1) — si la feature elimina o contradice
   algo del mapa, el usuario lo aprueba AHORA, no en el cierre; **Cómo** (bias + SINTESIS si
   ya existe; desviación del bias → ADR primero, spec después); **ficheros** (ownership contra las
   unidades en vuelo de `ESTADO.md`: si comparte ficheros con otra → secuenciales; hotspots
   — migraciones de BD, rutas, modelos compartidos, lockfiles — secuenciales SIEMPRE).
   Después, el **Contexto para el constructor** (rutas exactas — la carga automática NO
   funciona, ADR-001) y el **Plan de trabajo** (esqueleto fijo; pasos extra solo si esta
   unidad los necesita). Test de autocontención: ¿un constructor sin NADA de contexto previo
   puede trabajar leyendo solo esta spec + su contexto? Si no → reescribir.
   `<HARD-GATE>` **El usuario anota el contrato** (lee, corrige, aprueba — su ritual de
   mayor apalancamiento). Su OK lo escribe ÉL como `aprobado: YYYY-MM-DD` en el frontmatter
   (`00-metodo/README.md`): sin esa fecha no hay despacho, y el script lo bloquea.
5. **Despacho y obra.** El padre despacha **con el script, no a mano**:
   `python docs/00-metodo/scripts/unidad.py despachar NNN-slug`, que crea la rama `NNN-slug`
   desde la rama principal (remota si existe; local si aún no se conectó GitHub), con su
   checkout en `worktrees/NNN-slug`, y **aplica las
   precondiciones** (contrato aprobado por el usuario, contrato con prosa real, tope de trabajo
   en vuelo, rama no reutilizada); el camino manual las salta todas. La rama es local hasta el
   push del PR. Después el padre actualiza `ESTADO.md` y lanza el subagente constructor con la
   especificación como punto de entrada (estado → `en_obra`). El constructor trabaja
   ÚNICAMENTE en esa rama/worktree, ejecutando el Plan de trabajo en orden y marcando `[x]`:
   PRIMERO crea los tests que la feature necesita — de integración, end-to-end, y unit
   tests si hacen falta — y deben FALLAR (rojo); después implementa hasta que TODO esté
   verde, SIN tocar los tests; suite completa y evidencia pegada (Definición de hecho de la
   spec cumplida). Commit, push, **pull request** (título con `NNN-slug`), y la rama queda
   PENDIENTE DE APROBACIÓN (estado → `en_revision`). Sorpresas → `hallazgos.md`.
   Contradicción con la spec o el mapa → **PARAR y devolver la tarea**.
6. **Cierre (el padre, a petición del usuario).** Es el ritual indivisible de
   `runbooks/cierre.md` (con `gh` y sin `gh`), cerrado con `unidad.py cerrar` — aquí solo lo
   específico de una feature. Resumen de los 10 pasos en
   `00-metodo/README.md` — aquí solo lo específico de una feature. Verificar la evidencia
   (¿el output es real y completo?) → revisor fresco (sesión/subagente nuevo, solo lectura):
   *"Revisa el diff contra especificacion.md: cada R\* implementado, los casos límite con
   test, y nada fuera de los ficheros declarados. Comprueba además que los ficheros de test
   NO se modificaron después del commit que los creó —ni se debilitaron, ni se borraron, ni se
   marcaron como saltados para que pasara el código— y que la feature no DUPLICA funcionalidad
   que ya existía en otro módulo de `main/`. Reporta solo huecos de corrección, no
   preferencias de estilo."* — veredicto a la sección **Revisión** del `hallazgos.md`; huecos
   de corrección → vuelven al constructor; limpio → merge del PR → **suite end-to-end
   completa sobre main** → **el padre lanza una instancia de la app** (comando de arranque:
   el `AGENTS.md` del repo de código) y el usuario la valida en **modo novato**, probando los
   ejemplos reales de los R\*. `<HARD-GATE>` Sin ese OK no hay cierre; "no es lo que pedí" →
   nueva unidad tipo `bug`. Con el OK, consolidar: aplicar los Deltas a `02-flujos/` y pasar
   el flujo del mapa a **`entregada`** · cosechar `hallazgos.md` (conocimiento/, ADRs, nuevas
   unidades al ROADMAP — lo crea la fase 4, `runbooks/planificacion.md`; mientras no exista,
   se quedan anotadas en `hallazgos.md`) · actualizar `ESTADO.md` + `INDICE.md` · mover la unidad a `archivo/`
   · borrar worktree y rama (estado → `mergeada`).
