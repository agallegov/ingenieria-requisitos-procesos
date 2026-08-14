# El Método — manual de operación

## Principio rector: sistema cerrado

Este método deja **lo mínimo posible a la imaginación y a la variabilidad entre sesiones**:

- Todo lo repetible está en una **plantilla** (se rellena), un **runbook** (se sigue paso a
  paso), un **script** (se ejecuta) o un **hook** (se cumple solo).
- El agente **rellena y ejecuta; no inventa**. Formatos, estados y rituales son vocabulario
  cerrado: no se crean variantes.
- Lo que el método no cubre **se escala al padre; no se improvisa**.
- Regla de confianza: script/hook (se cumple solo) > plantilla (guía la forma) > prosa (se pide).

## Las 7 fases

| # | Fase | Nivel | Produce |
|---|---|---|---|
| 1 | Constitución | proyecto | `01-constitucion/` — manifiesto + bias tecnológico |
| 2 | Flujos | proyecto | `02-flujos/` — mapa del negocio por actividades (de la entrevista) |
| 3 | Investigación | proyecto | `03-investigacion/` — cimientos técnicos (multi-rol, multi-sesgo, acotada por el bias) |
| 4 | Planificación | proyecto | `04-planificacion/ROADMAP.md` — unidades, orden, dependencias; esqueleto andante primero |
| 5 | Especificación | unidad | `05-trabajo/NNN-slug/especificacion.md` — contrato + plan de trabajo (ADR-005) |
| 6 | Construcción | unidad | el subagente constructor implementa el plan en su worktree |
| 7 | Cierre | unidad | verificar → revisar → merge → e2e + instancia validada → consolidar (indivisible; `runbooks/cierre.md`) |

Las fases 1-4 se recorren al arrancar el proyecto y se **actualizan** después (nunca se
re-hacen enteras). Las fases 5-7 se repiten por cada unidad de trabajo.

## Los 3 carriles (criterio de entrada, obligatorio decidirlo al abrir trabajo)

| Carril | Criterio de entrada | Papeles |
|---|---|---|
| **Exprés** | El diff cabe en una frase **Y** no cambia comportamiento | Ninguno — el rastro es el commit/PR (runbook `expres.md`) |
| **Normal** (default) | Todo lo demás | `especificacion.md` (contrato + plan de trabajo) |
| **Completo** | Transversal, arriesgado, o toca territorio desconocido | + `investigacion.md` de la unidad |

Si cambia comportamiento, **nunca** es exprés (debe declarar deltas al mapa).
Producción caída para usuarios reales no es un carril sino una **excepción de despacho**:
runbook `hotfix.md` (bug P0 que se salta la espera de aprobación, nunca la verificación).

## Los 7 tipos de unidad (cada uno con su runbook y su plantilla)

| Tipo | Contrato de cierre |
|---|---|
| `bug` | Fichero vivo en `docs/bugs/` que NO se archiva (ADR-006): tests de integración + e2e (+ unit si hacen falta) en rojo → fix → verde, sin tocar los tests + regresión contraprobada |
| `feature` | Comportamiento nuevo verificado por los criterios de la especificación |
| `refactor` | Nada observable cambia; la suite existente sigue verde |
| `migracion` | Mismo comportamiento sobre base nueva; suite completa |
| `auditoria` | Informe con hallazgos verificados (no toca código); los aceptados paren unidades |
| `investigacion` | Preguntas respondidas con fuentes → se promueve a `conocimiento/` |
| `documentacion` | Docs correctos verificados contra la realidad |

## Vocabulario cerrado de estados

- **Unidad** (`estado:` en el frontmatter de su especificación):
  `planificada → en_obra → en_revision → mergeada` · desvíos: `bloqueada`, `descartada`.
  Al cerrar, la carpeta pasa a `archivo/` (estado final implícito: archivada).
- **Actividad**: la fuente de verdad es `02-flujos/planos/planos.json`, que lo escribe el
  aparato heredado de ingeniería de requisitos (ADR-007); `02-flujos/INDICE.md` lo refleja.
  Manda el vocabulario del aparato —
  `sin empezar → en entrevista → especificada → en obra → entregada` — y estas son las
  equivalencias con los nombres cortos que usan los runbooks: `por_descomponer` = *sin
  empezar*, `en_obra` = *en obra*. No se crean más variantes.

## Frontmatter obligatorio de `especificacion.md`

