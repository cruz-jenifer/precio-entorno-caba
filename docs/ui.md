# Propuesta de interfaz

Diseño hecho con la skill `frontend-design`. Se eligió el frontend web propio: la página está en `web/` y la sirve `python -m precio_entorno.api`.

## Cambios respecto del primer plan

- **Delitos:** la escala pasó a gris azulado, como estaba previsto, y sus tonos se cortan por quintiles de las celdas a la vista. Con cortes proporcionales al máximo, una sola celda con muchos hechos dejaba casi todo el barrio en el tono más claro.
- **Leyenda:** muestra solo las muestras de color y se puede plegar. Las advertencias de cada capa están en «Cómo leer el mapa», plegado al principio, porque abiertas tapaban medio mapa.
- **Celular:** la marca usa el ancho angosto de Archivo para que entre en la barra, y los botones de capas se desplazan en una sola fila.
- **Coropletas:** el gris de los barrios tiene más contraste que en el plan, porque el mapa es el elemento principal.

## Brief propuesto

- **Tema:** elegir en qué barrio de CABA buscar un departamento para comprar o alquilar, con lo que hay alrededor a la vista.
- **Público:** una persona o una pareja que busca vivienda propia y no conoce todos los barrios. En la validación, también el equipo de una inmobiliaria que atiende varias búsquedas.
- **Tarea principal:** ver dónde rinde el presupuesto, revisar el entorno del barrio que interesa y crear una alerta. El flujo sigue siendo preferencias → comparación de barrios → búsqueda guardada → alerta.

### Lo que condiciona el diseño

- **Avisos sin fotos ni títulos:** solo hay precio, superficie, ambientes, barrio, expensas y enlace. No hay fotos para armar tarjetas como las de Airbnb. La unidad principal de la interfaz es el barrio, y el aviso aparece en segundo plano.
- **Sin puntajes:** el entorno se describe capa por capa y nunca se suma en un puntaje. Los delitos se muestran como hechos registrados, con su período.
- **Ubicación aproximada:** los pines de los avisos no declaran precisión. El mapa ubica barrios y capas públicas, no departamentos.

## Plan de diseño

### Color

| Nombre | Hex | Uso |
| --- | --- | --- |
| Vereda | `#F3F4F1` | Fondo general, gris frío de baldosa |
| Asfalto | `#1E2A32` | Texto y contornos de barrio |
| Jacarandá | `#6A4FB3` | Única acción y selección: barrio elegido, botón de alerta, filtros activos |
| Plátano | `#5E7D4F` | Plazas y parques. Fuera del mapa solo se usa en estados de éxito. |
| Cordón | `#CBD0CC` | Bordes, divisores y celdas vacías |
| Papel | `#FFFFFF` | Paneles sobre el mapa |

El jacarandá florece en noviembre en Buenos Aires y le da a la app un color propio que no es el de un portal inmobiliario. Como acento se usa solo para lo que la persona eligió. Las capas del mapa tienen su propia paleta de datos: los colores oficiales de cada línea de subte, la escala de ruido de amarillo a rojo y una escala gris azulada para delitos. El violeta de delitos actual pasa a gris azulado para no confundirse con el acento.

### Tipografía

- **Archivo**, de Omnibus-Type, una fundidora argentina, en una sola familia variable. Los títulos de barrio van en ancho expandido y peso 650, el cuerpo en ancho normal y peso 400, y precios y superficies con cifras tabulares.
- **Escala:** 13, 15, 18, 24 y 34 px, con interlineado de 1,45 para el cuerpo.
- **Descartada:** Montserrat, aunque lleve el nombre de un barrio porteño. Está en demasiados sitios y no diferencia.

### Layout

