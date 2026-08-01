# Bias tecnológico — BROWNFIELD (el código ya existe)

**Función:** acotar la fase 3 (Investigación). El stack de este proyecto NO se elige:
**ya está elegido — es el que vive en `main/`**. Aquí mandan tres reglas:

## 1. Adherencia total al stack existente

Se construye como ya se construye en ese repo: mismos frameworks, mismas convenciones,
mismos comandos. Cambiar una pieza del stack no es una unidad normal: es una `migracion`
con su ADR. Reescribir lo que funciona: prohibido sin decisión explícita del humano.

## 2. Primero conocer, después tocar: la ADOPCIÓN (primera unidad, obligatoria)

La primera unidad del workspace es fija — tipo `investigacion` + `auditoria`, carril
completo — y ninguna otra unidad se despacha antes de cerrarla:

- **Inventario extraído del código** (con rutas citadas, no de memoria): estructura del
  repo, stack real y versiones, comandos de build/test/arranque, y toda la documentación
  existente (README, docs/, configs, comentarios clave).
- **Estado de los tests**: ¿hay suite? ¿corre? ¿está en verde? (output real pegado).
  Sin suite = primera deuda declarada: **no se toca comportamiento sin red de tests**.
- **Salidas** (todas al meta-repo — el repo de código no se toca en la adopción):
  `03-investigacion/SINTESIS.md` (el stack existente documentado como bias efectivo, con
  los comandos de build/test/arranque), y el **gap-map código↔flujos**: qué promete el mapa
  de la entrevista que el código no hace, y qué hace el código que el mapa no recoge →
  candidatas al ROADMAP.

## 3. Los principios universales siguen valiendo

Open source, mínimo código, mínima invención de la IA, y la regla SaaS ("¿puedo irme en
una tarde?") — como criterio para lo NUEVO que se añada, nunca como excusa para reescribir
lo que ya funciona.
