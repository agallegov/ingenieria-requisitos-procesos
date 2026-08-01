# AGENTS.md del REPO DE CÓDIGO — plantilla

> Esto NO es el AGENTS.md del meta-repo (ese ya existe en la raíz del workspace y es el
> router del padre). Esto es el fichero que vive **dentro del repo de código**, en `main/`, y
> lo escribe la PRIMERA unidad del esqueleto andante, cuando ya se sabe con qué se construye.
>
> Por qué es obligatorio: el método dice "suite en verde" y "lanzar una instancia para que el
> usuario la pruebe" en cada cierre de cada unidad. Sin los comandos exactos escritos aquí,
> esos pasos no los puede ejecutar un agente fresco, y cada constructor se los inventa.
> Regla que lo exige: `runbooks/planificacion.md`, regla 6.
>
> Copia lo de debajo de la línea al `AGENTS.md` del repo de código y rellena los huecos con
> comandos **literales y copiables**, probados en esta máquina. Ni "instala las dependencias"
> ni "corre los tests": el comando exacto.

---

# AGENTS.md — <nombre del repo de código>

Repo de código de «<título del proyecto>». Se orquesta desde su meta-repo (la carpeta padre;
ver `repos.yaml` allí). Aquí solo vive el código de la aplicación.

## Comandos (literales, probados; los usa el método en cada cierre)

| Para… | Comando |
|---|---|
| Levantar el entorno desde cero | `<comando>` |
| Correr la suite completa | `<comando>` |
| Correr solo los end-to-end | `<comando>` |
| Lanzar una instancia para que la use el usuario | `<comando>` → `<URL o cómo se abre>` |
| Comprobación de seguridad antes de publicar | `<comando>` |
| Parar / limpiar | `<comando>` |

## Qué necesita esta máquina

<Lo que hay que tener instalado, y la versión. Si algo de aquí no aparece en verde en
`docs/00-metodo/scripts/doctor.py` del meta-repo, no es una dependencia: es un problema.>

## Estructura

<Dos o tres líneas: dónde vive cada cosa, para que el discovery de código de un agente sea
barato. Una funcionalidad vive en SU módulo.>

## Reglas de este repo

- Los secretos van en `.env` (fuera de git) y **el `.env` está en `.dockerignore`**: un
  secreto horneado en una imagen es un secreto publicado.
- Las dependencias de desarrollo y test están separadas de las de producción.
- Ningún script de datos de ejemplo (usuarios de prueba, superusuarios) se ejecuta solo ni
  imprime credenciales por pantalla o en los logs.
- Los tests se escriben antes que el código y no se debilitan para que pase la suite.
