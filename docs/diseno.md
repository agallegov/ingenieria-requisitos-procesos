# Diseño del método

Para quien mantenga esta herramienta. El alumno no necesita leer esto.

## La idea en una frase

Una persona de negocio no técnica no sabe escribir requisitos, pero sí sabe
contar su negocio: la IA entrevista siguiendo `RUNBOOK.md`, la persona
valida mirando una web que se rellena sola, y el resultado son
especificaciones que otra IA puede construir o auditar sin inventarse nada.

## Fundamentos

Cada pieza es una técnica establecida de la ingeniería de requisitos,
despojada de su liturgia:

- La entrevista por hechos pasados ("cuéntame la última vez que...") es la
  técnica de incidentes críticos: preguntar por funciones produce
  soluciones imaginadas; preguntar por episodios revela el problema.
- Los flujos "hoy" y "con la app" son el as-is/to-be del modelado de
  procesos, dibujados como diagrama de actividades simplificado con una
  novedad: los pasos se tipan por EJECUTOR (persona, código, IA, tercero),
  que es la pregunta de diseño de una app moderna.
- Los requisitos usan la sintaxis EARS (evento, estado, fallo, invariante);
  las pruebas son Specification by Example (Dado/Cuando/Entonces con datos
  reales); las reglas con 3 o más condiciones van en tablas de decisión.
- Las entregas son cortes verticales priorizados, empezando por el
  esqueleto que recorre el camino feliz de punta a punta (walking
  skeleton, story mapping).
- La superficie de uso incluye el requisito negativo ("qué no debe poder
  pasar jamás"), heredero de los misuse cases.
- El conjunto encaja con el Spec-Driven Development: la salida compilada
  (01-constitution + 02-flows) equivale a las fases /constitution y
  /specify de una cadena tipo Spec Kit; el plan y la implementación son
  del agente constructor.

## Decisiones de arquitectura

- **Una única fuente de verdad por plano**: `planos.json`, validado contra
  `visor/esquema.json` con `visor/validar.py` (ids únicos, referencias,
  cobertura). Todo lo demás se genera: el spec (`generar_spec.py`), la
  documentación (`compilar.py`) y la web.
- **La plantilla web está congelada** (`visor/plantilla.html`): ninguna IA
  genera ni edita HTML jamás; solo produce datos. Así la web es idéntica
  para todos los proyectos y alumnos. Paleta validada para daltonismo y
  identidad por triple canal (color, forma y etiqueta escrita).
- **Servidor efímero local** (`servir.py`): solo stdlib, solo 127.0.0.1,
  puerto 8765 estable, se apaga tras 15 minutos de inactividad (cada
  visita resetea el contador).
- **Dos escalas, un esquema**: un proyecto de una actividad usa un plano
  único; en cuanto hay más de una, hay mapa (catálogo por áreas con estado
  y dependencias) y una carpeta `actividades/<id>/` por actividad. La web
  enseña entonces el menú lateral.
- **La herramienta es de solo lectura**: los proyectos viven siempre fuera
  de esta carpeta (regla en AGENTS.md, CLAUDE.md y RUNBOOK.md).

## Descartes deliberados

Notaciones formales (UML/BPMN/DMN como notación), personas y mapas de
empatía, prototipado de pantallas, métodos formales (TLA+, Alloy) y marcos
de proceso de equipo (Scrum, Double Diamond): coste de ceremonia que no
paga a esta escala o que pertenece al lado de la obra. Las user stories en
formato tarjeta se descartaron como especificación: la unidad aquí es la
entrega verificable (requisitos EARS + pruebas con datos reales).

## Abierto

- Fuente tipográfica embebida en la plantilla (hoy Arial del sistema).
- Lanzador de doble clic para Windows sin Python en el PATH.
- Bloque opcional de "principios innegociables" al estilo /constitution
  explícito.
