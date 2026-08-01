# Ingeniería de requisitos: instrucciones para el agente

Esta carpeta es una HERRAMIENTA, no un proyecto: contiene un método completo
para entrevistar a una persona de negocio y producir los planos (los spec
files) de su aplicación, con una web local para que los valide mirando.

1. Ante CUALQUIER petición que involucre un proyecto — una idea nueva, un
   código que YA EXISTE (en GitHub o en una carpeta local), una auditoría,
   o cambios sobre unos planos ya hechos — lee `RUNBOOK.md` ENTERO y sigue
   su triaje de modos (A: de cero, B: código existente, C: iteración).
   "Trabajar en un proyecto existente" es Modo B: jamás clones el repo y lo
   trabajes a pelo saltándote el método. Si lo que trae es mantenimiento de
   los proyectos YA creados ("actualiza mis proyectos", "¿están al día?"),
   es el **Modo D** del RUNBOOK: `visor/actualizar.py revisar --todos`,
   preguntar cuáles quiere y aplicar; el criterio para lo que ese workspace
   haya adaptado está en `ACTUALIZAR-PROYECTOS.md`. Si dudas de
   si algún flujo aplica, la duda se resuelve leyendo `RUNBOOK.md`, nunca
   concluyendo desde este resumen que "ningún flujo aplica".
2. Regla dura: NO guardes proyectos dentro de esta carpeta. La única escritura
   local permitida es el registro ignorado `.ingenieria-requisitos-local/`.
   Ni proyectos, ni
   specs, ni notas, ni temporales. El proyecto del usuario vive en SU
   carpeta de trabajo, fuera de aquí; si tu sesión está corriendo dentro de
   esta carpeta, pregúntale dónde quiere guardar su proyecto y trabaja allí.
3. Los scripts de la herramienta se invocan con la ruta de ESTA carpeta:
   `visor/servir.py` (la web local), `visor/validar.py` (validación de los
   planos), `visor/generar_spec.py` (el spec de un plano),
   `visor/compilar.py` (la documentación completa de la aplicación),
   `visor/bootstrap.py` (monta el workspace de trabajo completo desde los
   planos: meta-repo + repo de código, con el método de `plantilla/`) y
   `visor/actualizar.py` (Modo D: reparte el método a los workspaces ya
   creados; `revisar` informa, `aplicar` escribe solo lo que nadie tocó allí).
