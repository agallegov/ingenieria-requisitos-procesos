# ADR-038 · Toda delegación dentro de la sesión

- Estado: aceptada; alcance aprobado por el usuario en el contrato 165 el 2026-09-12.
- Origen: P-20260912-c5261643; unidad 165-delegacion-nativa-en-la-sesion.
- Sustituye el mecanismo de lanzamiento externo de ADR-022, la excepción del revisor y la vía opcional de ADR-033, y los perfiles externos de ADR-037. Conserva revisión independiente, evidencia, identidad de contenido y paridad de plataformas.

## Contexto

El constructor ya podía ser un hijo nativo del padre, pero el revisor y otras vías de
construcción seguían usando otro proceso IA. El usuario ha pedido que todos los agentes,
en todas las plataformas, formen parte de la sesión que los coordina. Además, el registro
previo cerraba por unidad sin vincular siempre el recibo al hijo real y aplicaba reglas de
constructor a la revisión.

## Decisión

1. Constructores, revisores, investigadores, auditores y validadores son hijos nativos del
   padre. Claude usa Agent/SendMessage y Codex sus herramientas collaboration. La regla
   también rige para la revisión de esta modificación. Exprés/directo siguen construidos
   por el padre; esta decisión no crea delegación donde el carril no la pide.
2. subagente.py implementa preparar → vincular → finalizar. La preparación no demuestra que
   arrancara un agente. El vínculo conserva el resultado de la herramienta, la identidad real
   del hijo y su padre. Se permite recibir el ID al terminar una llamada síncrona.
3. Se finaliza un recibo exacto, con rol e identidad coincidentes y propiedad vigente del
   cerrojo. Repetir la finalización no cambia el resultado. Interrumpir o recuperar no se
   convierte en entrega. El cierre del constructor mide trabajo/plan; el revisor mide
   contenido/ronda/veredicto y no crea un commit de construcción.
4. El revisor es un agente nuevo con contexto fresco, distinto del constructor y con otro
   modelo de la misma plataforma según la política del método. Ni reutilizar una conversación
   ni abrir otro ejecutable satisface esa independencia.
5. Modelo solicitado y observado se distinguen. La acreditación usa metadatos de la tarea
   concreta: hijo/padre de session_meta y modelo de turn_context en Codex, agentId/sessionId
   y mensajes del asistente en Claude. No se elige el último registro global ni se acredita
   un modelo escrito en el encargo. Una fuente insuficiente conserva esa limitación.
6. Ninguna orden nueva ejecuta claude -p, codex exec ni otro proceso o sesión IA independiente.
   ejecucion.py conserva funciones comunes y compatibilidad de lectura; las órdenes retiradas
   explican la migración. Si la sesión no ofrece una capacidad necesaria, la tarea queda
   pendiente con una salida concreta, sin fallback externo.
7. Recibos históricos siguen siendo legibles. El contenido revisado conserva su identidad a
   través de un rebase equivalente. Una preparación sin resultado no desplaza evidencia válida.

## Límites y consecuencias

El protocolo usa los permisos de la herramienta nativa y comprueba snapshots de código y
documentos. No fabrica un aislamiento de SO que esa herramienta no exponga; tampoco detecta
por sí solo escrituras transitorias revertidas antes del snapshot final. Los metadatos locales
aportan evidencia y consistencia de identidades, no autenticación criptográfica contra su dueño.
Estos límites se declaran en el recibo y no se ocultan con una firma de modelo solicitado.

Git, intérpretes, tests y scripts locales siguen siendo herramientas ordinarias. Esta decisión
prohíbe externalizar agentes IA, no los procesos necesarios para desarrollar o verificar código.
No autoriza despliegues, envío de mensajes ni cambios en otros talleres.

## Verificación y distribución

Pruebas de ciclo por rol, identidad incorrecta, metadatos cruzados, idempotencia, cerrojos,
revisión sin cambios de código, historial, rebase y rechazo de lanzamientos externos. La suite
simula resultados nativos sin llamar a proveedores IA. Se ejecuta además una tarea real nativa
en la plataforma disponible y se distingue de la compatibilidad comprobada mediante fixtures.

AGENTS.md, roles, sandbox, runbooks, ayuda, tablero y plantilla distribuida usan este mismo
mecanismo. visor/bootstrap.py incorpora esta ADR al manifiesto del método.

## Fuentes

Investigación de dos lentes en la petición, con lectura del código base 0a84e076 y fuentes
oficiales consultadas el 2026-09-12: https://learn.chatgpt.com/docs/agent-configuration/subagents
y https://code.claude.com/docs/en/sub-agents . La ejecución nativa de la unidad aporta evidencia
local adicional, con identidad y fuente específica en .runtime/.
