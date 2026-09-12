# Runbook · CONTROL PLANE DE TEST Y EVIDENCIA

**Cuándo:** una prueba crea/muta datos, arranca un preview, construye una imagen o presenta output
como evidencia de un target. **Autoridad:** ADR-024 y `scripts/control_plane.py`.

## Orden obligatorio: identidad → guard → conexión

1. Deriva una identidad con valores estables del repositorio, unidad y run. No uses PID ni hora si
   necesitas reanudar el mismo run después de SIGKILL.
2. Usa sus derivados para DB, puerto, nombre/tag Docker, temporal y log. Nunca uses `latest`.
3. Construye el entorno del target y ejecuta `assert_safe_test_target` antes de crear pool, cliente,
   socket o migración. La única forma segura de envolver una API es `connect_if_safe(callback, env)`:
   ante un target rojo el callback queda sin invocar.
4. Tras arrancar un preview, consulta su endpoint de identidad y pasa el JSON a
   `identity.assert_preview_identity`. HTTP 200 por sí solo no identifica nada.

Ejemplo importable:

```python
from control_plane import RunIdentity, connect_if_safe

identity = RunIdentity("facturacion", "042-recalculo", "ci-17")
env = {"APP_ENV": "test", "DB_HOST": "localhost", "DB_NAME": identity.database()}
connection, target = connect_if_safe(connect_database, env,
                                     expected_namespace=identity.namespace)
```

Un host E2E remoto requiere `allow_hosts={"e2e.internal"}` exacto aportado por el operador o por
la configuración protegida del CI. El manifiesto no puede autorizar su propio host: `allow_hosts`
dentro de un target es inválido. Esa allowlist externa tampoco autoriza un entorno o nombre
productivos. Los errores y la caja negra redactan de forma estructural cabeceras de autenticación,
cookies, DSN, URL con `userinfo` y valores secretos incluso entre comillas; aun así, nunca pegues
`.env` ni manifiestos con contraseñas en `hallazgos.md`.

## Manifiesto CI

`scripts/ci/control-plane.json` contiene solo identidad, targets declarados y las rutas de los
artefactos de control:

```json
{
  "version": 1,
  "identity": {
    "repo": "facturacion", "unit": "042-recalculo", "run": "ci-17",
    "namespace": "<salida de identity>", "fingerprint": "<salida de identity>"
  },
  "targets": [{
    "env": "test", "host": "localhost", "database": "<database derivada>",
    "fingerprint": "<salida exacta de guard-test para este target>"
  }],
  "guard_script": "scripts/ci/control-plane-guard",
  "receipt": ".runtime/control-plane-receipt.json"
}
```

Genera la identidad con `python3 docs/00-metodo/scripts/control_plane.py identity ...`; genera la
huella del target ejecutando `guard-test` sobre el JSON de entorno. `lint_ci.py` vuelve a derivar
ambas: una huella escrita a mano o copiada de otro destino bloquea. El wrapper ejecutable
`scripts/ci/control-plane-guard` solo invoca ese guard canónico y `scripts/ci/provision-e2e` debe
invocarlo como primera orden sustantiva, con fail-fast activo, antes de provisionar o conectar.

Valida un target local con:

`python3 docs/00-metodo/scripts/lint_ci.py --repo worktrees/NNN --require-control-plane`

Para un host remoto autorizado desde configuración protegida, no edites el manifiesto; pasa la
confianza desde fuera:

`python3 docs/00-metodo/scripts/lint_ci.py --repo worktrees/NNN --require-control-plane --control-plane-allow-host e2e.internal`

## Evidencia causal

La evidencia de una corrección determinista se conserva como recibo JSON. Registra `version: 1`,
`claim`, `target_fingerprint`, `route`, `test_scope`, las métricas de presupuesto y exactamente
tres `runs`: versión antigua falla, versión nueva pasa y mutante deliberado falla. Cada run incluye
`phase`, la misma huella, `passed` booleano real, `command`, `exit_code` y el SHA-256 del output.
Una cadena como `"false"`, un comando ausente, un exit code contradictorio, otra huella o un scope
menor bloquean.

El manifiesto CI consume el recibo indicado por `receipt`. Para ligar además el cierre mecánico,
la ficha declara:

```yaml
control_plane: requerido
target_fingerprint: <huella esperada>
```

y se cierra con
`unidad.py cerrar NNN-slug --recibo-control-plane .runtime/control-plane-receipt.json`.
El script compara ruta, scope, target, causalidad y presupuesto con la política real de la unidad;
no basta con que el recibo se describa a sí mismo como válido.

No se mutan producción, servicios remotos ni datos compartidos para fabricar la contrapueba. El
mutante es una fixture local o una inversión controlada en un proceso efímero.

## Gates y presupuesto

| Ruta | Gates terminales | Pruebas | Primer artefacto | Cierre método | Overhead |
|---|---|---|---:|---:|---:|
| documental | revisión; sin merge/app | validación doc | 30 s | 2 min | 25% |
| prototipo | cancelación explícita; nunca cierre/entrega | smoke local | 5 min | 10 min | 20% |
| exprés | aviso + evidencia; sin OK de app | área | 30 s | 2 min | 20% |
| directo | merge + revisión + OK app | área | 5 min | 15 min | 20% |
| normal | merge + revisión + OK app | área + full | 15 min | 30 min | 25% |

