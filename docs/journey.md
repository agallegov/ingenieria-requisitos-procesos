# Journey completo del método "de la idea al spec"

Borrador v2 (22-jul-2026). Documento de diseño del workflow: se itera aquí y
después se baja a la skill y al prompt maestro. No es material de alumno.
La v2 incorpora la reestructuración de Nate (multi-flujo, superficie de uso,
visor local) y queda pendiente de contrastar con las fuentes que va a traer
antes de reescribir las fases de la SKILL.md.

## Principios que gobiernan todo el flujo

1. La claridad la trae el humano; la IA estructura, cuestiona, expande y
   patrulla los bordes.
2. El esqueleto es el flujo del negocio, no las tarjetas. Las unidades de
   trabajo se derivan del flujo al final; nunca se elicitan sueltas.
3. Los spec files son la única fuente de verdad y el único canal entre
   agentes: la IA analista y la IA constructora/auditora no se hablan, se
   escriben a través de los specs.
4. El usuario valida leyendo, mirando el visor y usando; nunca redacta.
5. Un solo método de elicitación para todos los destinos: lo que se bifurca
   es el encargo (construir, auditar), no la conversación.
6. Plantilla y contenido separados SIEMPRE: lo visual y lo estructural están
   congelados y viajan con la skill; con el usuario solo se generan datos
   (JSON) y texto de negocio.

## La arquitectura del visor (decidido y construido, 22-jul)

- `visor/plantilla.html`: página fija, autocontenida, sin dependencias ni
  red. No se genera ni se toca: misma fuente, mismo fondo, mismos bloques en
  cualquier ordenador.
- `visor/esquema.json`: JSON Schema del formato de datos. Lo que se produce
  con el usuario es SOLO `proceso.json` (varios flujos, actores, pasos
  tipados humano/estatico/ia, decisiones regla/excepción con rama que vuelve).
- `visor/servir.py`: servidor efímero, solo stdlib de Python, solo
  127.0.0.1, puerto libre automático, abre el navegador y muere solo a los
  15 minutos. Relee los datos en cada recarga (editar json + F5 basta). Para
  volver a verlo, se relanza.
- Verificado end-to-end el 22-jul: URL inmediata, plantilla y datos servidos,
  404 fuera de ruta, autoapagado comprobado.

## Actores y canales

- **Usuario de negocio**: cuenta hechos, corrige mirando el visor, prioriza,
  decide qué borde no importa. Nunca escribe requisitos.
- **IA analista** (la skill): entrevista, mantiene los flujos y los specs,
  genera `proceso.json`, levanta el visor, redacta el encargo. Única IA que
  habla con el usuario sobre el "qué".
- **IA constructora** (sesión aparte): recibe spec files + encargo de
  construcción. Decide el "cómo". Sus dudas van a "Preguntas abiertas" del
  spec; el analista las resuelve con el usuario; nunca de palabra.
- **IA auditora** (sesión aparte): recibe spec files + encargo de auditoría +
  código. Corrobora specs contra código y produce desviaciones en lenguaje
  de negocio.
- **Formador** (meta-actor): fija expectativas antes de la sesión.

## Puertas de entrada (triaje del primer turno)

Una pregunta como mucho, si el contexto no lo dice ya: "¿Qué traes: una idea
para construir de cero, un código que ya existe y quieres entender o auditar,
o cambios sobre un spec que ya hicimos?"

- **Modo A, proyecto de cero**: journey completo.
- **Modo B, código existente**: misma elicitación SIN mirar el código (el
  código ancla y contamina la entrevista); el encargo final es de auditoría.
- **Modo C, iteración**: protocolo de iteración directo sobre los specs.
- Compuestos: arreglos tras auditoría = C + reconstrucción; feature sobre
  código sin spec = B del tramo afectado + C.

## Las fases de conversación (reestructuración v2, propuesta de Nate)

