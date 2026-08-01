---
unidad: NNN-slug
tipo: bug
carril: normal
estado: planificada        # planificada (reportado) | en_obra | en_revision | mergeada | bloqueada | descartada
aprobado: no               # LO PONE EL USUARIO, jamás el agente: `no` | fecha YYYY-MM-DD del día
                           # que aprueba el arreglo. Sin fecha, `unidad.py despachar` bloquea.
                           # Única excepción: hotfix P0 (`--force --motivo "..."`, runbook hotfix.md).
actividad: <id del INDICE de flujos>
ficheros: []
actualizado: YYYY-MM-DD
---

# NNN · BUG: <síntoma en una frase>

> Fichero ÚNICO del bug (ADR-006). Vive en `docs/bugs/NNN-slug.md` y acumula TODO su ciclo
> de vida: reporte → reproducción → diagnóstico → propuesta → resolución → cierre.
> Lo escriben el padre (secciones 1, 4-decisión y 6) y el subagente del bug (2, 3, 4-propuesta
> y 5) — es el único fichero de docs/ que ese subagente puede tocar. NO se archiva: la
> carpeta bugs/ es el historial.
> Quien reporta jamás marca un bug como resuelto: solo la implementación verificada puede.
> La evidencia sensible (datos personales, credenciales) vive en `.private/` y se referencia
> por ruta; aquí jamás se copia.
> Prohibido `git stash`: la pila es única y compartida entre TODOS los worktrees — un pop
> puede llevarse trabajo de otra rama.

## 1 · Reporte (el padre, con lo que cuenta el usuario)

- **Qué esperaba el usuario:** <comportamiento prometido; cita el criterio del mapa/spec si existe>
- **Qué pasa de verdad:** <el síntoma, con ejemplo concreto: datos, pasos, resultado>
- **Severidad preliminar:** P0 (producción caída) … P4 (cosmético)
- **Estado de triaje:** Necesita información | Reproducible | Intermitente | Duplicado
- **Fuente:** <quién/cómo llegó>
- **Alcance:** se arregla el defecto y NADA más (refactors y mejoras → otra unidad).

## 2 · Reproducción (el subagente; su PRIMERA misión)

- **Test end-to-end que lo reproduce:** `<ruta del test en el worktree>` — estado: **ROJO**
- **Output del test en rojo:** (pegado, no resumido)
- **Pasos deterministas:** 1. … 2. … 3. Esperado: X · Real: Y
- **Frecuencia e intentos:** <reproducciones positivas Y negativas, con entorno y hora — los
  intentos que NO reproducen también se anotan>

## 3 · Diagnóstico (la causa raíz)

<Qué lo causa de verdad, no el síntoma. Siempre se rellena: es materia prima del conocimiento.>

### Hechos comprobados

<Solo lo demostrado con evidencia (output, logs, capturas).>

### Hipótesis y preguntas abiertas

<Lo no demostrado, marcado como tal. Jamás mezclado con los hechos.>

## 4 · Propuesta de solución (solo si tiene miga; si es directa, saltar a 5)

- **Propuesta:** <qué se haría y por qué, en cristiano>
- **Alternativas descartadas:** —
- **Decisión del usuario (vía el padre):** PENDIENTE | APROBADA (YYYY-MM-DD) | RECHAZADA → <qué se acordó>

## 5 · Resolución (el subagente)

- **Qué se cambió:** <ficheros y qué se hizo>
- **Test del bug:** VERDE — output pegado, sin haber tocado el test
- **Tests de regresión añadidos:** <cuáles y qué comportamiento fijan para que NO vuelva> —
  comprobados en ROJO sin el arreglo y en VERDE con él (un test que pasa en los dos casos no vale)
- **Suite completa:** VERDE — output pegado
- **Pull request:** <rama `NNN-slug` → main; título con NNN-slug>

### Plan de trabajo del subagente (esqueleto fijo; marcar `[x]` al completar)

- [ ] 1. Test que reproduce el bug, en ROJO (sección 2) · _Depende de: —_
- [ ] 2. Causa raíz diagnosticada y escrita (sección 3) · _Depende de: 1_
- [ ] 3. Arreglo implementado: el test del bug en VERDE sin haberlo tocado · _Depende de: 2_
- [ ] 4. Tests de regresión contraprobados (rojo sin el arreglo, verde con él) · _Depende de: 3_
- [ ] 5. Suite completa + lint en verde; evidencia pegada arriba · _Depende de: 4_
- [ ] 6. Commit y push de la rama `NNN-slug` · _Depende de: 5_
- [ ] 7. Abrir el **pull request** contra la rama principal, con `NNN-slug` en el título y enlace a esta ficha · _Depende de: 6_
- [ ] 8. **PARAR.** La rama queda PENDIENTE DE APROBACIÓN (estado → `en_revision`). Devuelve el control al padre con el enlace del PR y la evidencia. · _Depende de: 7_

### Reglas del constructor (fijas)

- Escribes SOLO en tu worktree y en esta ficha. El resto de la documentación se lee, jamás se toca.
- Si tu trabajo va a contradecir el mapa o el alcance del bug → **PARA y devuelve la tarea**.
- **No mergeas tú. Tu trabajo termina en el pull request abierto.** El merge, la suite
  end-to-end sobre main y el lanzamiento de la instancia para que el usuario valide los hace
  el padre, a petición del usuario. Ni `git merge`, ni `gh pr merge`, ni push a la principal.
- Los tests escritos no se debilitan ni se borran. Arreglas el defecto y NADA más.
- Nada está "hecho" sin el output del check en verde. Evidencia, no afirmación.

## 6 · Cierre (el padre, a petición del usuario)

- **Revisión (revisor fresco, ANTES del merge):** LIMPIO | HUECOS DE CORRECCIÓN → <cuáles;
  cada uno vuelve al subagente antes del merge> · Fecha: YYYY-MM-DD
- Merge del PR: — · Suite end-to-end completa tras el merge: — · Instancia lanzada: —
- **Validación del usuario:** PENDIENTE | OK (YYYY-MM-DD) | REABIERTO → <por qué; vuelta a la sección 2>
