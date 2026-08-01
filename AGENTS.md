# Ingeniería de requisitos: instrucciones para el agente

Esta carpeta es una HERRAMIENTA, no un proyecto: contiene un método completo
para entrevistar a una persona de negocio y producir los planos (los spec
files) de su aplicación, con una web local para que los valide mirando.

1. Si el usuario pide crear o definir un proyecto, lee `RUNBOOK.md` ENTERO y
   síguelo al pie de la letra. Si pide actualizar workspaces creados por esta
   lanzadera, lee `ACTUALIZAR-PROYECTOS.md` y realiza la auditoría razonada.
2. Regla dura: NO guardes proyectos dentro de esta carpeta. La única escritura
   local permitida es el registro ignorado `.ingenieria-requisitos-local/`.
   Ni proyectos, ni
   specs, ni notas, ni temporales. El proyecto del usuario vive en SU
   carpeta de trabajo, fuera de aquí; si tu sesión está corriendo dentro de
   esta carpeta, pregúntale dónde quiere guardar su proyecto y trabaja allí.
3. Los scripts de la herramienta se invocan con la ruta de ESTA carpeta:
   `visor/servir.py` (la web local), `visor/validar.py` (validación de los
   planos), `visor/generar_spec.py` (el spec de un plano),
   `visor/compilar.py` (la documentación completa de la aplicación) y
   `visor/bootstrap.py` (monta el workspace de trabajo completo desde los
   planos: meta-repo + repo de código, con el método de `plantilla/`).
