# Archivo de cookies: qué es y cómo se saca del navegador

Documento de la Fase 9 (B2b). Se lee en dos minutos y no hace falta saber nada
de programación.

## Para qué sirve

Algunos videos (sobre todo de X/Twitter, Instagram o YouTube con restricción de
edad) piden **estar con la sesión iniciada**. Miauki puede pedirle las cookies
al navegador, pero Chrome y Edge nuevas las guardan **cifradas** y a veces no se
pueden leer (error DPAPI, problema del motor yt-dlp, no de Miauki).

La alternativa es un **archivo de cookies**: un `.txt` que exporta el navegador
con las cookies de los sitios donde tenés sesión. Miauki lo lee, usa lo que
necesita y **solo guarda la ruta del archivo** (no lo copia).

## Antes de empezar: el archivo es una llave

El archivo permite entrar a tus cuentas sin contraseña. **No lo compartas, no lo
subas a ningún lado y no lo dejes en una carpeta sincronizada** (OneDrive,
Google Drive, Dropbox). Cuando ya no lo necesites, borralo y tocá "Quitar" en
Ajustes.

## Cómo exportarlo

La forma oficial que documenta yt-dlp (FAQ, "How do I pass cookies to yt-dlp")
es una extensión del navegador que exporta en formato Netscape:

- **Chrome / Edge / Brave**: extensión **"Get cookies.txt LOCALLY"**.
  Es la que dice *LOCALLY*. La vieja "Get cookies.txt" (sin LOCALLY) fue
  reportada como malware y la sacaron de la tienda: no la instales.
  Link: https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
- **Firefox**: extensión **"cookies.txt"**.
  Link: https://addons.mozilla.org/firefox/addon/cookies-txt/

Pasos con la extensión:

1. Entrá al sitio y **asegurate de estar con la sesión iniciada** (por ejemplo,
   abrí `x.com` y mirá que aparezca tu cuenta).
2. Tocá el ícono de la extensión.
3. Elegí "Export" / "Exportar" para **ese sitio** (no "todas las cookies": solo
   las que correspondan).
4. Guardá el archivo en una carpeta tuya, por ejemplo
   `C:\Users\TuUsuario\Documents\cookies\x.txt`.
5. En Miauki: **Ajustes → Usar el inicio de sesión de tu navegador →
   "Elegir archivo…"** y seleccioná ese `.txt`.

## Qué revisa Miauki antes de aceptarlo

- que el archivo exista y termine en `.txt`;
- que pese algo razonable (ni vacío ni más de 5 MB);
- que tenga el formato Netscape: primera línea `# Netscape HTTP Cookie File`
  (o `# HTTP Cookie File`) y al menos una cookie adentro.

Si algo falla, el aviso dice qué pasó y el archivo no se guarda. El chequeo usa
`http.cookiejar`, la biblioteca estándar de Python: no se instaló nada nuevo.

## Si el video sigue pidiendo sesión

- Las cookies vencen: volvé a exportar el archivo.
- En Windows el archivo tiene que usar saltos de línea **CRLF**. La extensión ya
  lo hace; si lo editaste a mano, guardalo con el Bloc de notas.
- Exportá solo el sitio que te interesa; un archivo con todas las cookies de
  todos los sitios es más peligroso y no ayuda más.

## Notas técnicas (para quien programe)

- El ajuste `archivo_cookies` guarda la ruta; si está vacío se usa
  `navegador_cookies`. El archivo **gana** sobre el navegador.
- `miauki/core/cookies.py` es el único lugar que decide qué cookies se pasan a
  yt-dlp (`cookiefile` / `cookiesfrombrowser`), tanto para analizar como para
  descargar, y cuáles se leen para las vías de imágenes de X (solo dominios
  `x.com` y `twitter.com`, en memoria).
- Los valores de las cookies nunca van al log, al diagnóstico, a los fixtures ni
  a los tests.
