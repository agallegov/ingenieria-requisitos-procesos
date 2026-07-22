# Ingeniería de requisitos con IA

Convierte lo que sabes de tu negocio en unos planos que una IA puede
construir sin inventarse nada. Tú no escribes requisitos: cuentas tu negocio,
la IA te entrevista, y validas mirando una web que se va rellenando sola.

## Qué necesitas

- Un ordenador con Python 3. Si no lo tienes, tranquilo: tu propia IA lo
  comprobará al empezar y lo instalará contigo.
- Un agente de IA que pueda ejecutar comandos en tu ordenador (por ejemplo
  Claude Code). Un chat web normal no vale: no puede levantar el visor.
- Tiempo tranquilo por delante, y tu negocio en la cabeza: el proceso de
  memoria, con nombres y números reales.

## Cómo se usa (3 pasos)

1. Descomprime esta carpeta donde quieras. Es la herramienta: no se toca ni
   se guarda nada dentro.
2. Abre tu agente de IA en la carpeta donde quieras guardar tu proyecto
   (por ejemplo `Documentos/mi-app/`) y dile:
   **"Lee el RUNBOOK.md de [la ruta de esta carpeta] y sigue sus
   instrucciones."**
   Si abres el agente dentro de la herramienta también funciona: te
   preguntará dónde guardar tu proyecto.
3. Cuenta tu negocio y corrige lo que te enseñe. Con hechos reales, no con
   teorías. La IA hace el resto.

Durante la conversación se te abrirá una página en el navegador: son tus
planos, y se actualizan solos según avanza la entrevista. Mientras la tengas
abierta se mantiene viva; si pasa un buen rato sin usarse se apaga sola, y
entonces basta pedirle a tu IA que la vuelva a levantar.

## Qué obtienes al final

En tu carpeta de proyecto (la tuya, fuera de la herramienta):

- `planos.json`: tu proyecto como datos (lo que pinta la web). En
  aplicaciones grandes, un mapa general más `actividades/<actividad>/` con
  los planos de cada actividad.
- `spec.md` y `encargo.md`: la especificación en texto y el encargo exacto
  para la IA que construya (o audite) tu aplicación, en una sesión nueva.
- `especificaciones/`: la documentación completa de tu aplicación, siempre
  regenerable: `01-constitution/` (las reglas y el mapa de toda la app) y
  `02-flows/` (un documento por actividad).

## Reglas de oro

- Tú nunca redactas: cuentas y corriges leyendo.
- Si algo cambia después, se cambian los planos y se regenera; nunca le
  pidas cambios "de palabra" a la IA que construye.
- La validación final es usar la aplicación con los ejemplos reales de tus
  planos, no mirar pantallas bonitas.
