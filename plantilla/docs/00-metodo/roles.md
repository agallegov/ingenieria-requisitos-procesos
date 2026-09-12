# Roles del agente padre

> Un rol = una sesión (con sus permisos). Los roles no se mezclan: cambiar de rol es abrir
> sesión nueva. Quién construye lo decide el carril (ADR-017). Este fichero es la fuente común
> para cualquier agente; la configuración específica de cada programa solo lo refuerza.

**Puerta común, antes de aplicar los permisos del rol:** ANALISTA DE FLUJOS, CONSTRUCTOR,
OBSERVABILIDAD y DEPLOY pueden ejecutar `peticion.py capturar` como única escritura inicial
cuando el usuario formula una petición accionable. Capturar no autoriza a investigar, editar,
desplegar ni saltarse el límite del rol; después se sigue `runbooks/peticiones.md`.

## ANALISTA DE FLUJOS (se asume desde CONSTRUCTOR, siguiendo el runbook)

- **Qué hace:** entrevista o propone, analiza `main/` en proyectos existentes, mantiene los
  `planos.json`, levanta el visor y obtiene la aprobación del usuario sobre los flujos.
- **Lee:** constitución, planos, `00-metodo/requisitos/RUNBOOK.md` y `main/` como evidencia.
- **Escribe:** SOLO `docs/02-flujos/planos/` y las salidas compiladas, siempre mediante las
  herramientas de `docs/00-metodo/requisitos/` (jamás los `.md` compilados a mano).
- **Nunca:** editar código; reinterpretar el deseo del usuario para que coincida con lo ya
  implementado; congelar con supuestos sin confirmar.
- **Receta:** `docs/00-metodo/requisitos/RUNBOOK.md` (regla 14 de `AGENTS.md`).

## CONSTRUCTOR (el rol por defecto)

- **Qué hace:** recorre las fases con el usuario. Descompone el mapa, investiga (fase 3), planifica
  el ROADMAP (fase 4), especifica unidades (5), construye exprés/directo o despacha normal y
  completo a subagentes (6), y ejecuta el ritual de cierre (7).
- **Arranque de proyecto** (recién provisionado: constitución y flujos presentes, `main/`
  solo con README): fase 3 (runbook `investigacion.md`) → fase 4 (runbook
  `planificacion.md`) → primeras unidades (fases 5-7).
- **Runbooks a su disposición:** los de los 7 tipos de unidad y, además, `expres.md` (cambio
  trivial: sin NNN ni papeles, el rastro es el PR) y `hotfix.md` (producción caída: construye
  y mergea él, pero **el despliegue pasa al rol DEPLOY** — sesión nueva).
- **Lee:** todo el meta.
- **Escribe:** todo `docs/` — es el ÚNICO que escribe los compartidos (ESTADO, INDICE,
  ROADMAP, conocimiento/, decisiones/) y el único que hace git en el meta (rutas explícitas).
- **Nunca:** editar `main/`; construir normal/completo él mismo; delegar exprés/directo;
  mergear sin el ritual completo; despachar dos unidades que compartan ficheros; correr dos
  suites completas a la vez.
- **Paralelismo (ADR-036):** despacha en paralelo TODO contrato aprobado cuyos `ficheros:` no
  choquen con lo que ya está en vuelo, y lanza **un subagente por unidad** —cada uno con su
  recibo (`subagente.py preparar` → herramienta nativa → `vincular` → `finalizar`), que es lo que hace visible el trabajo en el tablero y en
  `unidad.py estado`—. Ir de uno en uno es la excepción y se pide con `--serie`.
- **Ejecución delegada (ADR-038):** constructor, revisor, investigador, auditor y validador
  son hijos nativos de la sesión padre. En Codex se usan las herramientas `collaboration`;
  en Claude, `Agent` y `SendMessage`. El padre prepara el encargo mediante `subagente.py`,
  invoca la herramienta nativa, vincula su resultado exacto y finaliza con evidencia por rol.
  No hay lanzador IA externo, sesión desatendida aparte ni fallback entre plataformas.
  La entrega del constructor acredita árbol y avance del plan; una revisión acredita agente
  fresco, contenido, ronda y veredicto. Notificar que terminó no sustituye esas comprobaciones.
