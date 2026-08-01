---
unidad: NNN-slug
revisor: no              # LO ESCRIBE EL PADRE en el cierre: quién hizo la revisión fresca
                         # (sesión/subagente nuevo). El constructor jamás se pone aquí.
revisado: no             # `no` | fecha YYYY-MM-DD de esa revisión. `unidad.py cerrar` la exige.
---

# NNN · Hallazgos del constructor

> Único fichero del meta que el constructor rellena. El padre lo cosecha en el cierre:
> promociones a conocimiento/, ADRs, nuevas unidades, correcciones al método.

## Evidencia de verificación (obligatorio)

```
<output real de la suite de tests + lint. Pegado, no resumido.>
```

<Capturas y volcados si hay UI: van a `.runtime/NNN-slug/` (fuera de git, ya existe) y aquí
se referencian por RUTA, nunca pegados. Lo sensible (credenciales, PII) va a `.private/`.>

## Desviaciones de implementación

<El cómo cambió respecto a lo previsto, sin tocar el contrato. Si hubo desviación de
CONTRATO, esta unidad debió pararse — si estás escribiendo aquí en vez de haber parado,
explica por qué.>

- —

## Descubrimientos (candidatos a conocimiento/)

<Cosas aprendidas que le ahorrarían trabajo al siguiente: trampas de una librería,
comportamientos no documentados, comandos útiles.>

> **Cómo se cosecha esto** (lo hace el PADRE en el cierre, y `unidad.py cerrar` lo exige):
> cada viñeta acaba marcada con `→ promovido a <destino>` o con `→ descartado (motivo)`.
> Puede ir en cualquier punto de la viñeta —también en su última línea, que es donde cae
> natural— y admite negrita. Literalmente así:
>
> - El cliente de X reintenta en silencio: los timeouts hay que mirarlos en sus logs.
>   → promovido a `conocimiento/cliente-x.md`
> - Idea de cachear la home. → descartado (sin medición que lo justifique)

- —

## Trabajo descubierto (candidatos a nuevas unidades)

<Bugs vistos de pasada, deudas, mejoras. NO los arreglaste (fuera de alcance): los apuntas.>

<Los hallazgos que añade el REVISOR en el cierre —no el constructor— empiezan por `[revisor]`.
Es lo que permite, dentro de tres meses, distinguir una revisión de verdad de un constructor
que se puso un sello a sí mismo.>

- —

## Revisión (la rellena el padre en el cierre)

<Paso 2 del ritual de cierre: veredicto del revisor fresco (sesión/subagente nuevo, solo
lectura) sobre el diff contra la especificación. El constructor NO escribe aquí; su nombre y
la fecha van al frontmatter (`revisor:`, `revisado:`) y sin ellos `unidad.py cerrar` bloquea.>

- **Veredicto:** LIMPIO | HUECOS DE CORRECCIÓN
- **Huecos** (si los hay; cada uno vuelve al constructor antes del merge):
  - —
- **Fecha:** YYYY-MM-DD
- **Validación del usuario sobre la app corriendo:** — <la escribe `unidad.py cerrar`>

<FRONTERA DEL REVISOR (regla del método, no preferencia): solo son huecos de corrección los
incumplimientos del contrato de ESTA unidad, los fallos de seguridad y la pérdida de datos.
Un riesgo de un flujo futuro, una mejora o un "esto convendría prepararlo para cuando…" NO
reabre la unidad: se anota arriba como trabajo descubierto y sigue su camino. Solo un fallo
crítico permite una segunda ronda.>
