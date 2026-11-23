<p align="center">
  <a href="README.md">English</a> ·
  <strong><a href="README.es.md">Español</a></strong>
</p>

<p align="center">
  <img src="docs/img/portada-miauki.png" alt="Miauki YT" width="100%">
</p>

<p align="center">
  <b>Miauki YT</b> — el descargador amigable para todos.
  Bajá videos, música, fotos e historias de tus sitios favoritos con una sola app, simple.
</p>

---

## ¿Por qué Miauki?

Miauki nació como un proyecto personal: un descargador que simplemente *funcione*, sin menús llenos de jerga técnica, sin interfaces feas, sin pedirte que seas un experto.

Después me di cuenta de que podía servirle a mucha más gente. Así que lo pulí, lo hice lindo, lo traduje y lo regalé a la comunidad — porque creo que el buen software debería ser **gratis, simple y agradable** para todos: tu abuela, tu vecino, tu profe, vos.

Si lo usás y te gusta, ya es una victoria. Si querés ayudarme a seguir mejorándolo (mejores modelos, sitios nuevos, más funciones), hay una sección de apoyo opcional al final. Cualquier aporte ayuda, pero nada es obligatorio.

## Qué hace

Pegás un link, tocás **Analizar**, y Miauki te muestra el video, la canción, la foto o la historia con sus calidades. Elegís una y se descarga a tu carpeta. Eso es todo.

| Sitio | Contenido |
|---|---|
| **YouTube** | Videos, shorts, playlists, YouTube Music |
| **TikTok** | Videos, fotos (con sesión/cookies) |
| **Instagram** | Posts, reels, historias, highlights |
| **Facebook** | Videos, reels (fotos piden sesión/cookies) |
| **X / Twitter** | Videos, fotos múltiples, NSFW (con cookies) |
| **Snapchat** | Spotlight e historias |
| **Google Imágenes** | Imágenes directas y links de share.google |
| **Otros** | Vimeo, Dailymotion, Reddit, Pinterest, SoundCloud y más (vía yt-dlp) |

## Características

- **Interfaz amigable** en español e inglés (selector en Ajustes).
- **Simple por diseño**: un campo, un botón, resultados claros. Sin conocimientos técnicos.
- **Cola de descargas** con pausar / reanudar / cancelar.
- **Cookies**: archivos `.txt` (Netscape) y `.json`, o elegí navegador (Chrome, Edge, Firefox, Brave, Chromium, Opera, Vivaldi) para contenido que pide sesión.
- **Calidades**: video hasta 4K/8K, música 320, imagen original (según el sitio).
- **Privacidad**: sin telemetría. Todo queda en tu PC.
- Ventana inicial 1420×840, redimensionable.

## Descargar

| Versión | Descarga | SHA-256 |
|---|---|---|
| **v1.0.0** | [Miauki.YT.v1.0.0.exe](https://github.com/MakiEzequiel/miauki-yt/releases/download/v1.0.0/Miauki.YT.v1.0.0.exe) | `2f976c8aa1c80d9677348d157734908eb9dbc034e0fcc84449d1d621c3bc9503` |
| **v1.0.0 (ZIP completo)** | [Miauki.YT.v1.0.0.-.Windows.zip](https://github.com/MakiEzequiel/miauki-yt/releases/download/v1.0.0/Miauki.YT.v1.0.0.-.Windows.zip) | `c47465d28c81f317a14e9f32db66e7106db88a981a3ddab9fe23d074240dd818` |

> Windows SmartScreen puede avisar al abrir el `.exe` por primera vez: es normal en programas sin certificado de firma. Elegí "Más información → Ejecutar de todas formas".

El `.exe` es completamente autónomo (lleva adentro ffmpeg, yt-dlp y la interfaz). No requiere instalación.

## Requisitos

- Windows 10/11 (con WebView2 Runtime; Miauki lo instala solo si falta).
- Para `--selftest` o correr desde código: Python 3.11+.

## Desde el código

```bash
pip install -r requirements.txt
python app.py            # abre la app
python app.py --selftest # verifica ffmpeg, yt-dlp, WebView2 e interfaz
python -m pytest         # suite de pruebas
```

## Documentación

- `docs/DECISIONES.md` — decisiones de diseño y arquitectura.
- `docs/PENDIENTES.md` — pendientes y limitaciones conocidas.
- `docs/DISTRIBUCION.md` — cómo se construye el `.exe`.

## Apoyo

Miauki es gratis, de código abierto y sin publicidad. Si te sirve y querés ayudarme a seguir mejorándolo (pagar mejores herramientas de desarrollo, sitios nuevos, traducciones), cualquier aporte es muy agradecido:

- **PayPal**: [paypal.me/ezequielgottwald](https://www.paypal.com/paypalme/ezequielgottwald)
- **Alias bancario (Argentina, Naranja X)**: `makiezequiel.naranja`
- **USDT (Tron TRC20)**: `TPQcvumqfVcxWgHHveUSgLy4CVBYsMjZrg`

Gracias por leer, por usar y por ser parte de este proyecto chiquito. 🐱

## Licencia

MIT — ver [LICENSE](LICENSE). Miauki integra yt-dlp, ffmpeg y otras librerías de terceros (detalle en `docs/LICENCIAS_TERCEROS.md`).

---

**English:** [README.md](README.md)