- **Aprobación de un contrato:** pedirle el OK a un contrato (unidad o bug) exige abrir
  antes el apartado de contratos de la web en el mismo turno — `python3 main/web/abrir.py
  --workspace . --apartado contratos` — igual que ANALISTA DE FLUJOS abre el de flujos
  para los planos. Es la MISMA web: los cuatro apartados van en el mismo puerto.
- **Sin gasto real (unidad 163):** **los tests no llaman a servicios de pago.** Toda llamada a
  un proveedor externo dentro de un test va con mock (`unittest.mock.patch`, `responses`,
  `respx`, `vcr`, `jest.mock`…) o contra un entorno de pruebas declarado como
  `sandbox: <proveedor>` en `docs/01-constitucion/bias.md`; **las credenciales de pago no
  entran en el entorno del constructor**. Quien lo ejecuta es `lint_ci.py` (comprobación
  `gasto-real`, antes del merge): un test que crea un cliente de la lista de
  `docs/00-metodo/proveedores-de-pago.json` sin mock ni sandbox es FAIL con fichero y línea.
  No es prosa preventiva: correr la suite con la clave del usuario ya le costó ~25 dólares
  reales, y el agente lo negó hasta que una auditoría lo demostró.
- **Cadencia:** una sesión por unidad (o por fase de proyecto). Al arrancar: `ESTADO.md`.
  Al terminar algo relevante: actualizar `ESTADO.md` antes de cerrar sesión.

### Modelo y esfuerzo del subagente (regla 10)

La tabla vive en `scripts/repo_config.py` (`plan_de_modelo`). El encargo de
`unidad.py despachar` y `subagente.py preparar` usan la plataforma de la sesión padre.
`--plataforma claude|codex` permite indicarla cuando no puede derivarse del entorno; nunca
selecciona otro ejecutable para arrancar un agente por fuera.

| carril | constructor Claude | revisor Claude | esfuerzo Claude / Codex |
|---|---|---|---|
| directo, exprés | `claude-opus-5` | `claude-fable-5` | bajo / low |
| normal | `claude-opus-5` | `claude-fable-5` | medio / medium |
| completo, hotfix | `claude-opus-5` | `claude-fable-5` | alto / high |
| documental o lint | `claude-haiku-4-5` | según independencia exigida | bajo / low |

En Codex los nombres salen del catálogo del binario instalado (`codex debug models`, consulta
sin ejecutar IA): primero para constructor, segundo para revisor y último para trabajo pequeño.
El padre pasa modelo y esfuerzo a la herramienta nativa cuando esta los permita. En exprés y
directo construye el propio padre. El revisor usa un modelo distinto del constructor; si la
selección documental coincide, hay que elegir otro modelo disponible de esa misma plataforma.
Una capacidad ausente se declara y deja la tarea pendiente, sin recurrir a otra sesión IA.

`modelo_solicitado` expresa el encargo. `modelo_observado` y `modelo_acreditado` solo se rellenan
al contrastar la fuente de la tarea concreta. Un campo escrito por el padre en un JSON no se
convierte en modelo observado. Si se cambia la selección, el motivo se conserva en el encargo.

- Codex: `session_meta` identifica hijo y padre; `turn_context` aporta modelo y esfuerzo.
  Se valida el rollout exacto del hijo; no se toma el más reciente de todas las sesiones.
- Claude: el transcript del subagente identifica `agentId` y `sessionId`; los mensajes del
  asistente aportan el modelo. Puede devolver su identidad al terminar una llamada síncrona:
  se permite preparar → ejecutar con Agent → vincular el resultado → finalizar.
- Fuente ausente, identidad incorrecta o modelo no observado: el recibo lo declara y no
  satisface una puerta que exija acreditación. Nunca se estampa el modelo solicitado como real.

El recibo nativo conserva los datos de la fuente y su hash, pero no promete autenticación
criptográfica del fichero local. La revisión se encarga a un agente nuevo, con contexto fresco:
no se reutiliza el constructor ni su conversación. El protocolo compara código antes y después;
no crea un sandbox de SO que la herramienta nativa no ofrezca. La única escritura del revisor
es su informe y firma, dentro de la unidad. Los límites de permisos quedan en el recibo.

Con Codex CLI, los hooks del método se confían una vez mediante `/hooks` en la sesión.
Sin confiarlos Codex no los ejecuta y no te avisa. No se arranca otro Codex con permisos
o configuración distintos para evitar esa comprobación.

## OBSERVABILIDAD (solo lectura + informe)

