# Frontera de la delegación nativa

Desde ADR-038, toda tarea delegada corre como hijo de la sesión padre: constructor,
revisor, investigador, auditor y validador, tanto en Claude como en Codex. El padre usa las
herramientas nativas para crear, observar, conversar y detener al hijo. `subagente.py`
registra el encargo y la evidencia; nunca ejecuta IA. Los lanzamientos de `ejecucion.py`
están retirados, incluida la antigua vía opcional del constructor.

## Flujo

1. Captura y evalúa la petición; crea y despacha la unidad por sus scripts.
2. Prepara el recibo con `subagente.py preparar NNN-slug --rol constructor` (o el rol de
   la tarea). Se deriva la plataforma de la sesión; si falta, indica `--plataforma`.
3. Usa `collaboration.spawn_agent` en Codex o `Agent` en Claude, con el worktree, encargo,
   modelo y esfuerzo preparados. Para revisión usa contexto fresco y un agente distinto.
4. Conserva el resultado nativo y su fuente; vincula el ID real mediante `subagente.py
   vincular`. Un ID de cerrojo no sustituye la identidad del agente.
5. Finaliza ese recibo exacto mediante `subagente.py finalizar`, después de comprobar la
   terminación del hijo. El constructor aporta trabajo y plan; los roles de lectura,
   informe y evidencia de que el contenido no cambió. Receta: `runbooks/control-plane.md`.

## Permisos y límites observables

El método respeta los permisos que ofrece la sesión nativa. El encargo fija la frontera de
escritura y el protocolo registra snapshots de código y documentos antes y después. No se
promete aislamiento de sistema operativo cuando la herramienta no lo expone, ni se copian
credenciales a otro HOME para conseguirlo. El código del revisor es de solo lectura; su única
escritura permitida es el informe y la firma de su unidad.

Los snapshots detectan diferencias observables al finalizar, no prueban que nunca existiera
una escritura transitoria luego revertida. El modelo solicitado tampoco demuestra el modelo
real: se contrasta con la fuente de la tarea concreta. Los metadatos locales aportan evidencia,
no autenticación criptográfica. Estos límites quedan escritos en el recibo.

Si falta una capacidad necesaria, se conserva la tarea pendiente y se explica cómo continuar
en una sesión compatible. No se inicia `claude -p`, `codex exec`, otro proceso IA ni una
sesión independiente como salida alternativa. Git, intérpretes, tests y herramientas ordinarias
siguen siendo procesos locales del trabajo; no son agentes delegados.