Los límites no convierten un trabajo correcto en incorrecto: disparan una anotación y una decisión
de simplificar/escalar. Seguridad, pérdida de datos, permisos y dinero siempre usan el gate más
fuerte que exija el riesgo.

Un prototipo no pasa por `unidad.py cerrar`: aunque declare descarte, el comando se niega a
archivarlo o reconciliarlo como entrega. Se conserva la ficha en estado `descartada` y se cancela
cada proceso con `peticion.py marcar-proceso P-ID --proceso unidad:NNN-slug --estado cancelado`.

## Delegar dentro de la sesión (ADR-038)

El protocolo es el mismo para `constructor`, `revisor`, `investigador`, `auditor` y
`validador`. Los scripts registran evidencia, nunca arrancan otra IA. Sustituye NNN-slug,
RECIBO y AGENTE por los valores reales de la unidad, la preparación y la herramienta.

```sh
python3 docs/00-metodo/scripts/subagente.py preparar NNN-slug --rol revisor
python3 docs/00-metodo/scripts/subagente.py vincular NNN-slug --rol revisor --recibo-id RECIBO --native-task-id AGENTE --evidencia .runtime/resultado-nativo.json
python3 docs/00-metodo/scripts/subagente.py finalizar NNN-slug --rol revisor --recibo-id RECIBO --native-task-id AGENTE --resultado ok
```

Entre preparar y vincular, el padre invoca la herramienta nativa de su sesión: en Codex,
`collaboration.spawn_agent`; en Claude, `Agent`. Puede comunicarse con el hijo y detenerlo
mediante las herramientas de la misma sesión. La preparación entrega modelo/esfuerzo; si la
plataforma no puede derivarse, se indica `--plataforma codex` o `--plataforma claude`.
Para usar la herramienta desde otra copia local durante una migración existe la opción global
`--workspace RUTA`, antes del subcomando. No cambia el origen de la sesión IA.

La evidencia conserva el resultado de la herramienta y referencia metadatos de ese hijo:

```json
{
  "tool": "collaboration.spawn_agent",
  "native_task_id": "/root/revisor_de_la_unidad",
  "parent_session_id": "identidad-real-del-padre",
  "contexto": "fresco",
  "metadata_path": "ruta-al-rollout-exacto-del-hijo"
}
```

En Claude `tool` es `Agent`, `native_task_id` es su agentId y metadata_path apunta a su
transcript. Una llamada síncrona puede devolver el ID al terminar: el recibo queda preparado
hasta vincular ese resultado, sin fingir que preparación equivale a ejecución. Los metadatos
validan hijo, padre y modelo; un modelo escrito en este JSON no se considera observado.
La revisión nunca usa un hijo reutilizado ni el contexto del constructor. El informe conserva
veredicto y firma; el protocolo mide contenido y ronda, sin pedir commits de constructor a un
revisor. Las rutas de evidencias quedan en .runtime/, y las conversaciones o secretos no se
copian al informe público.

`subagente.py estado NNN-slug` muestra preparaciones, tareas vinculadas y resultados, incluidos
los recibos históricos. Solo se finaliza el recibo indicado y con la identidad y rol correctos.
Repetir la misma finalización no cambia su resultado; una preparación vacía no reemplaza una
entrega acreditada.

## Interrupción y recuperación

Primero se comprueba el estado del hijo con la herramienta nativa. Para parar una tarea viva,
el padre la interrumpe allí y finaliza su recibo con `--resultado cancelado --motivo ...` y
los mismos IDs. El script no mata procesos por PID ni convierte una interrupción en entrega.
Los cerrojos se liberan solo cuando coinciden dueño y fencing; no se borra el de otro agente.

Una preparación sin hijo se cancela con
`subagente.py cancelar NNN-slug --recibo-id RECIBO --rol ROL --motivo ...`.
No exige inventar un ID nativo para un agente que todavía no existe.

Si el padre desaparece, se conserva el recibo incompleto. Para el protocolo nativo existe
`subagente.py recuperar NNN-slug --recibo-id RECIBO --rol ROL --motivo ...`:
comprueba que el proceso del padre ya no esté vivo y libera únicamente los registros de
cerrojo exactos, con su fencing. Deja el intento fallido; no afirma que el hijo haya parado.
Consultar y detener ese hijo sigue correspondiendo a la herramienta nativa. Si el dueño sigue
vivo, se explica el límite y no se le quita el cerrojo.

`lease.py desbloquear NNN-slug` se conserva para ejecuciones históricas; puede limpiar un
proceso legado que estuviera registrado, nunca lanzar otro. Recuperar no acredita éxito:
se reanuda con una preparación nueva y se conserva el motivo y referencia al intento anterior.
Una firma ausente se obtiene con otra revisión fresca, no se reconstruye de memoria.

## Suites de este método

Viven en la herramienta de ingeniería de requisitos (el repositorio que montó este workspace),
no aquí: `visor/tests/run-fast` (rápida) y `visor/tests/run-nightly` (nocturna/adversarial).
Ambas son herméticas. La nocturna recorre fixtures legacy→new→mutant, matrices de DSN y dos árboles
concurrentes sin abrir red, Docker ni bases reales. Desde un workspace no hay nada que ejecutar:
estos scripts se prueban en origen y llegan ya probados con cada actualización del método.
