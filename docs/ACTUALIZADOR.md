# Actualizador del motor (yt-dlp) — diseño

Fase 7, Parte A. Fecha: 20/10/2026. Aprobado por Maki (decisión 1 de la fase:
se actualiza solo en cada inicio y además hay un botón manual rosa fucsia neón).

Fuentes oficiales consultadas el 20/10/2026 (no de memoria):

- PyPI JSON API: <https://pypi.org/pypi/yt-dlp/json> (versión, `sha256` de cada
  archivo, tamaño, `requires_python`).
- Lanzamiento oficial en GitHub:
  <https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest> (etiqueta y lista
  de archivos, incluido `SHA2-256SUMS.sig`).
- README oficial de yt-dlp (dependencias, firmas, requisitos de JavaScript):
  <https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/README.md>.
- pywebview 6.2.1 (eventos de ventana y `create_window`): ya documentado en
  `docs/DECISIONES.md`; no cambia nada para esta parte.

## 1. Fuente: PyPI (wheel) y no el lanzamiento de GitHub

| | PyPI (`yt_dlp-<ver>-py3-none-any.whl`) | GitHub (`yt-dlp.tar.gz`) |
|---|---|---|
| Formato | wheel = zip con el paquete **Python puro** | tar.gz con el paquete |
| Hash oficial | `digests.sha256` en el JSON de PyPI | `SHA2-256SUMS` |
| Firma | no publica firma | `SHA2-256SUMS.sig` (GPG) |
| Tamaño | 3,2 MB | 6,0 MB |
| Piezas necesarias | 1 JSON + 1 archivo | 1 JSON + 1 suma + 1 archivo |

**Se elige PyPI.** Motivos:

1. Es el artefacto que instala `pip`: el mismo binario que usa el proyecto.
2. El `sha256` viene en la **misma respuesta oficial** que la versión y el
   tamaño: una sola pieza de confianza, sin parsear archivos de sumas.
3. No hay `.exe` ni binarios: solo código Python (`py3-none-any`).
4. GitHub no publica el wheel; habría que bajar el `.tar.gz` (el doble de
   tamaño) y extraerlo igual.

**Cruce con GitHub (defensa en profundidad).** La actualización solo se acepta
si la misma versión existe como lanzamiento oficial en
`api.github.com/repos/yt-dlp/yt-dlp/releases/latest` (se compara la
etiqueta con la versión **por números**: PyPI dice `2026.8.19` y la etiqueta
`2026.08.19`, que es la misma). Para reemplazar
un archivo, un atacante tendría que controlar **dos** cuentas oficiales.

**Firma GPG: no se verifica, y está documentado por qué.** yt-dlp publica
`SHA2-256SUMS.sig` y su clave pública (`public.key`), pero comprobarla requiere
GnuPG instalado (`gpg.exe`, no viene con Windows) o una biblioteca criptográfica
nueva. Las dos opciones agregan piezas o dependencias que
hoy no existen; el hash de PyPI + el cruce con GitHub cubren la integridad
frente a una descarga corrupta o a un espejo falso. Si en el futuro se firma el
`.exe`, se puede sumar GnuPG al build.

Nunca se baja ni se ejecuta un `.exe`. No se usa `curl_cffi` ni ningún binario.

## 2. Qué se descarga y cómo se guarda

1. `GET https://pypi.org/pypi/yt-dlp/json` con
   `User-Agent: Miauki-YT/<versión de la app>`; tope 2 MB; timeout 10 s.
2. Se elige el archivo con `packagetype == "bdist_wheel"` y nombre
   `yt_dlp-<ver>-py3-none-any.whl`. Tope **20 MB**.
3. `GET` del archivo en `files.pythonhosted.org` (host de la lista blanca;
   se comprueba también la URL final después de las redirecciones). Tope
   **20 MB** y timeout 60 s. Se corta si el `Content-Length` o los bytes
   recibidos pasan el tope.
4. `sha256` calculado en streaming y comparado con el del JSON de PyPI. Si no
   coincide, se descarta y se registra (sin datos personales).
