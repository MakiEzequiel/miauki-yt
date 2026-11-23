# Distribución de Miauki YT v1.0 (Fase 5C, C2)

Fecha: 20/10/2026. **Solo diseño y datos verificados: no se cambió el build.**
Todo lo que dice "verificado" se consultó ese día en la fuente que se cita.

---

## 1. Onefile o carpeta

Hoy el build es **`--onefile`**: un solo `.exe` de ~… MB que al abrirse se descomprime
en `%TEMP%\_MEIxxxx` y arranca. Ventajas: es un archivo, fácil de mandar por WhatsApp.
Costos reales:

| | Onefile (hoy) | Carpeta (`--onedir`) |
|---|---|---|
| Archivos a entregar | 1 `.exe` | 1 carpeta con ~40 archivos |
| Arranque en frío | 2–6 s (descomprime cada vez) | <1 s |
| Antivirus | **más falsos positivos** (un `.exe` que se autoextrae y ejecuta otro `.exe`) | menos sospechoso |
| Actualizar | reemplazar 1 archivo | reemplazar la carpeta |
| Si el usuario lo copia mal | poco probable | puede romper la carpeta |
| Firma de código | 1 firma | 1 firma (el `.exe`) |

**Recomendación:** para vender, **carpeta comprimida en `.zip`** (más rápido, menos
falsos positivos) **y además un instalador** (ver §2). El onefile queda para la versión
"portable" de prueba. No es una decisión cerrada: es la propuesta.

## 2. Instalador o ZIP

- **ZIP**: cero código nuevo, cero dependencias, el usuario descomprime y ejecuta.
  Malo para el usuario no técnico (no queda en el menú Inicio, no hay desinstalador).
- **Instalador**: Inno Setup (gratis, licencia permisiva, ~5 MB) o WiX (MSI, más
  burocrático). Inno Setup alcanza: crea acceso directo, instala en
  `%LOCALAPPDATA%\Programs\Miauki YT`, copia `LICENCIAS.txt` al lado del `.exe`,
  desinstala limpio y **no pide administrador**.
- **Recomendación:** Inno Setup, instalación por usuario (sin UAC), y el ZIP como
  alternativa portable. Ninguno se implementó todavía.

## 3. Falsos positivos de antivirus con PyInstaller

Es un problema conocido y **no significa que la app tenga un virus**: los antivirus
marcan empaquetadores (PyInstaller, py2exe, NSIS) porque los usan también programas
maliciosos. Qué lo reduce, en orden de impacto:

1. **Firmar el `.exe`** (ver §4): es lo que más baja los falsos positivos.
2. **`--onedir` en vez de `--onefile`**: menos "autoextraíble".
3. Metadatos completos (ya están: nombre, versión, autor, descripción).
4. **No empaquetar binarios raros**: hoy solo `ffmpeg.exe`, que es de gyan.dev y muy
   conocido; los AV no suelen marcarlo.
5. Enviar el `.exe` a **Microsoft (Microsoft Defender → Submit a file)** y a los AV que
   lo marquen (Avast, Kaspersky, ESET tienen formularios de "falso positivo").
6. Publicar el SHA-256 del archivo en la página de descarga: el comprador puede
   verificarlo.

El paquete se arma con `tools/build_exe.py` y `tools/armar_entrega.py` (este último
avisa si el `.exe` no tiene la misma interfaz que el repo). Junto al `.zip` queda
`Entrega/Miauki YT v1.0.0 - SHA-256.txt` con el hash del `.zip` y del `.exe`.

**Aviso honesto:** aunque esté firmado, las primeras semanas algún AV puede marcarlo.
Se resuelve reportando el falso positivo, no "comprando" una reputación.

## 4. SmartScreen y firma de código: costos reales

### Qué pasa hoy sin firmar

Al ejecutar el `.exe` en un Windows 10/11 actualizado, SmartScreen muestra
"Windows protegió tu PC" con **"Ejecutar de todas formas"** escondido en "Más
información". La reputación se construye por archivo y por certificado; un programa
nuevo con pocas descargas **queda en rojo durante mucho tiempo**. Para vender, esto
espanta compradores.

### Opciones verificadas (20/10/2026)

