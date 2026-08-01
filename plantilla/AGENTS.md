# AGENTS.md — {{TITULO}} (meta-repo)

Este es el **meta-repo de orquestación**: aquí vive todo el pensamiento del proyecto (docs/)
y el método de trabajo. El código vive en OTRO repositorio, clonado en `main/` (solo lectura)
y trabajado en `worktrees/` (una copia por unidad de trabajo). Ambos ignorados por git aquí.

## Al arrancar (haz esto antes que nada)

1. **Actualiza el taller:** ejecuta `setup.py` con el Python disponible. Esto coloca
   `main/` en la última `origin/main` mediante fast-forward; si no puede, PARA y explica
   por qué. Nunca trabajes desde una referencia remota antigua.
2. **Linta el método:** `python docs/00-metodo/scripts/lint_metodo.py`. Un FAIL se arregla
   antes de seguir (regla dura 13).
3. **Lee `docs/05-trabajo/ESTADO.md`**: dónde estamos, qué hay en vuelo y qué toca ahora.
4. **Declara tu rol al usuario y confírmalo ANTES de trabajar.** Ofrécele los tres:
   - **CONSTRUCTOR** (el de por defecto): construye, especifica, despacha y cierra unidades.
   - **OBSERVABILIDAD** (solo lectura): revisa el estado real del sistema y reporta; no arregla.
   - **DEPLOY**: el único con manos en producción.

   Un rol = una sesión: **no se mezclan** (cambiar de rol es abrir sesión nueva). Si el
   usuario no dice otra cosa, trabajas como CONSTRUCTOR. Para tocar flujos, el CONSTRUCTOR
   asume el rol ANALISTA DE FLUJOS y sigue el runbook de requisitos (regla 14). Detalle,
   permisos y hard-gates de cada rol: `docs/00-metodo/roles.md`.

## Orden de lectura (router) — lee solo lo que tu tarea necesita

| Si vas a… | Lee |
|---|---|
| Orientarte (¿dónde estamos?) | `docs/05-trabajo/ESTADO.md` |
| Entender qué es esta aplicación | `docs/01-constitucion/manifiesto.md` |
| Decidir o dudar sobre tecnología | `docs/01-constitucion/bias.md` |
| Entender el negocio y sus actividades | `docs/02-flujos/INDICE.md` (el detalle de una actividad, solo si la tocas) |
| Saber cómo trabajamos (fases, carriles, tipos) | `docs/00-metodo/README.md` |
| Detalle de tu rol (analista · constructor · observabilidad · deploy) | `docs/00-metodo/roles.md` |
| Trabajar la unidad NNN | `docs/05-trabajo/NNN-*/especificacion.md` (contrato + plan) |
| Reportar o trabajar un bug | `docs/bugs/NNN-slug.md` + runbook `bug` (ADR-006) |
| Cerrar una unidad (de cualquier tipo) | `docs/00-metodo/runbooks/cierre.md` |
| Saber qué hay instalado en esta máquina | `python docs/00-metodo/scripts/doctor.py` |
| Cambio trivial que no cambia comportamiento | `docs/00-metodo/runbooks/expres.md` |
| Producción caída / urgencia | `docs/00-metodo/runbooks/hotfix.md` |
| Añadir, cambiar o aprobar flujos y requisitos | `docs/00-metodo/requisitos/RUNBOOK.md` |
| Consultar cimientos técnicos del proyecto | `docs/03-investigacion/SINTESIS.md` (lo escribe la fase 3) |
| Ver el roadmap | `docs/04-planificacion/ROADMAP.md` (lo escribe la fase 4) |
| Entender un porqué del MÉTODO | `docs/00-metodo/decisiones/` |
| Entender un porqué de ESTE proyecto | `docs/decisiones/` |
| Aprovechar lo ya aprendido | `docs/conocimiento/` |

## Reglas duras

1. **Roles.** El agente padre (la sesión que habla con el usuario) trabaja SOLO en este
   meta-repo y **jamás escribe código**. Los subagentes constructores trabajan SOLO en su
   `worktrees/NNN-slug/`.
2. **Escritura.** Un constructor escribe únicamente en su worktree y en su unidad:
   `hallazgos.md` + casillas `[x]` del plan (bugs: su fichero `docs/bugs/NNN-slug.md`). Los
   ficheros compartidos — `ESTADO.md`, `INDICE.md`, `ROADMAP.md`, `conocimiento/`,
   `decisiones/` — los escribe SOLO el padre, en el ritual de cierre. Una unidad
   `auditoria`, `investigacion` o `documentacion` despachada con `--documental` no crea
   worktree: su subagente lee `main/` y escribe únicamente dentro de SU carpeta de unidad.
3. **Git del meta-repo: solo el padre**, con rutas explícitas. Nunca `git add -A`.
4. **Numeración y despacho: con el script, no a mano.**
   `python docs/00-metodo/scripts/unidad.py nnn | nueva <tipo> <slug> | despachar <NNN-slug>
   | estado`. Asigna el `NNN` (nunca se renumera), crea la unidad desde su plantilla ANTES
   que el worktree, y bloquea el despacho si la spec sigue vacía o si ya hay trabajo en
   vuelo. `--force` (solo hotfix) salta la puerta dejando la deuda escrita.
5. **Trabajo en vuelo: UNA unidad por defecto.** Paralelo solo para unidades que no comparten
   ningún fichero (declarado en cada especificación), tope 2-3.