Sustituye a la numeración 1-7 de la skill cuando la corroboremos con las
fuentes. Cada fase cierra con una validación de lectura o de visor, nunca con
sensación de completitud. Una pregunta por turno, episodios y hechos, nada de
menús de opciones.

**F0. Apertura y triaje.** Contrato conversacional (qué haremos, qué se
espera de él, qué saldrá) + modo A/B/C. Volcado libre y frase de contrato.

**F1. Cartografía de flujos (multi-flujo).** TODOS los flujos de trabajo
actuales, manuales, contados como si no hubiera ordenadores (o con los
mínimos): varios flujos, varios actores, excepciones y reglas pegadas al
paso. Cada flujo entra en `proceso.json` con `momento` "hoy" y se valida en
el visor. Cierra cuando el usuario dice "así pasa de verdad" en todos.

**F2. Interrogatorio de huecos.** La máquina pregunta y pregunta sobre lo
abierto en los flujos: episodios reales ("la última vez que salió mal"),
huecos lógicos, y la red de seguridad de la checklist de olvidos aplicada
por flujo (excepciones, concurrencia, volumen, primer día, estados...).
Ejemplos con datos de verdad en los puntos calientes (2 normales + 1 raro,
tablas de decisión si hay 3+ condiciones combinadas).

**F3. Materia prima y reparto.** Qué formatos y archivos predeterminados
existen (Excel, plantillas, PDFs, correos tipo), qué datos hay y de dónde
vienen, qué se migra o se ignora. Y el reparto: qué se puede automatizar con
código normal, qué con IA, qué se queda en humanos. Los flujos se retipan y
entran en `proceso.json` con `momento` "futuro"; el usuario corrige en el
visor. "Esto lo quiero seguir haciendo yo" es válido; un paso `ia` sin
revisión humana que toque dinero o clientes se señala como riesgo.

**F4. Superficie de uso.** Interfaces, puntos de entrada, permisos y roles.
Súper estándar y súper rígida: una ficha fija por interfaz/punto de entrada
(quién entra, por dónde llega, qué ve, qué puede hacer, qué NO debe poder
pasar nunca) y una matriz roles x acciones. Campos exactos de la ficha:
pendiente de las fuentes de Nate.

**F5. Bajada a spec files.** Se genera la serie completa (ver salida), el
analista señala sus 3 zonas de menor confianza, y el usuario lee buscando
mentiras y huecos. Nada no dicho por el usuario entra como requisito: va a
"Preguntas abiertas".

Mapeo con la skill actual: F0 = fases 1-2; F1 = fase 3 en multi-flujo;
F2 = fases 4-6; F3 = fase 6.5 + checklist 3/7; F4 = checklist 2/6 ampliada
(nueva de verdad); F5 = fase 7.

## La salida: serie de spec files

Carpeta `<slug>/`, todo versionable, legible por una guía humana y
corroborable por un agente:

1. `proceso.json`: los flujos hoy y futuro como datos (fuente del visor y
   estructura maestra para los agentes).
2. `spec.md`: propósito y frase de contrato, requisitos EARS por tramo,
   reglas y tablas de decisión, criterios Dado/Cuando/Entonces con datos
   reales, estados por entidad, datos y su origen, fuera de alcance,
   preguntas abiertas.
3. `superficie.md`: interfaces, puntos de entrada, fichas por rol, matriz de
   permisos. (nuevo en v2)
4. `encargo.md`: el texto para la IA constructora o auditora.
5. `mural.md`: notas de trabajo (registro interno, no viaja al agente).

## Después de la conversación

**Construcción (modo A).** Sesión nueva: encargo + spec files. La
constructora genera su plan, trata los Dado/Cuando/Entonces como tests de
aceptación, y sus dudas van a "Preguntas abiertas" del spec, nunca de
palabra. Lo no especificado: opción más simple y reversible + pregunta
apuntada.

**Auditoría (modo B).** Encargo de auditoría:

