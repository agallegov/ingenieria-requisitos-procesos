# Aislamiento opcional de constructores

`scripts/sandbox_lanzar.py` es una ayuda avanzada para envolver el proceso de un
constructor y limitar las rutas en las que puede escribir. No se ejecuta
automáticamente, no sustituye los permisos del sistema y no constituye por sí solo
una garantía de seguridad.

## Uso seguro

1. Crea la unidad y su worktree mediante `unidad.py`.
2. Ejecuta primero `sandbox_lanzar.py` sin `--ejecutar` y revisa el mecanismo y las
   rutas que muestra.
3. En esa máquina concreta, comprueba con un comando inocuo que escribir fuera del
   worktree falla y que el trabajo Git permitido sigue funcionando.
4. Solo después usa `--ejecutar`. Si cambia el sistema operativo o la herramienta de
   aislamiento, repite la comprobación.

El script busca, por este orden, `srt`, `sandbox-exec` o `bwrap`. Si no encuentra un
mecanismo se niega a ejecutar, salvo que la persona acepte expresamente
`--permitir-sin-sandbox`. La disponibilidad y el comportamiento de esas herramientas
dependen del ordenador; el workspace nunca debe fingir que las ha validado.

## Límites que intenta aplicar

- Escritura en el worktree y en las zonas Git necesarias para guardar un commit.
- Bloqueo de los puntos de configuración y hooks compartidos de Git.
- Bloqueo de lectura de directorios habituales de credenciales.
- Red denegada o limitada cuando el mecanismo elegido puede aplicarlo realmente.

Los worktrees comparten parte del repositorio Git. Por eso ampliar permisos al Git
común es una decisión explícita (`--git-compartido`) y debe evitarse si no hace falta.
Las ramas alternativas de sistema operativo pueden tener limitaciones distintas; el
resultado impreso por el programa es la fuente que se debe revisar antes de lanzar.

Para código hostil o ejecución desatendida se necesita una frontera administrada por
el dueño de la máquina —por ejemplo un contenedor o una política corporativa— y una
comprobación específica. Un repositorio clonado no puede concederse ni imponerse por
sí mismo privilegios de seguridad en el equipo del usuario.
