# Sistema visual de Lüga

Usá esta referencia para mantener coherentes los componentes de la aplicación. Las variables del bloque inicial de `web/styles.css` son la fuente de los valores que usa la interfaz.

La dirección es funcional y sobria: datos legibles, superficies opacas y una acción principal por contexto. La consulta de `ui-ux-pro-max` aporta la dirección de minimalismo funcional; la paleta y Archivo conservan la identidad existente de Lüga.

## Colores y significado

| Variable CSS | Valor | Uso |
| --- | --- | --- |
| `--vereda` | `#F3F4F1` | Fondo de la aplicación |
| `--papel` | `#FFFFFF` | Formularios y paneles |
| `--pieza` | `#F5F4F1` | Grupos de datos y controles deshabilitados |
| `--asfalto` | `#23272B` | Texto principal |
| `--asfalto-suave` | `#55626B` | Texto secundario y ayudas |
| `--jacaranda-oscuro` | `#553C99` | Acción principal y texto de selección |
| `--jacaranda` | `#6A4FB3` | Foco y borde de selección |
| `--jacaranda-tinte` | `#ECE8F7` | Fondo de selección y acciones secundarias |
| `--borde-control` | `#84909A` | Límite visible de los campos |
| `--cordon` | `#CBD0CC` | Separadores y bordes decorativos |
| `--platano` | `#3E6B4F` | Confirmación, junto con un mensaje |
| `--alerta` | `#9A3412` | Error, junto con su explicación |

Conservá los colores de datos del mapa definidos en `web/app.js`: líneas de subte, ruido, delitos y otros elementos tienen significados propios. El verde de plazas del mapa sigue siendo `#5E7D4F`.

## Tipografía

Usá Archivo para toda la interfaz, con `system-ui` como alternativa. No agregues otra fuente para precios o encabezados.

| Uso | Tamaño | Regla |
| --- | --- | --- |
| Ayudas, etiquetas y tablas | 14 px | `--t-chico` |
| Cuerpo y campos | 16 px | `--t-base`, interlineado 1,5 |
| Títulos de sección | 18 px | `--t-medio` |
| Títulos de diálogo | 24 px | `--t-grande` |
| Título principal | 32 px | `--t-titulo`, adaptable en celular |
| Nombre de barrio | 52 px / 40 px | Escritorio / celular |

Los precios y superficies usan cifras tabulares. Los títulos pueden usar el ancho expandido de Archivo. Conservá las unidades junto al dato y permití que las etiquetas se distribuyan en varias líneas.

## Espaciado y forma

Usá `--espacio-1`, `2`, `3`, `4`, `6`, `8` y `12`: corresponden a 4, 8, 12, 16, 24, 32 y 48 px. Reservá 8 px entre elementos relacionados, 16 px dentro de grupos y 24–32 px entre secciones. Los ajustes de posicionamiento del mapa pueden necesitar medidas intermedias.

Los campos y acciones usan `--radio-control` (12 px); los paneles internos, `--radio-panel` (16 px); la hoja principal, `--radio-hoja` (24 px). Las opciones segmentadas, chips y marcas conservan `--radio-pastilla`.

## Botones y formularios

- Usá `.boton-primario` para confirmar la tarea principal: crear una alerta, interpretar una descripción o aplicar sus filtros.
- Usá `.boton-comparar` para avanzar con una selección de barrios y `.boton-texto` para cerrar, volver o consultar detalles.
- Mantené una altura mínima de 44 px. Los estados activo, deshabilitado y ocupado deben conservar su significado y no cambiar el ancho del control.
- Usá el mismo borde y radio en campos, selectores y áreas de texto. Los campos agrupados en `.campo` llevan un único borde exterior.
- Mantené etiquetas visibles y conectá las ayudas y errores con el campo. Los errores conservan el valor escrito y explican cómo corregirlo.
- Mostrá las confirmaciones con texto y fondo verde suave; los errores, con texto y fondo cálido. No transmitas el estado solo mediante color.
- El foco usa un contorno violeta de 3 px. Las transiciones duran 150 ms y se eliminan con movimiento reducido.

La aplicación usa un tema claro explícito. Comprobá su lectura cuando el sistema operativo prefiera un tema oscuro; no agregues una variante oscura parcial.

## Verificación

Ejecutá `python -m unittest discover -s tests -v` y los casos `tests/test_web_*.cjs` con `node --test`. Para revisar el recorrido visual, ejecutá `python tests/verificar_recorrido_ui.py`; requiere Playwright y Chromium. Si usás un Chromium existente, indicá su ejecutable con `--browser`.

Verificá los estados de botones y campos, el contraste de texto y bordes, el foco, el movimiento reducido y el desbordamiento entre 320 y 1440 px. Las pruebas del recorrido usan bases temporales y tienen el envío de correo desactivado.