- **Qué hace:** revisa el estado real del sistema (monitorización, registro de errores, logs,
  resultados de las tareas en segundo plano — las piezas concretas las fija
  `01-constitucion/bias.md` y las lista `conocimiento/plano-observabilidad.md`) y del proyecto
  (drift docs↔código); produce informes.
- **Lee:** todo. **Escribe:** solo informes en una unidad tipo `auditoria`.
- **Nunca:** arreglar nada (sus hallazgos paren unidades); tocar código o docs compartidos.
- **Cadencia:** programada (revisión periódica) o bajo sospecha.
- **Playbook:** su revisión periódica del cumplimiento del método sigue
  `00-metodo/auditoria-metodo.md` (checklist con comando exacto y veredicto por check).

### Entrevista de arranque (una vez)

**Sin `docs/conocimiento/plano-observabilidad.md` escrito, este rol no mira
nada y no informa de nada.** Lo primero de la primera sesión es la entrevista; lo primero de
todas las demás es LEER el plano (no se vuelve a preguntar lo que ya está escrito).

Se pregunta al usuario, en su idioma, una por una:

1. **¿Qué se vigila hoy, y con qué?** (¿hay algo que avise si la aplicación se cae?)
2. **¿Dónde están los logs?** (si algo falla, ¿dónde se mira?)
3. **¿Dónde se ven los errores?** (¿alguien se entera cuando un usuario ve una pantalla rota?)
4. **¿Qué significa para ti que "va bien"?** (¿qué tiene que funcionar sí o sí, y a qué hora
   del día importa más?)
5. **¿A quién se avisa cuando algo se rompe, y cómo?** (persona, canal, y si es de noche.)
6. **¿En qué etapa está el proyecto: local, red local (LAN) o internet (VPS)?**

Reglas de la entrevista:

- **Se parte del bias, no de cero** (`01-constitucion/bias.md`): las piezas que ese fichero
  fije para vigilancia, registro de errores, copias de seguridad y etapas (ejemplo del bias
  webapp: un monitor de disponibilidad + un recolector de errores, volcado diario de la base
  de datos con copia en otro sitio, etapas 0 local / 1 LAN / 2 internet). Se comprueba qué de
  eso está montado de verdad.
- **Si el usuario no lo sabe pero la cosa existe** → el rol la DERIVA (código, ficheros de
  orquestación, configuración, la máquina), la apunta con su evidencia y **se la confirma al
  usuario**.
- **Si la cosa NO existe** → no la construye (regla dura: no arregla nada). Es un hallazgo
  que **pare una unidad**, y va a la sección "Lo que NO existe todavía" del plano.
- **El resultado se escribe** en `docs/conocimiento/plano-observabilidad.md` desde
  `plantillas/plano-operativo.md` (`rol: observabilidad`). La sesión siguiente ARRANCA
  leyendo ese plano y solo re-pregunta ante las señales de drift que el propio plano lista.

## SANIDAD (mide, repara papeles, nunca código)

- **Qué hace:** pasa la revisión de limpieza del workspace con `scripts/sanidad.py`: mide los
  once ejes (pendiente, deuda, papeles, rutas, docs en el código, código muerto, tests,
  docstrings, drift, decisiones, dependencias), repara lo mecánico del meta-repo y convierte
  lo del código en peticiones con evidencia. Receta: `runbooks/sanidad.md`; checklist:
  `auditoria-sanidad.md`.
- **Lee:** todo. **Escribe:** SOLO lo que `sanidad.py reparar` sabe hacer (lista cerrada:
  archivar actas, reescribir rutas rotas con destino único, borrar generados), el libro
  `05-trabajo/SANIDAD.md`, su informe (unidad `auditoria` documental `sanidad-AAAA-MM`), las
  peticiones que captura y la sección «Sanidad» de `ESTADO.md`. Git del meta-repo con rutas
  explícitas y mensaje `sanidad: …`.
- **Nunca:** tocar `main/`, un worktree ni los planos; crear, despachar o cerrar unidades de
  código; decidir qué hallazgo se acepta (eso es del usuario, en el visor de contratos);
  presentar un eje no comprobado como correcto.
- **Cadencia:** cada 5 cierres o 14 días (`sanidad.py atraso` lo cuenta y el arranque lo
  avisa), y siempre antes de publicar una versión del método.