5. **Extracción segura**: se lee el zip en memoria. Se rechaza cualquier
   entrada con ruta absoluta, `..`, letra de unidad, enlace simbólico o nombre
   raro; solo se copian las que empiezan con `yt_dlp/`. Resultado:
   `%LOCALAPPDATA%\Miauki YT\motor\yt-dlp-<versión>\yt_dlp\...`.
   Se escribe primero en `motor\tmp-<aleatorio>\` y, ya verificada, se renombra
   a su carpeta definitiva (el renombre es atómico en el mismo volumen).
6. Si algo falla en cualquier paso, se borra la carpeta temporal.

## 3. Prueba de humo antes de activar

`Miauki YT.exe --probar-motor <carpeta> [versión]` (modo oculto, igual que
`--selftest`):

- `sys.path.insert(0, <carpeta>)` **dentro de ese proceso** y `import yt_dlp`
  exclusivamente desde ahí (se comprueba `yt_dlp.__file__`).
- Compara `yt_dlp.version.__version__` con la esperada (la que le pasa el
  actualizador; si no viene, se toma del nombre de la carpeta).
- Crea el extractor (`yt_dlp.YoutubeDL`) y corre el motor de selección de
  formatos con una respuesta de ejemplo **guardada** (sin internet, ver
  `_EJEMPLO` en `miauki/core/motor.py`): debe devolver calidades con selector y
  contenedor.
- Sale con 0 o 1. El actualizador lo lanza como subproceso con timeout 60 s
  usando **el propio .exe** (en desarrollo, `python app.py --probar-motor ...`).

Si falla: se borra la carpeta, la versión queda en la lista de **malas** (no se
reintenta) y se sigue con la que estaba.

## 4. Activación, reversa y orden

Estado en `%LOCALAPPDATA%\Miauki YT\motor.json`:

```json
{"activa": "2026.08.19", "anterior": null, "malas": [],
 "ultima_comprobacion": "2026-10-20T19:30:00", "origen": "incluida"}
```

- `core/motor.py` es el **único** módulo que importa `yt_dlp`. Todos los demás
  (`analyzer`, `downloader`, `images`, `diagnostico`, `app`) piden el módulo por
  `motor.ytdlp()`. Al pedirlo: si hay una versión activa descargada, se pone su
  carpeta al principio de `sys.path` y se importa; si el `import` falla, se
  aparta esa versión, se marca como mala y se vuelve a la anterior o a la
  embebida, registrándolo.
- La importación sigue siendo **diferida**: nada toca `yt_dlp` al abrir la
  ventana. Por eso, si la comprobación termina antes del primer análisis o
  descarga, la versión nueva se usa en ese mismo momento (no se importó nada
  todavía). Si ya se importó o hay trabajo en curso, se aplica al reiniciar.
- **Nunca se baja de versión** por una fuente remota: solo se acepta una
  versión estrictamente más nueva que la activa (comparación por tuplas
  numéricas). Volver a una anterior es únicamente la **reversa propia**.
- Se guarda la versión anterior que funcionó (`anterior`) y la embebida queda
  como último recurso.

## 5. Cuándo corre

- **En cada inicio**, en un hilo de fondo que arranca cuando la ventana ya está
  creada (no demora la apertura ni el primer análisis).
- Se omite si la última comprobación fue hace **menos de 10 minutos**
  (`MINUTOS_ENTRE_COMPROBACIONES = 10`) o si el interruptor
  "Actualizar automáticamente al abrir" está apagado.
- Una sola comprobación por inicio (bandera en memoria).
- Nunca cambia el motor mientras haya un **análisis** o una **descarga** en
  curso: el estado activo se puede escribir, pero la sesión sigue usando el
  módulo ya importado (es un import de Python: no se puede cambiar en caliente
  sin reiniciar el proceso). El botón manual lo dice claro: "Se usa desde que
  reiniciés Miauki".
- Sin internet, host no permitido, hash incorrecto, tamaño excesivo, ruta
  maliciosa, versión igual o más vieja, versión mala conocida o prueba de humo
  fallida: **se ignora en silencio** (solo log) y se sigue con el motor actual.
  El inicio automático nunca abre una ventana de error.

## 6. Mensajes y errores

- `core/errors.py` gana el código `motor_viejo` para los mensajes reales de
  yt-dlp que piden actualizar ("Confirm you are on the latest version using
  yt-dlp -U", "You are using an outdated version", "unsupported version of
  yt-dlp"). El error muestra "Actualizar motor" al lado, que dispara la misma
  comprobación.
- La tarjeta "Motor de descargas" de Ajustes informa versión en uso, si es la
  incluida o una actualizada, la fecha y hora de la última comprobación y los
  resultados en una región `role="status"`.

## 7. Límites conocidos (documentados, no resueltos)

- **yt-dlp-ejs y runtime de JavaScript**: desde 2025 yt-dlp usa un componente
  aparte (`yt-dlp-ejs`, incluido en el extra `default` de PyPI) más un runtime
  de JavaScript (deno recomendado, también node/bun/QuickJS) para resolver los
  desafíos de YouTube. El `.exe` **no** trae `yt-dlp-ejs` y no empaqueta node.
  En esta PC node está instalado y las pruebas de YouTube dan los mismos
  formatos con y sin node. Si una versión futura de yt-dlp lo exige para
  YouTube, la prueba de humo **no lo detecta** (no usa internet): queda anotado
  en `docs/PENDIENTES.md` para revisarlo con una descarga real tras cada
  actualización mayor.
- La comprobación no se hace en segundo plano mientras la app está abierta
  (solo al inicio y con el botón).
- No hay "Reiniciar ahora": el mutex de instancia única y el cierre con
  confirmación harían el reinicio propio más frágil que útil. Se aplica al
  próximo inicio.
