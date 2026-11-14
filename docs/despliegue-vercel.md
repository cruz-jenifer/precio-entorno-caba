# Despliegue privado en Vercel

La interfaz web también corre en Vercel, en `https://precio-entorno-caba.vercel.app`, con los **datos reales y solo para la cuenta dueña del proyecto**. Los permisos de las fuentes cubren la lectura de sus sitios, no mostrar sus avisos al público. Por eso el proyecto está protegido con Vercel Authentication para todos los despliegues: para abrirlo hay que iniciar sesión en Vercel con esa cuenta.

## Cómo está armado

- **Entrada:** `precio_entorno/vercel_app.py`, declarada en `[tool.vercel] entrypoint`. La raíz del repositorio tiene `app.py`, que es la app de Streamlit, y no se despliega.
- **Disco de solo lectura:** en Vercel solo `/tmp` admite escritura. Al arrancar, cada instancia copia las bases reales a `/tmp/precio-entorno/` y crea ahí la demo. **Una búsqueda guardada en Vercel dura lo que dura la instancia.** La base que cuenta sigue siendo la local, que actualiza `actualizar.py`. El alta con mail se manda a Make como en local, así que el aviso por correo no depende de esa copia.
- **Carpeta desplegada:** la arma `scripts/preparar_vercel.py` en `.vercel-build/` (ignorada por Git):
  - código de `HEAD` (`git archive`), no del árbol de trabajo, para no publicar cambios sin confirmar;
  - bases reales, capas del mapa, CSV anuales del Mapa del Delito y radar (unos 60 MB);
  - `pyproject.toml` con solo FastAPI, NumPy y Matplotlib, `.python-version` y `vercel.json`.
  No se copian `.env`, crudos de captura ni la app de Streamlit.

## Desplegar o actualizar los datos

```bash
python scripts/preparar_vercel.py --desplegar
```

Sin `--desplegar`, el script solo arma la carpeta. La carpeta queda vinculada al proyecto en `.vercel-build/.vercel/`, y el script la conserva. Para que Vercel muestre avisos nuevos hay que volver a correr el comando después de `actualizar.py`.

**No desplegar con `vercel deploy` a secas desde `.vercel-build/`.** La carpeta está dentro del repositorio y la CLI adjunta el último commit. Vercel bloqueó un despliegue así («el autor del commit no tiene permiso para crear despliegues en este proyecto»). `--desplegar` corre la CLI sin acceso a Git.

## Protección

- El proyecto usa `ssoProtection.deploymentType = "all"`: la URL de producción y las generadas piden iniciar sesión.
- **Comprobarlo después de cada cambio de configuración**, sin sesión:

  ```bash
  curl -s -o /dev/null -w "%{http_code}\n" https://precio-entorno-caba.vercel.app/api/estado
  ```

  Tiene que responder `302` (redirección al inicio de sesión de Vercel), nunca `200`.
- **Lección del primer despliegue (13/11/2026):** la protección estándar de un proyecto nuevo cubre las URL generadas, pero no `precio-entorno-caba.vercel.app`. Además, el primer despliegue de un proyecto va directo a producción. Durante unos minutos esa URL respondió sin sesión, hasta que se pasó la protección a `all`. En un proyecto nuevo, activar la protección para todos los despliegues **antes** del primer despliegue.

## Secretos

- `MAKE_BUSQUEDAS_WEBHOOK_URL` se carga como variable sensible del entorno de producción, con `vercel env add MAKE_BUSQUEDAS_WEBHOOK_URL --environment production --sensitive` (el valor lo pega la persona dueña de la cuenta). Hace falta volver a desplegar para que tome efecto.
- Nunca se suben `.env` ni `.env.local`. Si la CLI crea un `.env.local` en `.vercel-build/` (token OIDC de desarrollo), el script lo borra en la siguiente preparación.
