# Scripts de build y de prueba

- `verify_ffmpeg.py` — verifica `miauki/bin/ffmpeg.exe` (usa el hash canónico de `miauki/core/ffmpeg_tools.py`, documentado en `docs/DEPENDENCIAS.md`).
- `build_exe.py` — genera `dist/Miauki YT.exe`: **primero verifica el ffmpeg y se detiene si falla**, después corre PyInstaller onefile con ícono y metadatos de `app_info.py`.

```
python tools/verify_ffmpeg.py     # solo verifica
python tools/build_exe.py         # verifica + empaqueta
```

El `--selftest` de la app (`python app.py --selftest` o `dist\Miauki YT.exe --selftest`) incluye la misma verificación del ffmpeg.


## Carpeta de datos en pruebas y herramientas

Ninguna herramienta de esta carpeta debe escribir en la carpeta real del usuario
(`%LOCALAPPDATA%\Miauki YT`). Alcanza con importar `_entorno` arriba de todo
(después del `sys.path.insert`):

```python
import _entorno  # apunta MIAUKI_DATOS a %TEMP%\miauki-herramientas\<script>
```

`miauki/paths.py` respeta `MIAUKI_DATOS` (ruta absoluta) antes que la carpeta
portable y que `%LOCALAPPDATA%`. Los tests lo hacen solos: cada `test_*.py`
importa `tests/apoyo.py`, que crea una carpeta temporal por corrida, y
`test_zz_datos_reales.py` falla si algo tocó la carpeta real.