En escritorio el mapa ocupa la mitad derecha y la lista de barrios la izquierda, como en Airbnb. Los filtros quedan en una barra superior fija.

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Comprar | Alquilar   Hasta USD 110.000   40 m²+   2 amb.   [Me importa ▾] │
├───────────────────────────────┬──────────────────────────────────────┤
│ 15 barrios con opciones       │ (Subte) (Plazas) (Ruido) (Delitos)   │
│                               │                                      │
│ Almagro              15 avisos│        mapa de CABA                  │
│ USD 84.000 mediana            │   barrios con tono según cantidad    │
│ Subte A y B, 1 plaza          │   de avisos que encajan              │
│ ───────────────────────────── │                                      │
│ Balvanera            12 avisos│                                      │
│ ...                           │                                      │
└───────────────────────────────┴──────────────────────────────────────┘
```

Al elegir un barrio, el mapa se acerca y la lista se reemplaza por su ficha:

```text
┌───────────────────────────────┬──────────────────────────────────────┐
│ ← Todos los barrios           │ (Subte) (Plazas) (Ruido) (Delitos)   │
│ Almagro                       │                                      │
│ 15 avisos, mediana USD 84.000 │     Almagro con sus capas            │
│ [Crear alerta para Almagro]   │                                      │
│                               │                                      │
│ Entorno                       │                                      │
│ Subte A y B, 5 estaciones     │                                      │
│ Ruido ≥70 dBA de día: 82 %    │  leyenda abajo a la izquierda        │
│                               │                                      │
│ Avisos que encajan            │                                      │
│ USD 79.000  45 m²  2 amb.  ↗  │                                      │
└───────────────────────────────┴──────────────────────────────────────┘
```

En el celular el mapa ocupa la pantalla y la lista sube desde abajo como una hoja que se arrastra. Los filtros se abren en una pantalla completa. Todo se alinea a la izquierda, y los precios y superficies a la derecha dentro de su columna.

### Principios

1. **El mapa es el protagonista.** La comparación de barrios se ve en la ciudad y no en una tabla. Esa es la decisión audaz; lo demás queda sobrio.
2. **Cada número trae su fuente al alcance.** El período y la unidad aparecen al pasar el cursor o en la ficha, no en leyendas largas debajo del mapa.
3. **Una sola acción principal por pantalla:** comparar en la lista y crear la alerta en la ficha.
4. **Datos ficticios marcados siempre:** en la demo, una franja fija avisa que los avisos son de ejemplo.

## Revisión contra los valores por defecto

- **Separadores con punto medio:** la app actual los usa en todos sus textos («Catálogo X · N avisos»), y es uno de los rasgos genéricos que la skill pide evitar. En el diseño nuevo se reemplazan por frases completas o por comas.
- **Tarjetas idénticas con sombra:** la lista de barrios usa filas separadas por una línea de color cordón, sin tarjetas ni sombras. El único elemento elevado es el panel sobre el mapa.
- **Acento terracota o verde ácido:** el acento es jacarandá, tomado de la ciudad y de la época del año.
- **Etiquetas en mayúsculas y números de paso:** los pasos 1, 2 y 3 de la app actual desaparecen. La barra de filtros y la selección en el mapa ya ordenan el recorrido.

## Plataforma

Streamlit no permite una lista y un mapa vinculados al pasar el cursor, paneles flotantes sobre el mapa ni una hoja deslizable en el celular. Hay dos caminos:

| Opción | Qué implica | Costo |
| --- | --- | --- |
| **A. Frontend web propio** | Una página HTML con MapLibre y deck.gl, servida por una API chica en Python que reutiliza `store`, `matching` y `entorno`. Streamlit queda para importar datos y probar. | Mayor: API, página y pruebas nuevas |
| **B. Streamlit con estilos** | Tema propio, tipografía, CSS y diseño ancho con columnas. Mapa y lista en paralelo, pero sin vínculo al pasar el cursor ni hoja móvil. | Menor: se mantiene todo lo actual |

La recomendación es la A, porque el diseño depende del vínculo entre la lista y el mapa. La B sirve si la prioridad es llegar rápido a la entrega del capstone.
