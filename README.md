# Ingeniería de requisitos con IA

Convierte lo que sabes de tu negocio en unos planos que una IA puede
construir sin inventarse nada. Tú no escribes requisitos: cuentas tu negocio,
la IA te entrevista, y validas mirando una web que se va rellenando sola.

## Qué necesitas

- Un ordenador con Python 3. Si no lo tienes, tranquilo: tu propia IA lo
  comprobará al empezar y lo instalará contigo.
- Un agente de IA que pueda ejecutar comandos en tu ordenador (por ejemplo
  Claude Code). Un chat web normal no vale: no puede levantar el visor.
- Entre 45 minutos y 2 horas, y tu negocio en la cabeza: el proceso de
  memoria, con nombres y números reales.

## Cómo se usa (3 pasos)

1. Descomprime esta carpeta donde quieras y abre tu agente de IA dentro de
   ella.
2. Dile: **"Lee RUNBOOK.md y sigue sus instrucciones."**
3. Cuenta tu negocio y corrige lo que te enseñe. Con hechos reales, no con
   teorías. La IA hace el resto.

Durante la conversación se te abrirá una página en el navegador: son tus
planos, y se actualizan solos según avanza la entrevista. El servidor de esa
página se apaga solo a los 15 minutos; si se apaga, pídele a tu IA que lo
vuelva a levantar.

## Qué obtienes al final

Una carpeta `proyectos/<tu-proyecto>/` con:

- `planos.json`: todo tu proyecto como datos (lo que pinta la web).
- `spec.md`: la especificación completa en texto, generada desde los datos.
- `encargo.md`: el texto exacto que debes darle a la IA que construya (o
  audite) tu aplicación, en una sesión nueva.

## Reglas de oro

- Tú nunca redactas: cuentas y corriges leyendo.
- Si algo cambia después, se cambian los planos y se regenera; nunca le
  pidas cambios "de palabra" a la IA que construye.
- La validación final es usar la aplicación con los ejemplos reales de tus
  planos, no mirar pantallas bonitas.