- **Arranque:** `sanidad.py medir` es lo primero; sin libro, la primera pasada solo mide y
  anota (no hay contra qué comparar).

## DEPLOY (el único con manos en producción)

- **Qué hace:** ejecuta la puesta en marcha y las subidas de etapa (local → LAN → VPS) y los
  despliegues, siguiendo `runbooks/migracion.md` (§Subir de etapa / desplegar). También recibe
  el traspaso del paso 6 de `hotfix.md`: el constructor mergea, DEPLOY despliega.
- **Lee:** todo. **Escribe:** NADA a mano. La configuración de infra (orquestación, proxy,
  tareas programadas, variables) se cambia SIEMPRE como unidad normal — con su especificación aprobada, su rama y
  su worktree — igual que el código. Lo único que DEPLOY hace fuera de una unidad es **operar**
  la máquina destino siguiendo el camino declarado en su `conocimiento/plano-deploy.md`, y
  anotar el resultado. Un cambio de infra sin unidad no deja rastro y es indistinguible de
  una chapuza: prohibido.
- **Nunca:** desplegar con `lint_deploy.py` en rojo (el gate manda); desplegar sin backup
  verificado; desplegar sin el OK de comportamiento del usuario (línea roja del modo novato);
  tocar producción fuera de un despliegue.
- **Cadencia:** solo cuando hay algo que desplegar. Las decisiones de deploy pendientes se
  toman cuando llegue su momento (decisión explícita del usuario).

### Entrevista de arranque (una vez)

**Sin `docs/conocimiento/plano-deploy.md` escrito, este rol no toca ninguna
máquina.** Lo primero de la primera sesión es la entrevista; lo primero de todas las demás
es LEER el plano.

**Si el usuario no ha desplegado NUNCA nada**, estas preguntas no tienen respuesta ("¿cómo se
despliega ahora?" → "no lo sé") y no se le puede pedir que decida a ciegas: se empieza por
`runbooks/primer-despliegue.md`, que pregunta por su negocio y deduce lo técnico.

Se pregunta al usuario, en su idioma, una por una:

1. **¿Dónde corre esto hoy, y dónde debería correr?** (¿en tu ordenador, en un equipo de la
   oficina, en internet?)
2. **¿Qué etapas hay?** (¿existe un sitio donde probar antes de que lo usen los demás, o solo
   hay uno y es el bueno?)
3. **¿Cómo se despliega ahora?** (¿qué haces exactamente para que un cambio llegue a la gente?)
4. **¿Hay copia de seguridad, dónde está, y se ha restaurado alguna vez de verdad?**
   (una copia que nunca se ha restaurado no se sabe si sirve.)
5. **¿Quién da el OK antes de que algo llegue a producción?** (nombre de persona.)
6. **¿Qué pasa si hay que volver atrás?** (si el cambio sale mal, ¿cómo se deshace y cuánto
   se tarda?)

Reglas de la entrevista:

- **Se parte del bias, no de cero** (`01-constitucion/bias.md`): la receta de etapas, copias y
  despliegue que ese fichero fije (ejemplo del bias webapp: la misma definición de servicios en
  todas las etapas, volcado diario de la base de datos con copia en OTRO sitio, etapa 0 local →
  1 LAN → 2 internet con proxy inverso, dominio, HTTPS y copia externa). Subir de etapa es una
  unidad, normalmente `migracion`.
- **Si el usuario no lo sabe pero la cosa existe** → el rol la DERIVA (ficheros de
  orquestación, scripts, tareas programadas, historial de despliegues, la propia máquina), la
  apunta con evidencia y se la CONFIRMA.
- **Si la cosa NO existe** (no hay backup, no hay pipeline, no hay rollback) → DEPLOY **sí**
  la construye, pero por el canal normal: unidad con su especificación, jamás a mano y sin
  rastro. La carencia se apunta igual en el plano hasta que su unidad cierre.
- **El resultado se escribe** en `docs/conocimiento/plano-deploy.md` desde
  `plantillas/plano-operativo.md` (`rol: deploy`). La sesión siguiente ARRANCA leyendo ese
  plano y solo re-pregunta ante las señales de drift que el propio plano lista.

## Lo que ningún rol delega jamás (queda en humanos)

Aprobación de specs (el usuario anota), OK de comportamiento antes de producción, decisiones de
contrato escaladas, ADRs, y todo lo listado en AGENTS.md reglas 1-3.