| Opción | Costo | ¿Sirve para Maki (Argentina, persona física)? |
|---|---|---|
| **Azure Trusted Signing (Basic)** | **USD 9,99/mes**, 5.000 firmas incluidas, extra USD 0,005 por firma (precio oficial de la API de precios de Azure) | **NO**: la validación de identidad "Public Trust" para personas individuales **solo admite residentes de EE.UU. o Canadá** (requisito de Microsoft, verificado en la guía de inicio) |
| **Certificado OV (Organization Validation)** de una CA (Sectigo, DigiCert, SSL.com, Certum…) | No publican precio en la web: **hay que pedir cotización**. Referencia de mercado: cientos de dólares por año | Sí, si la CA acepta **persona física / monotributista**; algunas piden CUIT y datos de la actividad |
| **Certificado EV (Extended Validation)** | Más caro que OV (misma lógica: cotización) | Igual que OV, con más papeles |
| **Sin firma** | USD 0 | Sí, con el cartel de SmartScreen |
| **SignPath / firmas gratuitas** | Gratis | Solo para proyectos **open source**; Miauki es propietario |

**Dato clave desde junio de 2023:** las CA ya no entregan la clave privada en un archivo;
va en un **token USB FIPS 140-2** (se envía por correo, tarda y suma costos de envío a
Argentina) o en un **HSM en la nube** (más barato de operar, cobrado por mes). Esto
cambia el costo real: no es solo el certificado, es el token o el HSM.

**Lo que la firma garantiza y lo que no:**

- Garantiza que el archivo lo firmó el dueño del certificado y que no se modificó.
- **No garantiza** que SmartScreen lo deje pasar la primera vez: la reputación igual se
  construye. Un certificado nuevo arranca sin reputación. EV históricamente daba
  reputación inmediata, pero Microsoft **no lo garantiza por escrito**.

**Recomendación práctica para v1.0:** lanzar **sin firmar**, avisar en la página de
compra cómo pasar SmartScreen ("Más información → Ejecutar de todas formas"), publicar
el SHA-256, y **cotizar un OV a nombre propio** cuando haya ventas que lo justifiquen.
No comprar EV de entrada: el retorno no está probado y el costo es alto.

## 5. Instalación en un Windows 10 limpio (sin WebView2)

- Windows 11 ya trae WebView2; **Windows 10 no** (depende de si Edge/Office lo
  instalaron antes). Sin WebView2 la app no puede mostrar la interfaz.
- La app ya detecta si falta y ofrece instalar el **bootstrapper oficial de Microsoft**
  (`Evergreen Bootstrapper`). Ese instalador **necesita internet**.
- **Caso sin internet**: no hay forma de instalar WebView2 sin conexión salvo llevar el
  instalador offline (`Evergreen Standalone Installer`, ~130 MB) en el mismo ZIP. Para
  v1.0: documentar "hace falta internet la primera vez" y, si se quiere cubrir el caso,
  agregar el standalone como archivo aparte en la página de descarga.
- La app verifica la **firma Authenticode** del instalador antes de ejecutarlo (ya
  implementado en `core/webview2.py`); así no se instala cualquier cosa que se llame
  igual.

## 6. Riesgo comercial: logos de YouTube, TikTok, Instagram, Facebook y X

El banner y los íconos usan los logos de esas plataformas. Qué conviene saber:

- Los logos son **marcas registradas** de cada empresa. Usarlos para *identificar* el
  servicio ("descarga desde YouTube") suele considerarse uso nominativo, pero **usarlos
  en el arte principal del producto** (banner, ícono, capturas de venta) puede leerse
  como sugerir afiliación o respaldo.
- La app ya aclara en Ajustes → Acerca: "Miauki YT no está afiliado a YouTube, TikTok,
  Instagram, Facebook ni X". Esa aclaración ayuda, no blinda.
- Riesgo realista: una queja (takedown) de una plataforma, no una demanda. Lo peor que
  pasa es que haya que sacar el logo.
- **Qué haría un abogado, en general** (esto no es asesoramiento legal): evitar los
  logos en el ícono y en el nombre del producto, mantenerlos solo como referencia
  chica, y usar la aclaración de no afiliación visible. **Consultá a un profesional
  antes de vender**: acá solo se describe el riesgo, no se resuelve.
- Nota técnica: el ícono de Instagram que se usa viene de **Simple Icons (CC0 1.0)**,
  que libera el *dibujo*, no la marca.

## 7. Qué falta para poder vender (resumen)

| Punto | Estado |
|---|---|
| `LICENCIAS.txt` completo (GPLv3, OFL, etc.) | **Hecho** (A5) y el build falla si falta |
| Oferta de código fuente de FFmpeg | **Hecha** (en `LICENCIAS.txt`) |
| Instalador / ZIP | Falta (propuesta: Inno Setup + ZIP portable) |
| Firma de código | Falta (propuesta: lanzar sin firmar; cotizar OV) |
| Prueba en Windows 10 limpio | Falta (Fase 9) |
| Página de descarga con SHA-256 y pasos de SmartScreen | Falta |
| Revisión de marcas por un profesional | Falta (recomendada antes de publicar) |
