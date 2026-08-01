# Bias tecnológico — GENÉRICO (este tipo de proyecto aún no tiene receta cerrada)

**Función:** acotar la fase 3 (Investigación). Este proyecto no es una aplicación web de
gestión, así que no viaja el stack por defecto del método: **el stack se decide en la fase 3,
con investigación y un ADR que lo justifique**, guiado por estos principios universales.

## Los principios (aplican a CUALQUIER tipo de software)

1. **100% open source.** Nada propietario en el stack de desarrollo.
2. **Mínimo código posible.** La mejor línea es la que no se escribe.
   Reutilizar > configurar > escribir. Reinventar la rueda: prohibido salvo ADR.
3. **Máxima adherencia a la herramienta elegida.** Se hace como su documentación oficial
   dice ("the framework way"). Desviarse exige ADR.
4. **Mínima invención de la IA.** Elegir tecnología aburrida, estable y con máxima huella
   de documentación y ejemplos; el mínimo espacio para que el agente invente.
5. **SaaS: la línea es "¿puedo irme en una tarde?"** — protocolo portable sí, plataforma
   que captura datos o lógica no.

## Qué debe producir la fase 3 con esto

`03-investigacion/SINTESIS.md` con: el stack elegido y por qué (fuentes oficiales y
recientes), qué regala cada pieza (menos código propio), y un ADR por cada decisión
que se aparte de los principios. Sin stack decidido no se especifica ninguna unidad.