6. **Búsquedas de código: dentro de `main/` o de tu worktree.** Desde la raíz no verás código
   (el gitignore lo oculta a las herramientas de búsqueda); eso es intencional.
7. **Merge y cierre son indivisibles.** Cerrar CUALQUIER unidad = verificar con evidencia →
   revisar (agente fresco, diff contra especificación) → merge → **suite end-to-end completa
   sobre main** → **lanzar una instancia de la app y que el usuario la pruebe** (sin su OK no
   hay cierre) → aplicar los deltas declarados al mapa → promover hallazgos/decisiones →
   actualizar `ESTADO.md` e `INDICE.md` → mover la unidad a `archivo/` → borrar worktree y
   rama. No existe "mergeado pero sin cerrar". El ritual completo, sus dos caminos (con `gh`
   y sin él) y la frontera del revisor: `runbooks/cierre.md`; los pasos mecánicos los hace
   `unidad.py cerrar`. (Único matiz de los bugs: su fichero NO se archiva, permanece en
   `docs/bugs/` — ADR-006.)
8. **Desviación de contrato → PARA y escala.** Si al construir descubres que tu trabajo
   contradiría la especificación o el mapa (eliminar algo, cambiar comportamiento prometido),
   no improvises: detente y devuelve la tarea al padre. Las desviaciones de implementación
   (cambia el cómo, no el contrato) se terminan y se reportan en `hallazgos.md`.
9. **Carriles.** Exprés: el diff cabe en una frase Y no cambia comportamiento → sin documentos,
   directo. Normal (default): una unidad con su `especificacion.md` (contrato + plan). Completo
   (transversal, arriesgado o desconocido): añade `investigacion.md`. **Si cambia
   comportamiento, nunca es exprés** (necesita declarar sus deltas al mapa). Producción
   caída: runbook `hotfix.md` (única vía que se salta la espera de aprobación).
10. **La especificación es el punto de entrada, no una celda.** Autocontenida (contexto,
    criterios, plan, verificación); puedes leer libremente la documentación que necesites.
11. **Fuentes en investigación:** doc oficial > más reciente; toda afirmación con fuente y
    fecha. Sin fuente = se declara como opinión.
12. **Evidencia, no afirmación.** Nada se da por hecho sin el output del check que lo
    demuestra (tests, capturas). "Hecho" sin evidencia no es hecho.
13. **El método también se lintea.** Al arrancar sesión del padre y como último paso de todo
    cierre: `python docs/00-metodo/scripts/lint_metodo.py`. Un FAIL se arregla antes de
    seguir; la estructura solo cambia con ADR.
14. **Los flujos siguen vivos.** Ante un cambio de comportamiento, asume el rol ANALISTA DE
    FLUJOS y sigue `docs/00-metodo/requisitos/RUNBOOK.md`: modifica la fuente en
    `docs/02-flujos/planos/`, enseña el visor web y obtén la aprobación del usuario ANTES de
    crear unidades de código (ADR-007).
15. **Este workspace funciona con CUALQUIER agente** (Claude, Codex, OpenCode, Antigravity…).
    Las capas duras son agnósticas: este AGENTS.md (estándar), los scripts (`unidad.py`,
    `lint_metodo.py`) y el hook `.githooks/pre-push` (lo ejecuta git, no el agente).
    El repositorio no distribuye carpetas de configuración privadas de ningún harness.

## Reglas de oro (siempre)

- **Producción y servicios externos (pagos, DNS, correo, chat) son LECTURA por defecto.**
  Cualquier mutación exige autorización explícita del usuario.
- **Fusionar main NO despliega.**
- **Nunca mostrar secretos ni PII.** Viven en `.private/` (referencia por ruta, jamás copia);
  lo generado (logs, capturas, dumps), en `.runtime/`. Ambos fuera de git.
- **Antes de afirmar que algo funciona, ejecutar la verificación que lo demuestra.**

## Autoridad de la información (qué fuente manda en conflicto)

- El código y sus tests describen el producto de su rama.
- `docs/` describe el workspace y el método.
- `git -C main worktree list` es el inventario autoritativo de worktrees.
- `docs/bugs/` es la verdad de los bugs.
- Los papeles de una unidad archivada son historia, no doctrina.
- Lo escrito gana a lo recordado.

## El repo de código

- `main/` — clon canónico. Solo `git pull`. **Jamás editar, commitear ni crear ramas aquí.**
  Única excepción, nombrada y acotada (ADR-009): el merge del paso 3 del cierre cuando esta
  máquina no tiene `gh` — camino B de `runbooks/cierre.md`. Nada más.
- `worktrees/NNN-slug/` — worktree en rama `NNN-slug`, espejo de `docs/05-trabajo/NNN-slug/`.
  Se crea al despachar la unidad y se borra en el cierre.
- Todo PR lleva `NNN-slug` en el título y enlaza su unidad.

## Origen de este workspace

Creado con el bootstrap de la herramienta de ingeniería de requisitos, desde los planos de la
entrevista. La constitución y los flujos (`01-constitucion/manifiesto.md`, `02-flujos/`) son
salida compilada de los planos: **no se editan a mano** — un cambio de negocio se hace
siguiendo `docs/00-metodo/requisitos/RUNBOOK.md`. El método
(`docs/00-metodo/`) viaja con la plantilla de la herramienta; aquí no se modifica sin ADR.
