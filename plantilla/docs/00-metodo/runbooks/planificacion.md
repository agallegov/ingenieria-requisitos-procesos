# Runbook · PLANIFICACIÓN (fase 4 — el padre, debatiendo con el usuario)

**Cuándo:** al terminar la fase 3 (síntesis escrita); después se alimenta en cada cierre,
nunca se re-hace entera.
**Produce:** `04-planificacion/ROADMAP.md` (plantilla `roadmap.md`).
**Contrato de cierre:** cada decisión debatida y aprobada por el usuario + plan de
construcción con el esqueleto andante primero.

## Paso a paso

1. **Cargar y corroborar TODO:** la constitución, TODOS los flujos, TODOS los informes de
   `03-investigacion/`, la `SINTESIS.md` y lo ya aprendido (`docs/decisiones/` y
   `docs/conocimiento/`). Se leen uno a uno; nada se planifica sin haberlos leído. Si algo se
   contradice entre ellos → se resuelve con el usuario antes de seguir.
   (**Los informes y la `SINTESIS.md` los produce la fase 3**, `runbooks/investigacion.md`; aún
   no existen: si faltan, correr la fase 3 es el paso previo y esta fase no arranca. En
   brownfield la fase 3 va acotada — `runbooks/adopcion.md` §6 — pero va.)
2. **Preparar las decisiones.** `<HARD-GATE>` **Antes de proponer tecnología, mirar la
   máquina:** `python docs/00-metodo/scripts/doctor.py --escribir`. **El ROADMAP no fija una
   herramienta que el doctor no haya visto en verde** — si no hay Docker, el plan no dice
   "se desarrolla con contenedores"; si no hay `gh`, el cierre va por el camino B de
   `runbooks/cierre.md` y eso se escribe AQUÍ, no se descubre en el paso del pull request.
   Por cada decisión a tomar (lenguaje, framework, librerías,
   integraciones, dónde corre): una opción recomendada y sus alternativas, con pros y
   contras EN CRISTIANO — cero jerga técnica; si un término técnico es inevitable, se
   explica en una frase. Entre las decisiones SIEMPRE está el **entorno de ejecución y
   testing local**: ¿Docker/compose o directo sin Docker (venv/node)? Criterio: Docker
   cuando hay varios servicios (BD, colas, workers) o cuando importa el aislamiento por
   rama/worktree; directo cuando es un script o automatización simple donde Docker solo
   añade fricción. La complejidad de terminal NO es argumento en contra (la maneja un
   agente).

   **Antes de proponer NADA, mirar qué ya existe.** `<HARD-GATE>` Buscar en el código
   (`main/`) si YA hay un módulo o componente que haga eso o algo parecido: **no se duplica
   código ni responsabilidades**. Si lo hay, la funcionalidad se encaja ahí (refactorizando
   ese módulo si hace falta), JAMÁS levantando un sistema paralelo; solo se propone módulo
   nuevo cuando ninguno existente es su sitio, y se dice a qué capa pertenece. Lo encontrado
   —módulos que se tocan y por qué no se duplica— se escribe en el ROADMAP.

   **Principios innegociables del diseño** (mandan al trocear en unidades y al decidir la
   arquitectura; cada unidad los vuelve a aplicar en su fase 5, `runbooks/feature.md`):
   Single Responsibility · KISS · clean code · encapsular por funcionalidades con capas de
   abstracción · los módulos se comunican entre ellos. **Prioridad nº 1: que el discovery de
   código de los agentes sea lo más barato posible en tokens** — una funcionalidad vive en
   SU módulo, no desperdigada por toda la app.
3. **Debatir con el usuario, ping-pong.** Las decisiones se presentan DE UNA EN UNA:
   "he encontrado esta tecnología, tiene estos pros, estos contras, se haría así".
   El usuario pregunta, el padre responde, y el usuario decide. `<HARD-GATE>` Nada queda
   decidido sin su OK. Una decisión gorda (contradice el bias, elimina algo) → ADR.
4. **Escribir el ROADMAP** con la estructura FIJA de la plantilla, siempre igual:
   ① resumen al principio (qué se construye y con qué, para leer en 30 segundos) ·
   ② los motivos de cada decisión (por qué sí, por qué no las otras) ·
   ③ tabla comparativa al final de las decisiones ·
   ④ plan de construcción: esqueleto andante primero (la cadena mínima que atraviesa el
   sistema punta a punta), los **módulos existentes que se tocan y por qué no se duplica**
   (paso 2), y la tanda actual troceada en unidades con orden y dependencias.
5. `<HARD-GATE>` **El usuario aprueba el documento final.** Actualizar `ESTADO.md` →
   fase 5: especificar y despachar la primera unidad de la tanda (runbook de su tipo).

## El bias de la planificación (fijo; se aplica a TODA decisión)

- **Quien decide no es técnico** y no tiene background fuerte de programación → todo se le
  explica en cristiano. PERO la elección técnica NO se rebaja por eso: la terminal y la
  implementación compleja las hace un agente, así que la dificultad de instalación no es
  argumento. PROHIBIDO proponer un SaaS o un ecosistema cerrado "porque es más fácil para
  un no técnico" (ejemplo: PostgreSQL sí; Supabase no).
- **Cero overengineering:** lo más sencillo que cumpla, rápido de implementar y que aguante
  en el tiempo.
- **Sin SaaS. Tecnología libre y ecosistemas abiertos SIEMPRE** (máximas libertades).
- **Destino por defecto: un VPS propio** (self-hosted).

## Reglas fijas

1. **Barrio Sésamo:** todo el documento entendible por alguien sin jerga técnica. Resumen
   SIEMPRE al principio; explicaciones mínimas; comparativa en tabla.
2. **El ROADMAP no asigna NNN.** El número se asigna al DESPACHAR (fase 5, desde main).
   Al abrir la unidad, su fila apunta al `NNN-slug`; al cerrarla, pasa a "Entregado".
3. **Solo el padre lo escribe, en fronteras:** cada cierre añade el trabajo descubierto y
   los hallazgos de auditoría aceptados; reordenar exige OK del usuario.
4. **Planificar poco y cerca:** detalle solo para la tanda actual; lo lejano, una línea.
5. **No duplica estado:** el estado vivo está en `ESTADO.md` y en los frontmatters.
6. **El entorno decidido se materializa en el AGENTS.md del repo de código**, con los
   comandos exactos y copiables: levantar el entorno, correr la suite completa, correr los
   e2e, lanzar una instancia local para que el usuario pruebe y la comprobación de seguridad.
   Sin esos comandos escritos,
   los pasos del método que dicen "suite en verde" o "lanzar instancia" no son ejecutables
   por un agente fresco — esta regla es la que lo garantiza. **No se escribe desde cero: se
   copia `plantillas/agents-repo-codigo.md`**, que ya trae los huecos fijos. (Lo crea la
   primera unidad del esqueleto andante y es lo que los constructores leen como "Contexto".)
