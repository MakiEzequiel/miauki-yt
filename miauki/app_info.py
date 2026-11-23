# -*- coding: utf-8 -*-
"""ÚNICA fuente de los datos de la app.

Nombre, versión, autor, descripción, lema, año, enlaces y textos legales.
Todo lo demás (Acerca de..., título de ventana, metadatos del .exe, README,
LICENCIAS.txt) lee de acá.
"""

NOMBRE = "Miauki YT"
NOMBRE_EXE = "Miauki YT"          # nombre del .exe que genera PyInstaller
VERSION = "1.0.0"
VERSION_TUPLA = (1, 0, 0, 0)      # PyInstaller pide 4 números
AUTOR = "Maki Ezequiel"
DESCRIPCION = "Descargador de videos y audio para Windows"
LEMA = "Las mejores descargas, siempre \u2665"
ANIO = 2026

# Texto principal de "Acerca de..." (spec-lock, dictado por Maki).
TEXTO_GRACIAS = ("Trasnochado, pensado y elaborado por Maki Ezequiel. "
                 "¡Espero que lo disfrutes mucho!")

# Aviso legal chiquito (spec-lock). Se muestra con contraste AA mínimo.
TEXTO_LEGAL = ("Usá Miauki solo con contenido que tengas derecho a descargar. "
               "Ni Miauki YT ni Maki Ezequiel están afiliados con alguna red "
               "social. Miauki YT es un programa independiente; las marcas y "
               "nombres de las plataformas pertenecen a sus respectivos dueños "
               "y se mencionan solo con fines de compatibilidad.")

# Licencia del programa (decisión Maki 09/11/2026): GPL 3.0 o posterior.
LICENCIA = "GNU GPL 3.0 o posterior"
LICENCIA_URL = "https://www.gnu.org/licenses/gpl-3.0.html"

# Versión en inglés (la interfaz la pide con api.info("en")). Los textos son
# la misma idea, traducida; el español de arriba sigue siendo el original.
DESCRIPCION_EN = "Video and audio downloader for Windows"
TEXTO_GRACIAS_EN = ("Thought out, designed and built late at night by Maki "
                    "Ezequiel. I hope you enjoy it a lot!")
TEXTO_LEGAL_EN = ("Only use Miauki with content you have the right to "
                  "download. Neither Miauki YT nor Maki Ezequiel is "
                  "affiliated with any social network. Miauki YT is an "
                  "independent program; platform brands and names belong to "
                  "their respective owners and are mentioned only for "
                  "compatibility purposes.")
LICENCIA_EN = "GNU GPL 3.0 or later"

# Donación (decisión Maki 09/11/2026). El alias se copia con
# api.copiar_alias: el texto sale de acá, nunca de JavaScript.
TEXTO_APOYO = ("Si disfrutás de Miauki YT, me ayudarías muchísimo con un "
               "pequeño incentivo para seguir desarrollando software libre "
               "y gratuito.")
TEXTO_APOYO_EN = ("If you enjoy Miauki YT, a small tip would help me a lot "
                  "to keep developing free, open software for everyone.")
ALIAS_DONACION = "makiezequiel.naranja"

# Donación en cripto (20/11/2026): dirección USDT en la red Tron (TRC20),
# obtenida del panel de Depósito de Binance. Copiar dirección: ver
# api.copiar_usdt.
USDT_DONACION = "TPQcvumqfVcxWgHHveUSgLy4CVBYsMjZrg"
USDT_DONACION_RED = "Tron (TRC20)"

# Clave corta -> URL. La interfaz NUNCA manda una URL: manda una clave y
# Python la traduce con esta lista blanca (api.abrir_enlace).
ENLACES = {
    "instagram": "https://www.instagram.com/tusrecursosdigitaless/",
    "facebook": "https://www.facebook.com/tusrecursosdigitaless/",
    "paypal": "https://www.paypal.com/paypalme/ezequielgottwald",
}

# Versión de yt-dlp que viaja dentro del .exe (la "incluida"). Se usa como
# respaldo y como base para saber si hay algo más nuevo. Un test comprueba
# que coincida con la librería instalada.
MOTOR_INCLUIDO = "2026.08.19"

# Fuente de actualizaciones de la APP (no del motor). Hoy está vacía:
# Maki indicó dejar el botón listo y conectarlo cuando defina dónde publicar
# las versiones (plan 19/11/2026).
URL_ACTUALIZACIONES_APP = ""