```yaml
---
unidad: NNN-slug
tipo: bug | feature | refactor | migracion | auditoria | investigacion | documentacion
carril: normal | completo
estado: planificada | en_obra | en_revision | mergeada | bloqueada | descartada
aprobado: no | YYYY-MM-DD
actividad: <id del INDICE de flujos>
ficheros: [rutas que esta unidad posee — dos unidades paralelas jamás comparten]
actualizado: YYYY-MM-DD
---
```

**`aprobado:` lo pone el USUARIO, nunca el agente.** Es el rastro comprobable del
`<HARD-GATE>` de la especificación: `no` mientras no lo haya leído y aceptado, y la **fecha
del día en que lo aprueba** cuando da su OK (se exige fecha y no un "sí" porque una fecha dice
*cuándo* se leyó). Sin esa fecha, `unidad.py despachar` **bloquea** y el linter da FAIL si
encuentra una unidad `en_obra`/`en_revision` sin ella. Única excepción: el hotfix P0
(`--force --motivo "…"`), que deja marca de deuda con reloj de 24 h.

## Los rituales (pasos fijos, en orden, sin saltos)

**Despacho de una unidad** (el padre): 1. asignar NNN y crear `05-trabajo/NNN-slug/` en main ·
2. rellenar especificación desde plantilla · 3. el usuario anota y aprueba el contrato, y su OK
queda escrito como `aprobado: YYYY-MM-DD` (sin esa fecha `unidad.py despachar` bloquea) ·
4. rellenar contexto y plan de trabajo (misma spec) · 5. crear worktree `NNN-slug` · 6. lanzar
constructor con la especificación como punto de entrada · 7. actualizar ESTADO.md.

**Cierre de una unidad** (el padre, **a petición del usuario**, indivisible, sea del tipo que
sea): el ritual completo, con sus dos caminos (con `gh` y sin él) y la frontera del revisor,
vive en **`runbooks/cierre.md`**, que es por donde cierran TODOS los tipos. En corto:
1. verificar con evidencia (checks + output) · 2. revisor fresco: diff contra especificación
(requisitos, edge cases, alcance; **que los ficheros de test no se tocaron después del commit
que los creó** y **que no se ha duplicado un módulo que ya existía en `main/`**) — veredicto a
la sección **Revisión** de `hallazgos.md`, firmado con `revisor:` y `revisado:`; huecos →
vuelven al constructor · 3. merge · 4. **tests sobre main al nivel del carril** (ADR-016;
tabla exacta en `runbooks/cierre.md`) · 5. **lanzar
una instancia de la app** (comando de arranque: el `AGENTS.md` del repo de código) y
**validación del usuario sobre ella**; sin su OK no hay cierre, "no es lo que pedí" → unidad
`bug` · 6. `unidad.py cerrar NNN-slug --ok-usuario YYYY-MM-DD`, que aplica las puertas y hace
lo mecánico (estado `mergeada`, archivar la unidad — los bugs no, ADR-006 —, borrar worktree y
rama **local** — la remota NO se borra jamás: es la única copia del trabajo fuera de este
disco (ADR-011) —, y lintar) · 7. lo que es criterio y no mecánica, que sigue siendo del
padre: aplicar deltas a `02-flujos/`, promover hallazgos → `conocimiento/` y decisiones →
`decisiones/`, y actualizar `ESTADO.md` + `INDICE.md`.

**Frontera del revisor** (ADR-009): devuelven el trabajo al constructor los incumplimientos
del contrato de ESA unidad, los fallos de seguridad y lo que pierda datos — nada más. Riesgos
de flujos futuros y mejoras se anotan como trabajo descubierto y NO reabren la unidad; solo un
fallo crítico permite una segunda ronda. Preparar hoy problemas que aún no existen retrasa lo
único que enseña de verdad: que el usuario use la aplicación.

## Piezas del método

- `runbooks/` — además de los 7 tipos: `cierre.md` (**el ritual de cierre, común a todos los
  tipos**, con el camino con `gh` y el camino sin él), `expres.md` (carril exprés: rama
  efímera, sin unidad) y `hotfix.md` (producción caída: se salta la espera de aprobación, con
  deuda de spec a pagar en 24 h). Cada tipo tiene su recorrido, sus puertas y su cierre.
  `investigacion.md` es también el runbook de la fase 3; `planificacion.md`, el de la fase 4.
- `plantillas/` — por unidad: especificacion (contrato + plan de trabajo, ADR-005),
  bug (fichero vivo en `docs/bugs/`, ADR-006), hallazgos, investigacion (carril completo) ·
  por proyecto: informe y sintesis (fase 3), roadmap (fase 4), y `agents-repo-codigo.md` (el
  AGENTS.md que la primera unidad deja DENTRO del repo de código, con los comandos exactos de
  entorno, suite, e2e, instancia para el usuario y seguridad).
