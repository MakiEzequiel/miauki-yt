# Miauki YT v1.0

Descargador de videos, música e imágenes de internet (YouTube, TikTok, Instagram, Facebook, X y +1800 sitios vía yt-dlp) como aplicación nativa de Windows (.exe de 64 bits).

Backend en Python 3.12 + interfaz HTML/CSS/JS mostrada con pywebview (motor Edge/WebView2).

## Estado

En construcción por fases. Fase 0 (preparación) completada.

## Documentación

- `docs/DECISIONES.md` — decisiones cerradas del proyecto.
- `docs/INVENTARIO_V2.6.md` — qué se reutiliza de la versión anterior.
- `docs/referencia/` — imagen de referencia y capturas de la v2.6.

## Listas de reproducción

Pegá el link de una playlist de YouTube (o YouTube Music) y la app la lista
completa: elegís qué videos bajar (todos vienen marcados), una calidad para
toda la lista (mejor / 1080p / 720p / 480p / solo música) y MIAUK! encola cada
video con su número (`[1/9] Título`). Máximo 100 videos por lista.

Los videos privados, eliminados o no disponibles no cortan la descarga: se
saltean y al final la Cola muestra un resumen con el motivo de cada uno
("5 porque el enlace es privado, 3 porque el video fue eliminado...").
