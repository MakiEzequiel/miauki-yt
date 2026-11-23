# Probar Miauki YT en Windows 10 (sesión limpia)

Sirve para verificar el `.exe` **como lo recibe una persona que nunca lo abrió**.
No hace falta instalar Python ni nada: el `.exe` ya trae todo.

## Antes de empezar

- **Paquete**: `Miauki YT v1.0.0 - Windows.zip` (fuera del repo, en
  `C:\Users\Maki\Desktop\PROYECTOS\Miauki YT\Entrega\`; 83,5 MB). Adentro:
  `Miauki YT.exe` + `LICENCIAS.txt`. Se rearma con `python tools/armar_entrega.py`
  (antes vivía en `%TEMP%`, que Windows puede borrar).
- **Máquina**: Windows 10 u 11, 64 bits, 4 GB de RAM o más, 300 MB libres.
- **Sin permisos de administrador**: se abre con doble clic desde el Escritorio
  o desde una carpeta normal (no `C:\Program Files`).
- **SmartScreen**: si Windows muestra "Windows protegió su PC", es normal en un
  programa sin firma comercial. Botón **Más información → Ejecutar de todas
  formas**.
- **Datos**: Miauki guarda historial, cola y ajustes en `%LOCALAPPDATA%\Miauki YT`.
  Para probar "como nuevo" se puede cerrar el programa y borrar esa carpeta.

Anotá al lado de cada punto: **OK**, **FALLA** (y qué pasó) o **NO PROBÉ**.

## Las 12 cosas

| # | Qué hacer | Qué tiene que pasar |
|---|---|---|
| 1 | Doble clic en `Miauki YT.exe`. | Abre en menos de 3 segundos y no pide administrador. |
| 2 | La primera vez, mirar la pantalla de Inicio. | Aparece el recorrido "Así de fácil se usa" (7 pasos). Al terminarlo o saltarlo **no vuelve a aparecer** la próxima vez. |
| 3 | Pegar un link de YouTube en el campo y tocar **Analizar**. | En unos segundos aparece la miniatura, el título, la duración y la lista de calidades ("Mejor · 1080p", "720p"…). |
| 4 | Elegir "Mejor · 1080p" y tocar **MIAUK!**. | El aviso "Agregada a la cola" aparece y la descarga se ve en **Cola** con la barra avanzando. |
| 5 | Esperar a que termine. | El estado pasa a **Terminada** en verde con su ícono y el aviso "Guardado." Aparece una notificación "Ver cola". |
| 6 | Abrir el archivo descargado con el reproductor de Windows (doble clic). | Se reproduce con imagen y sonido (es H.264 + AAC en MP4, lo que pide la opción "Máxima compatibilidad"). |
| 7 | Mirar el panel **Guardar en** (columna derecha). | Se ve el rótulo "Guardar en", la carpeta y, al pasar el mouse, un globo con la ruta completa. **Cambiar** abre el selector de carpetas y el cambio queda guardado. |
| 8 | Copiar un link de YouTube y, **sin tocar el campo**, apretar **Ctrl+V** en la ventana. | El link se pega solo y se analiza (no hay que tocar Analizar). |
| 9 | Arrastrar un link desde el navegador y soltarlo sobre la ventana. | Aparece la capa de vidrio "Soltá el link acá" y, al soltar, se analiza. Si se arrastra un archivo o una imagen, avisa con un mensaje amable y no rompe nada. |
| 10 | Probar un link de TikTok con **Analizar** (sin configurar cookies). | Muestra título, duración y calidades. Se puede descargar en MP4. |
| 11 | Con la ventana **detrás** de otra, lanzar una descarga y esperar. | Al terminar, el botón de Miauki **parpadea en la barra de tareas** hasta que volvés a la ventana. Si la ventana ya está al frente, no parpadea. |
| 12 | Ir a **Historial** y después a **Ajustes**. | Historial: cada entrada tiene ícono de tipo (video/música/imagen), el sitio con su ícono y el texto **nunca** dice "otro". Ajustes: la tarjeta **Motor de descargas** muestra la versión, lo revisado y el botón **Buscar actualización**; en **Acerca** están "Ver el recorrido", "Detalles técnicos" y "Copiar datos para pedir ayuda". |

## Extra (2 minutos)

- **Sin internet**: desconectar el WiFi y abrir Miauki. Tiene que abrir normal,
  sin carteles de error. La tarjeta Motor puede decir que no se pudo comprobar.
- **Motor de descargas**: en Ajustes, tocar **Buscar actualización**. Si hay una
  versión nueva, la baja, la prueba y avisa **"Motor actualizado"**. Si algo
  falla, se queda con la que ya andaba (nunca queda un motor roto).

## Si algo falla

1. Abrir **Acerca → Copiar datos para pedir ayuda**.
2. Pegar ese texto en un mensaje, junto con: el paso que falló, el link usado
   (si no es privado) y una captura de la pantalla.
3. Los registros quedan en `%LOCALAPPDATA%\Miauki YT\registros` (Acerca →
   "Abrir carpeta de registros").

## Qué NO cubre esta prueba

- Firma digital: el `.exe` no está firmado, por eso aparece SmartScreen.
- Varias cuentas de usuario de Windows en la misma máquina.
- Pantallas de más de 4K o configuraciones de escalado poco comunes.