> Audita el código contra los spec files. No asumas que el código es
> correcto ni que el spec es completo. Reconstruye el proceso que el código
> implementa en el mismo formato `proceso.json` y busca tres cosas: lo que
> el spec exige y el código no hace, lo que el código hace y el spec no
> pide, y lo que ambos cubren con reglas distintas. Ejecuta los ejemplos
> Dado/Cuando/Entonces contra el código real siempre que puedas. Cada
> desviación se reporta con el ejemplo que la demuestra, en lenguaje de
> negocio. No arregles nada sin encargo aparte.

Salida: `desviaciones.md` + la tercera foto en el visor (hoy / lo que
quería / lo que el código hace).

**Validación por el usuario.** Los ejemplos con datos reales son el guion de
la demo: recorrer la app con ellos y comprobar el resultado prometido.

**Iteración (modo C).** Todo cambio entra por el analista: sección impactada,
preguntas mínimas, actualizar spec y `proceso.json`, relanzar visor, enseñar
solo lo que cambió, reconstruir desde el spec.

## La unidad de trabajo: qué es una "historia" útil para una IA

La tarjeta clásica ("Como X quiero Y para Z") es formato pobre para una IA:
sin disparador, sin datos, sin frontera verificable. Nuestra unidad es un
**recorrido**: un corte vertical del flujo que el usuario puede probar de
principio a fin. Su anatomía sale entera de fases ya hechas:

1. Disparador y respuesta observable (EARS). [F5]
2. Ejemplo ejecutable con datos reales (Dado/Cuando/Entonces). [F2]
3. Posición en el flujo: de qué tramo viene, a cuál va. [F1]
4. Ejecutor de cada paso: humano, estático o ia. [F3]
5. Estados de las entidades que toca. [F2]
6. Superficie: desde qué interfaz, con qué rol y permisos. [F4]

Orden de entrega (propuesto, sección del spec): "si mañana solo existiera un
trozo de la app, ¿cuál te quita más trabajo?"; el usuario ordena por valor,
el analista ajusta por dependencias, la constructora construye en ese orden.

## Resueltas con el barrido bibliográfico (22-jul, encuesta de ingeniería de requisitos)

- Tarjetas de user story: descartadas como formato de spec. La propia
  literatura las define como organizador de conversación y backlog, no como
  especificación suficiente; nuestro EARS + Dado/Cuando/Entonces + recorridos
  cubre su función y compila a test.
- Primera entrega = esqueleto andante (walking skeleton): el camino feliz de
  punta a punta en fino. Resuelve también las dependencias duras (la vieja
  pregunta 7).
- Calidad no funcional: entra como "Condiciones de uso" en F4 (5 preguntas en
  lenguaje de negocio) y sección "Calidad y límites" del spec con criterios
  comprobables (fit criteria a lo Volere, ISO 25010 destilado).
- Trazabilidad ligera: requisitos y criterios numerados (R-n, C-n); la
  auditoría cita el identificador en cada desviación.
- Stakeholders ocultos (modelo cebolla) en F1; documentos reales como fuente
  de requisitos y obligaciones legales/contractuales en F3; glosario del
  negocio (lenguaje ubicuo) en el spec.
- Seguridad técnica de base: delegada explícitamente al constructor en el
  encargo (no se pregunta al no técnico por sesiones ni copias).
- Design.md intermedio estilo Kiro: no; el plan es del constructor.
- Descartes deliberados: notaciones formales (UML/BPMN/DMN como notación),
  personas y mapas de empatía, prototipado de pantallas, métodos formales
  (TLA+/Alloy), marcos de proceso de equipo (Scrum, Double Diamond) y threat
  modeling completo. Motivo común: coste de ceremonia que no paga a esta
  escala o vive en el lado de la obra.

## Siguen abiertas

1. Ficha de superficie de uso: validar en el piloto que los 7 campos bastan.
2. Visor: ¿fuente embebida en la plantilla para identidad total? ¿Lanzador
   para Windows sin python3 en PATH?
3. Visor: ¿bifurcación lado a lado (dos ramas con contenido) en la v2 del
   esquema, o basta el desvío anidado?
