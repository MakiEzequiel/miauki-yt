# -*- coding: utf-8 -*-
"""Errores propios con mensajes amables en español rioplatense.

Un solo lugar para: (1) los códigos y sus mensajes (lo que ve el usuario),
(2) el mapeo de los mensajes REALES de yt-dlp a esos códigos (A4), y
(3) sin_query() para no guardar URLs con query en el log.
"""
import re

MENSAJES = {
    # Los 12 de la spec §2
    "link_invalido": "Ese link no parece válido. Copiá y pegálo de nuevo.",
    "sitio_no_soportado": "Ese sitio todavía no lo soportamos.",
    "video_privado": "Ese video es privado: su autor no lo deja ver a nadie más.",
    "video_eliminado": "Ese video ya no existe: lo borraron o el link está viejo.",
    "requiere_sesion": "Ese contenido pide iniciar sesión en el sitio para verlo. Activá «Usar el inicio de sesión de tu navegador» en Ajustes.",
    "restriccion_edad": "Ese video tiene restricción de edad.",
    "no_disponible_pais": "Ese video no se puede ver desde tu país.",
    "sin_internet": "No hay conexión a internet. Revisá tu red y probá de nuevo.",
    "tiempo_agotado": "El sitio tardó demasiado en responder. Probá de nuevo en unos segundos.",
    "sin_subtitulos": "Ese video no tiene subtítulos.",
    "calidad_no_disponible": "Esa calidad no está disponible para este video.",
    "error_desconocido": "No pudimos analizar ese link. Pasó algo inesperado; el detalle quedó en el registro (Ajustes > Registro).",
    # De la spec §3 (detección de sitios)
    "lista_reproduccion": "Ese link es una lista de reproducción. Mandame el link de un video suelto.",
    # Playlists (plan de playlists)
    "playlist_muy_larga": "Esa lista tiene demasiados videos (máx. 600).",
    "playlist_sin_entradas": "La lista está vacía o no hay videos disponibles.",
    "playlist_error_analisis": "Algunos videos de la lista no pudieron analizarse.",
    "playlist_sin_id": ("Ese link de lista está incompleto: no trae el código de la lista. "
                        "Abrí la lista en YouTube y copiá el link completo."),
    "playlist_mix_no_visible": ("Ese link es una lista automática de YouTube (un Mix) que no se "
                                 "puede descargar. Pegá el link de una playlist normal o de un "
                                 "video suelto."),
    "no_es_video": "Ese link no es de un video.",
    # Operación (A3): un análisis a la vez
    "analisis_en_curso": "Todavía estoy terminando el análisis anterior. Probá de nuevo en unos segundos.",
    # Cola (Fase 4, decisión 3d.9)
    "cola_llena": "La cola está llena: ya hay 10 descargas esperando. Esperá a que se libere un lugar.",
    # Puente de la cola (Fase 4, decisión 3d.12)
    "entrada_invalida": "Esa descarga llegó incompleta desde la interfaz. Volvé a analizar el link e intentá de nuevo.",
    # Historial (Fase 6)
    "historial_no_encontrado": "Esa descarga ya no está en el historial.",
    "archivo_no_encontrado": "El archivo ya no está en esa carpeta.",
    # Acerca de (Fase 5C)
    "licencias_faltan": "No encontramos el archivo de licencias. Reinstalá Miauki YT para recuperarlo.",
    # Motor viejo (Fase 7, A3): yt-dlp avisa que hay que actualizarlo
    "motor_viejo": "YouTube cambió algo y la versión del motor quedó vieja. Tocá «Actualizar motor» y probá de nuevo.",
    # Verificación anti-bot de YouTube (tanda 20/11/2026, paso 5): NO es falta
    # de sesión; el reintento automático ya se intentó antes de llegar acá.
    "youtube_verificacion_bot": ("YouTube está pidiendo confirmar que no sos un robot. "
                                 "Esperá un minuto y probá de nuevo."),
    # Bloqueo del sitio (auditoría 23/11): HTTP 403/429 de cualquier sitio
    # (TikTok, Snapchat, etc.) NO es falta de internet; es un bloqueo temporal.
    "bloqueo_sitio": ("El sitio bloqueó temporalmente las consultas desde tu "
                       "conexión (verificación anti-bot). Esperá unos minutos e "
                       "intentá de nuevo."),
    # JavaScript para YouTube (Fase 8, 0.6): ver docs/JS_YOUTUBE.md
    "motor_sin_js": ("YouTube pidió una comprobación que esta versión no puede resolver sola. "
                     "Probá de nuevo; si sigue igual, tocá «Buscar actualización»."),
    # Cookies del navegador (Fase 9, B2): Chrome/Edge nuevos cifran las cookies
    # y yt-dlp no las puede leer (problema real, no nuestro).
    "cookies_bloqueadas": ("Ese navegador guarda las cookies cifradas y no podemos leerlas. "
                           "Probá con Firefox, o elegí un archivo de cookies en Ajustes."),
    "cookies_no_encontradas": ("No encontramos cookies de ese navegador. Entrá al sitio, "
                               "iniciá sesión y probá de nuevo, o elegí un archivo de "
                               "cookies en Ajustes."),
    # Archivo de cookies propio (Fase 9, B2b).
    "cookies_archivo_faltante": ("El archivo de cookies ya no está en esa ruta. "
                                 "Elegilo otra vez en Ajustes."),
    "cookies_archivo_invalido": ("Ese archivo no sirve como cookies.txt: tiene que ser un "
                                 ".txt exportado en formato Netscape."),
}

