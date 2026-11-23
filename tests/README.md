# Pruebas

Correr: `python -m unittest discover -s tests`

Cubierto hoy (Fase 1): rutas (portable/LOCALAPPDATA, interfaz externa/embebida), puente `api.py` (`{ok, data|error}`, sin excepciones a la interfaz) y verificación del ffmpeg (existencia + SHA-256).

Pendiente (Fases 3-4): selección de calidades, máquina de estados de la cola (incluida la pausa), limpieza del historial y detección de URLs.
