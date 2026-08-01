# Runbook · DEPLOY

**Cuándo:** llevar a una etapa real algo ya mergeado — primer arranque, actualización, subida de
etapa (`01-constitucion/bias.md`) y el despliegue de urgencia del paso 6 de `hotfix.md`.
**Quién:** el rol DEPLOY (`roles.md`: un rol = una sesión; el único con manos en la máquina
destino). El constructor jamás despliega; fuera de un despliegue, producción es de solo lectura.
**Plantilla:** `plantillas/despliegue.md` — una ficha POR despliegue, en la unidad que despliega
(`docs/05-trabajo/NNN-slug/despliegue.md`); si no nace de una unidad (hotfix), se pega en la
sección 6 · Cierre de `docs/bugs/NNN-slug.md`.
**Contrato de cierre:** etapa destino verificada en caliente con evidencia + ficha rellena +
anotado qué commit corre dónde, desde cuándo y quién lo puso.

## Precondiciones que BLOQUEAN (se comprueban antes de tocar la máquina)

1. `<HARD-GATE>` **Plano de deploy escrito**: `docs/conocimiento/plano-deploy.md` (entrevista de
   arranque del rol, `roles.md`). Máquinas, etapas, comandos y quién da el OK salen de ahí, nunca
   de la memoria. Sin plano, lo primero de la sesión es la entrevista.
2. `<HARD-GATE>` **Backup verificado = restaurado de prueba**, hecho AHORA (no vale el de anoche
   si hay migración de datos). El detalle no se repite aquí: `migracion.md` §Subir de etapa, paso
   1. Las dos evidencias —volcado y restauración— van pegadas en la ficha.
3. `<HARD-GATE>` **OK explícito del usuario** sobre el comportamiento que va a salir, probado con
   sus ejemplos reales (`roles.md`, línea roja del modo novato). "Los tests pasan" no es su OK.
4. Antes de la PRIMERA salida a internet (etapa 2): unidad tipo `auditoria` de seguridad cerrada.

## Los pasos

1. **Abrir la ficha** desde `plantillas/despliegue.md`: commit, etapa, responsable, ventana,
   pasos, verificaciones y rollback.
2. **Actualizar `main/` a `origin/main`.** Verificar que el commit que se pretende desplegar
   pertenece a esa rama. No se despliega un worktree ni una rama sin merge.
3. **Ejecutar el gate:** `python docs/00-metodo/scripts/lint_deploy.py`. Un rojo bloquea.
4. **Crear y restaurar el backup de prueba.** Pegar ambas evidencias.
5. **Leer el plan en voz alta con el usuario:** qué sale, dónde, cuánto tardará y cómo se
   vuelve atrás. Obtener su autorización explícita para mutar esa etapa.
6. **Ejecutar por el camino declarado** en `plano-deploy.md`, nunca con comandos improvisados.
   Si el camino no cubre el caso, parar y crear una unidad normal para arreglarlo.
7. **Verificación técnica inmediata:** procesos, salud, migraciones, colas y errores.
8. **Verificación de negocio:** recorrer un flujo real de punta a punta con datos seguros.
9. **Verificación de vigilancia:** monitor en verde y un error inocuo visible en el registro
   indicado por `plano-observabilidad.md`.
10. **Decidir:** todo verde → pedir al usuario que pruebe; cualquier rojo → rollback.
11. `<HARD-GATE>` **OK del usuario sobre la etapa real.** Sin ese OK, el despliegue no se
    declara correcto.
12. **Registrar:** commit, etapa, fecha, persona, duración y resultado en la ficha, el plano
    de deploy y `ESTADO.md`.

## Qué se anota al terminar, y dónde

- **La ficha**: commit/versión, etapa, evidencias, resultado, fecha y quién.
- **`conocimiento/plano-deploy.md`**: la línea de verdad — qué commit corre en qué etapa, desde
  cuándo y quién lo desplegó (`migracion.md`, paso 6) — y se sube `actualizado:`.
- **`ESTADO.md`**: una línea con la etapa y el commit desplegado. Es fichero compartido: se
  escribe dentro del ritual de cierre, indivisible (`00-metodo/README.md` §Los rituales).

## Si falla

- **Se decide en minutos, no en horas.** Disparan vuelta atrás: verificación en caliente en rojo,
  errores nuevos en el registro, o el usuario diciendo "esto no es lo que aprobé". Ante la duda se
  vuelve atrás: investigar se investiga en local, nunca con la etapa real coja.
- **Cómo:** el plan de vuelta atrás de la ficha, tal cual está escrito; si el despliegue migró
  datos, restaurando el backup de la precondición 2 (por eso se prueba ANTES).
- **Después:** el fallo se abre como `bug` con su ficha y su triaje, y el despliegue **no se
  reintenta** hasta que esa unidad cierre. La ficha queda con resultado "vuelta atrás" y su porqué.