- `roles.md` — los roles del padre (analista de flujos, constructor, observabilidad, deploy),
  con la entrevista de arranque `<HARD-GATE>` de los dos operativos (ADR-008).
- `decisiones/` — **los ADR DEL MÉTODO**: el porqué de estas reglas. El índice es el listado
  de la carpeta (`ls`), no una lista escrita a mano que se queda atrás. Se leen, no se editan;
  cuando un runbook cita "ADR-005", está aquí. Las decisiones de TU proyecto van en
  `docs/decisiones/`, con numeración propia desde `001` y citadas como `DP-NNN`: así
  `ADR-NNN` señala siempre, sin ambigüedad, a esta carpeta.
- `requisitos/` — el kit heredado de la herramienta de ingeniería de requisitos: runbook,
  visor web y scripts para mantener vivos los `planos.json` de `02-flujos/` (ADR-007).
- `auditoria-metodo.md`, `auditoria-calidad.md`, `auditoria-seguridad.md`,
  `seguridad-por-stack.md`, `sandbox.md` y `scripts/lint_deploy.py` ·
  `scripts/sandbox_lanzar.py` — playbooks y herramientas extra que la plantilla añade para las
  skills de auditoría y el gate de pre-despliegue.
- `scripts/unidad.py` — **el despachador**: `nnn` (siguiente número libre, mirando unidades,
  archivo, bugs y ramas) · `nueva <tipo> <slug>` (crea la unidad desde su plantilla) ·
  `despachar <NNN-slug>` (crea rama y worktree, y BLOQUEA si falta la aprobación del usuario
  —`aprobado:` sin fecha—, si la spec no tiene prosa real o si ya hay trabajo en vuelo;
  `--force` es la válvula de producción caída: **solo** unidades tipo `bug` con severidad
  **P0** declarada y `--motivo "…"` obligatorio, que se escribe en la ficha junto a la deuda) ·
  `cerrar <NNN-slug> --ok-usuario YYYY-MM-DD` (**el cierre**: puertas —OK del usuario con
  fecha, revisión firmada por alguien distinto del constructor, worktree sin nada sin guardar,
  rama fusionada de verdad— y después la mecánica; ADR-009) · `estado`.
- `scripts/doctor.py` — **qué hay de verdad en esta máquina** (Python, git y su identidad,
  `gh`, Docker, Node) y qué implica cada ausencia. Lo corre `setup.py` y la fase 4: el ROADMAP
  no fija una herramienta que no esté aquí en verde. Informa, nunca bloquea.
- `scripts/lint_metodo.py` — **el linter del método**: valida estructura congelada,
  vocabulario cerrado, frontmatters, aprobación del usuario en lo que está en obra, deudas de
  hotfix sin pagar (WARN dentro de las 24 h, FAIL pasadas o si la unidad ya está mergeada),
  ESTADO ≤100, coherencia worktrees↔unidades, cierres a medias, **trabajo huérfano** (worktree
  con cambios sin guardar, rama que dice estar terminada sin un solo commit) y **secretos
  horneables** (Dockerfile sin `.dockerignore` que excluya el `.env`). Se ejecuta al arrancar
  sesión del padre, al final de cada cierre, y en CI.
- El **bootstrap** no vive aquí sino en la herramienta de ingeniería de requisitos
  (`visor/bootstrap.py`, junto a su `plantilla/`): es la ÚNICA forma de crear un workspace,
  y es quien coloca este `00-metodo/` en cada proyecto (ADR-002).

**Principio rector de esta fase: sencillez Barrio Sésamo.** Lo mínimo que cumpla el trabajo,
invisible para el usuario final; ante la duda, la pieza NO se construye. Descartado por
simplicidad: el presupuesto de tokens por unidad — el límite real de atención ya es UNA unidad
en vuelo.

**Iteración corta, no entrega perfecta.** La pregunta que ordena el trabajo no es "¿está todo
previsto?" sino **"¿cuál es la parte más pequeña que podemos poner hoy delante del usuario
para aprender algo?"**. De ahí: unidades pequeñas y contratos breves · un constructor y UNA
revisión · resolver el problema de hoy y no los futuros · pruebas sobre el comportamiento
nuevo, no sobre escenarios que aún no existen · enseñar cada incremento cuanto antes. Lo que
NO se recorta nunca, porque no es ceremonia sino garantía: no perder datos, no filtrar
secretos y no romper lo que el usuario ya aprobó.