# Espera entre reintentos de la verificación anti-bot de YouTube (tanda
# 20/11/2026, paso 5): la usan el analizador y el descargador.
ESPERA_BOT = 3.0

# Segundo nivel de reintento (tanda 22/11/2026, paso 3): si el bloqueo sigue
# después de rotar clientes, se espera cada vez más antes de volver a probar.
ESPERAS_PACIENTES = (5.0, 10.0, 20.0)

# Mapeo de mensajes reales de yt-dlp → código (A4). Orden importa:
# lo específico va primero; lo desconocido cae en error_desconocido.
_REGLAS = [
    # JavaScript para YouTube (Fase 8, 0.6). Mensajes del código de yt-dlp
    # 2026.8.19; el aviso "No supported JavaScript runtime" se capturó en vivo.
    ("no supported javascript runtime", "motor_sin_js"),
    ("signature solving failed", "motor_sin_js"),
    ("n challenge solving failed", "motor_sin_js"),
    ("challenge solver script", "motor_sin_js"),
    # Motor viejo (Fase 7, A3): mensajes reales de yt-dlp (capturados 20/10/2026)
    # "Confirm you are on the latest version using yt-dlp -U" y variantes.
    ("on the latest version using yt-dlp", "motor_viejo"),
    ("you are using an outdated version", "motor_viejo"),
    ("unsupported version of yt-dlp", "motor_viejo"),
    # Verificación anti-bot de YouTube (tanda 20/11/2026, paso 5). Capturado
    # en vivo el 19/11: "Sign in to confirm you're not a bot". Va con código
    # propio, no con requiere_sesion: las cookies del navegador no lo resuelven.
    ("not a bot", "youtube_verificacion_bot"),
    # Otras frases de la página anti-bot / tráfico inusual (ajustes 21/11).
    ("unusual traffic", "youtube_verificacion_bot"),
    ("please complete the captcha", "youtube_verificacion_bot"),
    ("recaptcha", "youtube_verificacion_bot"),
    # Lista automática Mix de YouTube (real 20/11/2026): YouTube no la expone
    # para descargar ("This playlist type is unviewable.").
    ("playlist type is unviewable", "playlist_mix_no_visible"),
    # Navegador con las cookies cifradas (Fase 9, B2): capturado en vivo con
    # Edge en esta PC ("Failed to decrypt with DPAPI", yt-dlp issue 10927).
    ("failed to decrypt with dpapi", "cookies_bloqueadas"),
    ("does not look like a netscape format cookies file", "cookies_archivo_invalido"),
    ("could not find firefox cookies database", "cookies_no_encontradas"),
    ("could not find chrome cookies database", "cookies_no_encontradas"),
    ("could not find edge cookies database", "cookies_no_encontradas"),
    # Facebook: el extractor no puede leer los datos sin sesión (P0.5).
    ("cannot parse data", "requiere_sesion"),
    # Pinterest: el extractor solo busca video (Paso 4). La vía de imagen
    # (og:image) se intenta antes de informar este código.
    ("no video formats found", "no_es_video"),
    # Reddit: pide autenticación incluso en posts públicos (Paso 4). La vía
    # del JSON público se intenta antes; si no alcanza, este mensaje apunta
    # a las cookies.
    ("account authentication is required", "requiere_sesion"),
    # Instagram sin sesión (capturado en vivo 23/10/2026): el extractor avisa
    # "Instagram sent an empty media response ... use --cookies".
    ("instagram sent an empty media response", "requiere_sesion"),
    # Instagram Stories: los dos mensajes que lanza InstagramStoryIE (leídos en
    # el extractor de yt-dlp 2026.8.19: raise_login_required).
    ("you need to log in to access this content", "requiere_sesion"),
    # Contenido que pide sesión (ajustes 21/11): NO es un video eliminado.
    ("members only", "requiere_sesion"),
    ("sign in to watch", "requiere_sesion"),
    ("this content is unreachable", "video_eliminado"),
    ("confirm your age", "restriccion_edad"),
    ("age-restricted", "restriccion_edad"),
    ("age restricted", "restriccion_edad"),
    ("private", "video_privado"),
    ("not available in your country", "no_disponible_pais"),
    ("made this video available in your country", "no_disponible_pais"),
    # Eliminados REALES (ajustes 21/11): frases específicas antes del genérico
    # "video unavailable", que también aparece en bloqueos pasajeros.
    ("removed by the uploader", "video_eliminado"),
    ("has been removed", "video_eliminado"),
    ("deleted video", "video_eliminado"),
    ("video unavailable", "video_eliminado"),
    ("video is unavailable", "video_eliminado"),
    ("requested format is not available", "calidad_no_disponible"),
    ("no subtitles", "sin_subtitulos"),
    # Capturado en B9: yt-dlp para un link de imagen de Twitter
    ("is not a video", "no_es_video"),
    ("timed out", "tiempo_agotado"),
    ("timeout", "tiempo_agotado"),
    ("try again later", "tiempo_agotado"),
    # Estados HTTP reales (auditoría 23/11): un 404/410 es contenido que ya no
    # existe; un 401 es sesión; un 403/429 es bloqueo temporal. Antes caían en
    # "sin_internet" por el fragmento genérico "unable to download webpage".
    ("http error 404", "video_eliminado"),
    ("http error 410", "video_eliminado"),
    ("http error 401", "requiere_sesion"),
    ("http error 403", "bloqueo_sitio"),
    ("http error 429", "bloqueo_sitio"),
    ("urlopen error", "sin_internet"),
    ("getaddrinfo failed", "sin_internet"),
    ("connection refused", "sin_internet"),
    ("network is unreachable", "sin_internet"),
    ("no route to host", "sin_internet"),
    ("unable to download webpage", "sin_internet"),
    ("unsupported url", "sitio_no_soportado"),
    ("no suitable extractor", "sitio_no_soportado"),
]


class ErrorMiauki(Exception):
    """Error nuestro: código (log/tests) + mensaje amable (UI).

    `mensaje` es opcional: si el caso tiene un mensaje propio más preciso
    que el genérico del código, se usa ese (siempre amable y en español).
    """

    def __init__(self, codigo: str, mensaje: str | None = None):
        self.codigo = codigo
        self.mensaje = mensaje or MENSAJES[codigo]
        super().__init__(self.mensaje)


def codigo_de(mensaje: str) -> str:
    """Mapea el mensaje real de yt-dlp (o del error que sea) a nuestro código."""
    t = (mensaje or "").lower()
    for fragmento, codigo in _REGLAS:
        if fragmento in t:
            return codigo
    return "error_desconocido"


def sin_query(texto: str) -> str:
    """Quita la parte ?query de las URLs, para loguear sin parámetros sensibles."""
    return re.sub(r"\?\S+", "", texto or "")
