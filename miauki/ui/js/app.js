// Punto de entrada de la interfaz (Fases 2, 3B y 4B).
// Barra lateral: selección visual de la sección y contador de la Cola.
// Textos (strings.es.js): aplica las claves data-str / data-str-ph / data-str-aria.
// Paso 1: campo de link (botón X, Pegar) y el análisis real (Fase 3B).
// Paso 2: tarjeta de video (vacío / skeleton / listo; modo imagen con cuadrícula).
// Paso 3: segmentados accesibles (flechas), "Más opciones" y el panel de info
//         con los datos REALES del análisis (Fase 3B).
// Columna derecha: panel "Guardar en" con la ruta real de los ajustes y el
//         interruptor de subtítulos sincronizado con settings (cambiar_ajuste).
// Fase 4B: MIAUK! encola el snapshot (agregar_descarga) y los eventos
//         cola/progreso de Python mueven la insignia y guardan el progreso.
// Seguridad: los datos del análisis entran SOLO por textContent/atributos,
// nunca por marcado crudo; la miniatura y las fotos se muestran solo si son
// data:image/ (CSP de index.html).

(function () {
  "use strict";

  var SITIOS = {
    youtube: "YouTube",
    instagram: "Instagram",
    facebook: "Facebook",
    x: "X",
    tiktok: "TikTok",
  };

  var resultado = null; // último análisis OK (contrato de api.analizar)
  var enAnalisis = false;
  var nLanzamiento = 0; // para descartar respuestas viejas (§7)
  var tipoActual = "video";
  var ajustes = { incluir_subs: true, carpeta_descargas: "" };

  function str(clave) {
    return (window.MiaukiSTR || {})[clave] || "";
  }

  function formatearDuracion(segundos) {
    if (typeof segundos !== "number" || segundos < 0) return "—";
    var s = Math.round(segundos);
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var r = s % 60;
    var mm = h ? (m < 10 ? "0" + m : String(m)) : String(m);
    var ss = r < 10 ? "0" + r : String(r);
    return (h ? h + ":" : "") + mm + ":" + ss;
  }

  // Formato de números de Argentina: coma decimal y punto de miles.
  // ÚNICA función de la interfaz para números (decisión Maki, Fase 5): todo
  // (%, velocidades, tamaños, peso total) pasa por acá. null/no-número → "—".
  function formatearNumero(valor, decimales) {
    if (typeof valor !== "number" || !isFinite(valor)) return "—";
    var dec = decimales > 0 ? Math.floor(decimales) : 0;
    var partes = Math.abs(valor).toFixed(dec).split(".");
    partes[0] = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return (valor < 0 ? "-" : "") + partes[0] + (dec > 0 ? "," + partes[1] : "");
  }

  function formatearBytes(bytes, aprox) {
    if (typeof bytes !== "number" || !isFinite(bytes) || bytes < 0) return "—";
    var u = ["B", "KB", "MB", "GB"];
    var i = 0;
    var v = bytes;
    while (v >= 1024 && i < u.length - 1) {
      v /= 1024;
      i += 1;
    }
    var n = formatearNumero(v, v >= 10 || i === 0 ? 0 : 1);
    return (aprox ? "~" : "") + n + " " + u[i];
  }

  function nombreSitio(sitio) {
    if (SITIOS[sitio]) return SITIOS[sitio];
    // "otro" (o vacío) nunca se muestra tal cual.
    return sitio && sitio !== "otro" ? sitio : str("historial.sitioWeb");
  }

  // Navegación (Fase 4C Parte B, porción 1): muestra la pantalla del ítem.
  // Inicio conserva su DOM tal cual (no se re-renderiza) y es la única con la
  // columna derecha "Guardar en"; el resto la ocultan.
  var PANTALLAS = ["inicio", "playlist", "cola", "historial", "ajustes", "acerca"];

  function mostrarPantalla(nombre) {
    if (PANTALLAS.indexOf(nombre) < 0) nombre = "inicio";
    document.querySelectorAll("[data-pantalla]").forEach(function (el) {
      el.hidden = el.getAttribute("data-pantalla") !== nombre;
    });
    var app = document.getElementById("app");
    if (app) app.classList.toggle("sin-derecha", nombre !== "inicio");
    document.querySelectorAll(".nav-item").forEach(function (it) {
      if (it.getAttribute("data-pantalla") === nombre) it.setAttribute("aria-current", "page");
      else it.removeAttribute("aria-current");
    });
    // El foco va al titular: el lector de pantalla anuncia el cambio de sección.
    var h1 = document.querySelector('h1[data-pantalla="' + nombre + '"], [data-pantalla="' + nombre + '"] .pantalla-titulo');
    if (h1) h1.focus();
    if (nombre === "historial") cargarHistorial();
    return nombre;
  }

  function seleccionar(item) {
    mostrarPantalla(item.getAttribute("data-pantalla") || "inicio");
  }

  // Reemplaza cada marcador del HTML por su texto de strings.es.js.
  // Ojo: aria-label NO es propiedad DOM con guion (el["aria-label"] no refleja
  // el atributo); hay que usar setAttribute, si no el nombre accesible queda vacío.
  function aplicarTextos() {
    var marcas = [
      ["data-str", "textContent", null],
      ["data-str-ph", "placeholder", null],
      ["data-str-aria", null, "aria-label"],
      ["data-str-title", null, "title"],
      ["data-str-alt", null, "alt"],
    ];
    marcas.forEach(function (par) {
      document.querySelectorAll("[" + par[0] + "]").forEach(function (el) {
        var valor = str(el.getAttribute(par[0]));
        if (!valor) return;
        if (par[2]) el.setAttribute(par[2], valor);
        else el[par[1]] = valor;
      });
    });
  }

  // PASO 2: estados de la tarjeta de video (vacío / skeleton / listo).
  function mostrarVideoEstado(estado) {
    var zona = document.querySelector(".video-zona");
    if (zona) zona.setAttribute("data-estado-video", estado);
  }

  function limpiarVideo() {
    var mini = document.querySelector(".video-mini");
    var titulo = document.querySelector(".video-titulo");
    var meta = document.querySelector(".video-meta");
    var cuadricula = document.querySelector("[data-img-cuadricula]");
    var cantidad = document.querySelector("[data-img-cantidad]");
    if (mini) {
      mini.hidden = false;
      mini.removeAttribute("src");
      mini.alt = "";
    }
    if (titulo) {
      titulo.textContent = "";
      titulo.removeAttribute("title");
    }
    if (meta) {
      // Solo los spans con datos; el "·" (aria-hidden) se conserva.
      meta.querySelectorAll("span:not([aria-hidden])").forEach(function (s) {
        s.textContent = "";
      });
    }
    if (cuadricula) {
      cuadricula.hidden = true;
      cuadricula.textContent = "";
    }
    if (cantidad) cantidad.hidden = true;
    // El × de la vista previa (paso 5) oculta la tarjeta solo en la sesion:
    // cada analisis nuevo la vuelve a mostrar (decision de Maki).
    var tarjeta = document.querySelector(".video-listo");
    if (tarjeta) tarjeta.hidden = false;
  }

  // Un solo render por tarjeta (§7): todo lo que pone datos del análisis pasa
  // por textContent o atributos, nunca por marcado crudo.
  function renderVideo(data) {
    limpiarVideo();
    var esImagen = data.tipo === "imagen";
    var mini = document.querySelector(".video-mini");
    var info = document.querySelector(".video-info");
    var cuadricula = document.querySelector("[data-img-cuadricula]");
    var cantidad = document.querySelector("[data-img-cantidad]");

    var titulo = document.querySelector(".video-titulo");
    if (titulo) {
      titulo.textContent = data.titulo || "";
      // Decisión Maki 15/10/2026: 1 línea con "…" y el título completo en el tooltip.
      titulo.title = data.titulo || "";
    }

    var meta = document.querySelector(".video-meta");
    if (meta) {
      var partes = meta.querySelectorAll("span");
      if (partes[0]) partes[0].textContent = nombreSitio(data.sitio);
      if (partes.length > 1) partes[partes.length - 1].textContent =
        formatearDuracion(data.duracion);
      meta.hidden = esImagen;
    }

    if (esImagen) {
      if (mini) mini.hidden = true;
      if (info) info.hidden = true;
      if (cuadricula) {
        cuadricula.hidden = false;
        cuadricula.textContent = "";
        (data.imagenes || []).forEach(function (uri) {
          // Solo data:image/: la URL no se toca nunca (CSP + §7).
          if (typeof uri !== "string" || uri.indexOf("data:image/") !== 0) return;
          var img = document.createElement("img");
          img.alt = "";
          img.src = uri;
          cuadricula.appendChild(img);
        });
      }
      if (cantidad) {
        var n = (data.imagenes || []).length;
        cantidad.textContent = n + " " + str(n === 1 ? "paso2.foto" : "paso2.fotos");
        cantidad.hidden = false;
      }
    } else {
      if (mini) {
        if (data.miniatura && String(data.miniatura).indexOf("data:image/") === 0) {
          mini.src = data.miniatura;
        }
        mini.hidden = !mini.getAttribute("src");
      }
      if (info) info.hidden = false;
      if (cuadricula) cuadricula.hidden = true;
      if (cantidad) cantidad.hidden = true;
    }
  }

  // PASO 3: segmentados (role="radiogroup").
  // Patrón ARIA: un solo radio con tabindex=0 (roving), las flechas mueven
  // el foco Y marcan (como los radio nativos); Home/End van a los extremos.
  function seleccionarRadio(radio) {
    var grupo = radio.closest(".segmentado");
    if (!grupo) return;
    // Sincroniza AMBOS grupos de calidades (principal y "Más opciones").
    // Ambos usan data-calidad con el MISMO índice (índice en resultado.calidades).
    var calidadIdx = radio.getAttribute("data-calidad");
    var gruposCalidad = document.querySelectorAll(
      '[data-str-aria="paso3.grupoCalidad"], #mas-opciones .segmentado'
    );
    gruposCalidad.forEach(function (g) {
      g.querySelectorAll('[role="radio"]').forEach(function (otro) {
        var mismoIndice = otro.getAttribute("data-calidad") === calidadIdx;
        var esEl = otro === radio;
        var marcar = esEl || (calidadIdx !== null && mismoIndice);
        if (marcar) {
          otro.setAttribute("aria-checked", "true");
          otro.tabIndex = 0;
        } else {
          otro.setAttribute("aria-checked", "false");
          otro.tabIndex = -1;
        }
      });
    });
    // Para otros segmentados (tipo, música, foto), comportamiento original.
    if (!calidadIdx) {
      grupo.querySelectorAll('[role="radio"]').forEach(function (otro) {
        var esEl = otro === radio;
        otro.setAttribute("aria-checked", esEl ? "true" : "false");
        otro.tabIndex = esEl ? 0 : -1;
      });
    }
  }

  function iniciarSegmentados() {
    document.querySelectorAll(".segmentado").forEach(function (grupo) {
      grupo.addEventListener("click", function (evento) {
        var radio = evento.target.closest('[role="radio"]');
        if (!radio || radio.disabled) return;
        seleccionarRadio(radio);
        if (radio.hasAttribute("data-tipo")) cambiarTipo(radio.getAttribute("data-tipo"));
        else actualizarInfo();
      });
      grupo.addEventListener("keydown", function (evento) {
        var radios = Array.prototype.slice.call(grupo.querySelectorAll('[role="radio"]'));
        var i = radios.indexOf(document.activeElement);
        if (i < 0) return;
        var destino = -1;
        if (evento.key === "ArrowRight" || evento.key === "ArrowDown") {
          destino = (i + 1) % radios.length;
        } else if (evento.key === "ArrowLeft" || evento.key === "ArrowUp") {
          destino = (i - 1 + radios.length) % radios.length;
        } else if (evento.key === "Home") {
          destino = 0;
        } else if (evento.key === "End") {
          destino = radios.length - 1;
        }
        if (destino >= 0) {
          evento.preventDefault();
          var radio = radios[destino];
          if (radio.disabled) return;
          seleccionarRadio(radio);
          radio.focus();
          if (radio.hasAttribute("data-tipo")) cambiarTipo(radio.getAttribute("data-tipo"));
          else actualizarInfo();
        }
      });
    });
  }

  // Reconstruye un grupo de radios con la información real (§5). Opciones:
  // [{texto, atributo, valor, marcado}] — los atributos personalizados
  // (data-calidad / data-musica / data-foto) identifican la opción elegida.
  function construirRadios(grupo, opciones) {
    grupo.textContent = "";
    opciones.forEach(function (op, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "radio");
      b.setAttribute("aria-checked", op.marcado ? "true" : "false");
      b.tabIndex = op.marcado ? 0 : -1;
      b.textContent = op.texto;
      if (op.atributo) b.setAttribute(op.atributo, String(op.valor));
      grupo.appendChild(b);
    });
  }

  function opcionesGrupoCalidad() {
    if (!resultado) return [];
    if (tipoActual === "musica") {
      return (resultado.musica || []).map(function (m, i) {
        return {
          texto: m.kbps + " kbps",
          atributo: "data-musica",
          valor: i,
          marcado: i === 0,
        };
      });
    }
    if (tipoActual === "imagen") {
      var n = (resultado.imagenes || []).length;
      var ops = [];
      for (var i = 0; i < n; i++) {
        ops.push({
          texto: str("paso3.foto") + " " + (i + 1),
          atributo: "data-foto",
          valor: i,
          marcado: i === 0,
        });
      }
      return ops;
    }
    var recomendadas = (resultado.calidades || []).filter(function (c) { return c.recomendada; });
    var lista = recomendadas.length ? recomendadas : (resultado.calidades || []);
    return lista.map(function (c) {
      var etiqueta = c.etiqueta || (c.resolucion + "p");
      var idx = (resultado.calidades || []).indexOf(c);
      return {
        texto: c.recomendada ? c.recomendada + " · " + etiqueta : etiqueta,
        atributo: "data-calidad",
        valor: idx,
        marcado: idx === 0,
      };
    });
  }

  function pintarGrupoCalidad() {
    var grupo = document.querySelector('[data-str-aria="paso3.grupoCalidad"]');
    if (!grupo) return;
    construirRadios(grupo, opcionesGrupoCalidad());
  }

  function pintarMasOpciones() {
    var panel = document.getElementById("mas-opciones");
    var grupo = panel && panel.querySelector(".segmentado");
    var boton = document.querySelector(".btn-mas");
    if (!panel || !grupo || !boton) return;
    panel.hidden = true;
    boton.setAttribute("aria-expanded", "false");
    var esVideo = tipoActual === "video" && resultado;
    boton.hidden = !esVideo;
    if (!esVideo) {
      grupo.textContent = "";
      return;
    }
    // "Más opciones": TODAS las calidades, de mayor a menor (§5).
    var ordenadas = (resultado.calidades || []).slice().sort(function (a, b) {
      return (b.resolucion || 0) - (a.resolucion || 0);
    });
    var actual = opcionElegida();
    construirRadios(grupo, ordenadas.map(function (c) {
      return {
        texto: c.etiqueta || (c.resolucion + "p"),
        atributo: "data-calidad",
        valor: (resultado.calidades || []).indexOf(c),
        marcado: c === actual,
      };
    }));
  }

  function opcionElegida() {
    if (!resultado) return null;
    // Busca el radio marcado en AMBOS grupos (principal y "Más opciones").
    var radios = document.querySelectorAll(
      '[data-str-aria="paso3.grupoCalidad"] [role="radio"][aria-checked="true"],'
      + ' #mas-opciones .segmentado [role="radio"][aria-checked="true"]'
    );
    var radio = radios[0];
    if (!radio) return null;
    if (radio.hasAttribute("data-musica")) {
      return (resultado.musica || [])[Number(radio.getAttribute("data-musica"))] || null;
    }
    if (radio.hasAttribute("data-foto")) return null; // foto: sin opciones de info
    return (resultado.calidades || [])[Number(radio.getAttribute("data-calidad"))] || null;
  }

  function pintarDato(idDato, claveEtiqueta, valor) {
    var el = document.querySelector('[data-str="paso3.' + idDato + '"]');
    if (el) el.textContent = str(claveEtiqueta) + " " + (valor || "—");
  }

  function actualizarInfo() {
    var opcion = opcionElegida();
    var formato = null;
    var tamano = null;
    var tiempo = null;
    if (tipoActual === "video" && opcion) {
      formato = opcion.contenedor || null;
      tamano = formatearBytes(opcion.peso_bytes, opcion.peso_aprox);
      if (tamano === "—") tamano = null;
      if (resultado && resultado.duracion != null) {
        tiempo = formatearDuracion(resultado.duracion);
      }
    } else if (tipoActual === "musica" && opcion) {
      formato = "mp3";
      tamano = formatearBytes(opcion.peso_bytes, opcion.peso_aprox);
      if (tamano === "—") tamano = null;
    }
    pintarDato("datoFormato", "paso3.etiquetaFormato", formato);
    pintarDato("datoTamano", "paso3.etiquetaTamano", tamano);
    pintarDato("datoTiempo", "paso3.etiquetaTiempo", tiempo);
    // B1: con "Máxima compatibilidad" apagada puede tocar MKV, AV1 o VP9, que
    // el reproductor de Windows no siempre abre. Se avisa sin bloquear.
    var aviso = document.querySelector("[data-aviso-formato]");
    if (aviso) {
      var codec = (opcion && opcion.codec) || "";
      var raro = tipoActual === "video" && opcion &&
        ((opcion.contenedor === "mkv") || codec === "av1" || codec === "vp9");
      aviso.hidden = !raro;
    }
  }

  function pintarTipo() {
    var grupo = document.querySelector('[data-str-aria="paso3.grupoFormato"]');
    if (!grupo) return;
    var tipos = (resultado && resultado.tipos) || [];
    grupo.querySelectorAll("[data-tipo]").forEach(function (radio) {
      var esta = tipos.indexOf(radio.getAttribute("data-tipo")) >= 0;
      radio.disabled = !esta;
      radio.setAttribute("aria-disabled", esta ? "false" : "true");
      radio.tabIndex = esta ? radio.tabIndex : -1;
      if (!esta && radio.getAttribute("aria-checked") === "true") {
        radio.setAttribute("aria-checked", "false");
      }
    });
    // Fase 9, B3: si el post es solo imágenes, se avisa por qué Video y
    // Música están apagados (el dato lo decide el backend en `tipos`).
    var nota = document.querySelector("[data-tipo-nota]");
    if (nota) nota.hidden = !(tipos.length === 1 && tipos[0] === "imagen");
    var elegido = grupo.querySelector('[role="radio"][aria-checked="true"]');
    if (!elegido || elegido.disabled) {
      var primero = grupo.querySelector('[role="radio"]:not([disabled])');
      if (primero) {
        seleccionarRadio(primero);
        tipoActual = primero.getAttribute("data-tipo");
      }
    } else {
      tipoActual = elegido.getAttribute("data-tipo");
    }
  }

  function cambiarTipo(tipo) {
    tipoActual = tipo;
    pintarGrupoCalidad();
    pintarMasOpciones();
    actualizarInfo();
  }

  function renderCalidad(data) {
    pintarTipo();
    pintarGrupoCalidad();
    pintarMasOpciones();
    actualizarInfo();
  }

  // Errores del análisis: role="alert" (el mensaje viene del motor, §7).
  // Si el motor quedó viejo, aparece el botón "Actualizar motor" (Fase 7, A3).
  function mostrarError(mensaje, codigo) {
    var el = document.getElementById("paso1-error");
    if (!el) return;
    // El bloqueo anti-bot de YouTube (tanda 22/11/2026, paso 1) usa el texto
    // de la interfaz, que aclara que el problema es de YouTube y no de la app.
    if (codigo === "youtube_verificacion_bot") {
      mensaje = str("errores.youtubeVerificacionBot");
    }
    el.textContent = mensaje || str("errores.generico");
    el.hidden = false;
    var accion = document.querySelector("[data-error-motor]");
    if (accion) accion.hidden = codigo !== "motor_viejo" && codigo !== "motor_sin_js";
    // Fase 9, B2: si el contenido pide sesión, el atajo lleva a Ajustes.
    var ajustes = document.querySelector("[data-error-ajustes]");
    if (ajustes) {
      ajustes.hidden = ["requiere_sesion", "restriccion_edad", "cookies_bloqueadas",
                        "cookies_no_encontradas", "cookies_archivo_invalido",
                        "cookies_archivo_faltante"].indexOf(codigo) < 0;
    }
  }

  function limpiarError() {
    var el = document.getElementById("paso1-error");
    if (!el) return;
    el.hidden = true;
    el.textContent = "";
    var accion = document.querySelector("[data-error-motor]");
    if (accion) accion.hidden = true;
    var ajustes = document.querySelector("[data-error-ajustes]");
    if (ajustes) ajustes.hidden = true;
  }

  // ---------- Motor de descargas (Fase 7, A3) ----------
  // Un solo camino para el botón de Ajustes, el del error (Inicio) y el de la
  // Cola: estado ocupado con aria-busy, mensaje en la región role="status" y
  // aviso flotante cuando hay algo nuevo.
  var MS_AVISO_MOTOR = 6000;
  var temporizadorMotor = null;

  function avisarMotor(texto) {
    var aviso = document.querySelector("[data-aviso-motor]");
    if (!aviso) return;
    var cuerpo = aviso.querySelector("[data-aviso-motor-texto]");
    if (cuerpo) cuerpo.textContent = texto;
    aviso.hidden = false;
    if (temporizadorMotor) window.clearTimeout(temporizadorMotor);
    temporizadorMotor = window.setTimeout(function () {
      aviso.hidden = true;
      temporizadorMotor = null;
    }, MS_AVISO_MOTOR);
  }

  function textoMotor(resultado) {
    if (!resultado) return str("motor.sinInternet");
    if (resultado.accion === "actualizada") {
      return str(resultado.en_uso_ya ? "motor.actualizadoYa"
                                     : "motor.actualizadoReiniciar")
        .replace("{v}", resultado.version || "");
    }
    if (resultado.accion === "al_dia") return str("motor.alDia");
    return str("motor.sinInternet");
  }

  function buscarMotor(boton, alTerminar) {
    if (boton && boton.getAttribute("aria-busy") === "true") return;
    var textoOriginal = boton ? boton.textContent : "";
    whenReady(function () {
      if (boton) {
        // aria-busy + aria-disabled en vez de disabled: el boton conserva el
        // foco y su contraste mientras busca.
        boton.setAttribute("aria-busy", "true");
        boton.setAttribute("aria-disabled", "true");
        boton.textContent = str("motor.buscando");
      }
      window.pywebview.api.comprobar_motor().then(function (r) {
        if (boton) {
          boton.removeAttribute("aria-busy");
          boton.removeAttribute("aria-disabled");
          boton.textContent = textoOriginal;
        }
        var datos = r && r.ok === true ? r.data : null;
        if (alTerminar) alTerminar(datos);
      })["catch"](function () {
        if (boton) {
          boton.removeAttribute("aria-busy");
          boton.removeAttribute("aria-disabled");
          boton.textContent = textoOriginal;
        }
        if (alTerminar) alTerminar(null);
      });
    });
  }

  function iniciarMotor() {
    var version = document.querySelector("[data-motor-version]");
    var origen = document.querySelector("[data-motor-origen]");
    var ultima = document.querySelector("[data-motor-ultima]");
    var estado = document.querySelector("[data-motor-estado]");
    var boton = document.querySelector("[data-motor-buscar]");

    function pintarEstado(datos) {
      if (!datos) return;
      if (version) version.textContent = datos.version || "";
      if (origen) {
        origen.textContent = datos.origen === "actualizada"
          ? str("motor.versionActualizada")
          : str("motor.versionIncluida");
      }
      if (ultima) {
        ultima.textContent = datos.ultima ? fechaHistorial(datos.ultima)
                                          : str("motor.nunca");
      }
    }

    whenReady(function () {
      window.pywebview.api.estado_motor().then(function (r) {
        if (r && r.ok === true) pintarEstado(r.data);
      });
    });

    if (boton) boton.addEventListener("click", function () {
      buscarMotor(boton, function (datos) {
        var mensaje = textoMotor(datos);
        if (estado) estado.textContent = mensaje;
        if (datos && datos.accion === "actualizada") avisarMotor(str("motor.aviso"));
        // Si se actualizó, la tarjeta muestra la versión nueva.
        whenReady(function () {
          window.pywebview.api.estado_motor().then(function (r) {
            if (r && r.ok === true) pintarEstado(r.data);
          });
        });
      });
    });

    var errorBoton = document.querySelector("[data-error-motor]");
    if (errorBoton) errorBoton.addEventListener("click", function () {
      buscarMotor(errorBoton, function (datos) {
        var mensaje = textoMotor(datos);
        var el = document.getElementById("paso1-error");
        if (el && !el.hidden) el.textContent = mensaje;
        if (datos && datos.accion === "actualizada") avisarMotor(str("motor.aviso"));
      });
    });

    window.MiaukiUI.buscarMotor = buscarMotor;
  }

  function botonAnalizar() {
    return document.querySelector(".btn-analizar");
  }

  function botonMiauk() {
    return document.querySelector("[data-miauk]");
  }

  function estadoBotones(analizando, listo) {
    analisisEnCurso = !!analizando;
    var btn = botonAnalizar();
    if (btn) {
      btn.disabled = analizando;
      if (analizando) btn.setAttribute("aria-busy", "true");
      else btn.removeAttribute("aria-busy");
    }
    var miauk = botonMiauk();
    // MIAUK! se habilita solo con un análisis exitoso (Fase 3B); su clic
    // encola el snapshot elegido (Fase 4 B5).
    if (miauk) miauk.disabled = !listo;
  }

  // ENCÓLADO (Fase 4 B5): el snapshot sale del análisis + lo elegido en
  // la interfaz (tipo, calidad/música/foto, subtítulos). Para imagen se
  // manda la URL REAL de la foto (imagenes_urls, 3d.13); data: no sirve
  // para descargar.
  function construirSnapshot() {
    if (!resultado) return null;
    var base = {
      url_canonica: resultado.url_canonica,
      titulo: resultado.titulo,
      miniatura: resultado.miniatura || "",
      con_subs: false,
    };
    if (tipoActual === "imagen") {
      var radios = document.querySelectorAll('[role="radio"][aria-checked="true"][data-foto]');
      var indice = radios.length ? Number(radios[0].getAttribute("data-foto")) : 0;
      var urls = resultado.imagenes_urls || [];
      var urlFoto = urls[indice];
      if (typeof urlFoto !== "string" || !/^https?:\/\//i.test(urlFoto)) {
        return null;
      }
      base.url_canonica = urlFoto;
      base.tipo = "imagen";
      base.selector = null;
      base.contenedor = null;
      return base;
    }
    var opcion = opcionElegida();
    if (!opcion) return null;
    if (tipoActual === "musica") {
      base.tipo = "musica";
      base.selector = opcion.selector || "bestaudio";
      base.kbps = opcion.kbps;
      base.contenedor = null;
      return base;
    }
    base.tipo = "video";
    base.selector = opcion.selector;
    base.contenedor = opcion.contenedor || null;
    base.kbps = null;
    // P0.5: la resolución permite reanalizar y reintentar si el formato
    // pedido ya no existe (yt-dlp la usa como "height<=N" con respaldos).
    base.resolucion = opcion.resolucion || null;
    // Paso 3: opción "Original" (p.ej. Snapchat) — la URL directa se baja
    // sin yt-dlp (su filtro de seguridad rechaza la extensión rara).
    base.url_directa = opcion.url_directa || null;
    var input = document.querySelector('.col-bloque-subs input[type="checkbox"]');
    base.con_subs = !!(input && input.checked);
    return base;
  }

  function encolar() {
    if (!resultado || enAnalisis) return;
    var snapshot = construirSnapshot();
    if (!snapshot) {
      mostrarError(str("errores.generico"));
      return;
    }
    whenReady(function () {
      window.pywebview.api.agregar_descarga(snapshot).then(function (r) {
        if (!r || r.ok !== true) {
          mostrarError(r && r.error && r.error.mensaje,
                       r && r.error && r.error.codigo);
        } else {
          mostrarAvisoCola();
        }
        // la insignia la actualiza el evento "cola" desde Python.
      })["catch"](function () {
        mostrarError(str("errores.generico"));
      });
    });
  }

  // PLAYLIST (plan de playlists, Paso 5): pantalla con la lista de videos,
  // selección por casilla y UNA calidad para toda la lista (el listado es
  // plano: no hay calidades por video hasta descargar cada uno).
  var playlistDatos = null;

  function etiquetaCalidadPlaylist(o) {
    if (o.valor === "mejor") return str("playlist.calidadMaxima");
    if (o.valor === "musica") return str("playlist.calidadMusica");
    var h = Number(o.valor);
    if (h === 4320) return str("playlist.calidad8K");
    if (h === 2160) return str("playlist.calidad4K");
    if (h === 1440) return str("playlist.calidad2K");
    if (h === 1080) return str("playlist.calidadFullHD");
    return (Number.isFinite(h) ? Math.trunc(h) : o.valor) + "p";
  }

  function selectorPlaylist(valor) {
    // Selectores con respaldos (mismo criterio que analyzer P0.5), pero
    // pidiendo PRIMERO codecs compatibles con MP4 (H.264 + AAC): la app
    // fusiona con ffmpeg a mp4 y, si el formato elegido trae opus/vp9,
    // la fusión falla ("algo inesperado"). Ajustes 21/11.
    if (valor === "musica") return "bestaudio";
    var altura = (valor === "mejor") ? "" : "[height<=" + valor + "]";
    return "bestvideo[vcodec^=avc1]" + altura +
           "+bestaudio[acodec^=mp4a]" +
           "/bestvideo[vcodec^=avc1]" + altura + "+bestaudio" +
           "/bestvideo" + altura + "[ext=mp4]+bestaudio" +
           "/bestvideo" + altura + "+bestaudio" +
           "/best" + altura +
           "/best";
  }

  function renderPlaylist(data) {
    playlistDatos = data;
    var lista = document.querySelector("[data-pl-lista]");
    if (!lista) return;
    lista.textContent = "";
    var titulo = document.querySelector("[data-pl-titulo]");
    if (titulo) {
      titulo.textContent = data.titulo || "";
      titulo.title = data.titulo || "";
    }
    (data.entradas || []).forEach(function (entrada, i) {
      var fila = document.createElement("label");
      fila.className = "pl-fila";
      var casilla = document.createElement("input");
      casilla.type = "checkbox";
      casilla.checked = true;
      casilla.setAttribute("data-pl-idx", String(i));
      // Nombre accesible real: el título del video (el <label> lo envuelve,
      // pero el lector de pantalla lo lee mejor si el input lo lleva a él).
      casilla.setAttribute("aria-label", entrada.titulo || "");
      fila.appendChild(casilla);
      var mini = document.createElement("img");
      mini.className = "pl-mini";
      mini.alt = "";
      // Solo data:image/ (CSP); si la entrada no trajo miniatura, el gatito.
      if (typeof entrada.miniatura === "string" &&
          entrada.miniatura.indexOf("data:image/") === 0) mini.src = entrada.miniatura;
      else mini.src = "assets/img/Icos/Miauki.png";
      fila.appendChild(mini);
      var cuerpo = document.createElement("div");
      cuerpo.className = "pl-cuerpo";
      var t = document.createElement("span");
      t.className = "pl-vtitulo";
      t.textContent = entrada.titulo || "";
      t.title = entrada.titulo || "";
      cuerpo.appendChild(t);
      var d = document.createElement("span");
      d.className = "pl-vdur";
      d.textContent = formatearDuracion(entrada.duracion);
      cuerpo.appendChild(d);
      fila.appendChild(cuerpo);
      var li = document.createElement("li");
      li.className = "pl-item";
      li.appendChild(fila);
      lista.appendChild(li);
    });
    var calidad = document.querySelector("[data-pl-calidad]");
    if (calidad) {
      var opciones = (data.calidades && data.calidades.length)
        ? data.calidades
        : [{valor:"mejor"},{valor:"1080",resolucion:1080},
           {valor:"720",resolucion:720},{valor:"480",resolucion:480},
           {valor:"musica"}];
      calidad.textContent = "";
      opciones.forEach(function (o) {
        var opt = document.createElement("option");
        opt.value = o.valor;
        opt.textContent = etiquetaCalidadPlaylist(o);
        calidad.appendChild(opt);
      });
      calidad.value = data.calidad_defecto || (opciones[0] && opciones[0].valor) || "mejor";
    }
    var aviso = document.querySelector("[data-pl-salteados]");
    if (aviso) {
      var ns = (data.salteados || []).length;
      aviso.textContent = ns
        ? str("playlist.salteados").replace("{n}", formatearNumero(ns))
        : "";
      aviso.hidden = ns === 0;
    }

    var todos = document.querySelector("[data-pl-todos]");
    if (todos) todos.checked = true;
    pintarPlaylistSeleccion();
  }

  function pintarPlaylistSeleccion() {
    var casillas = document.querySelectorAll("[data-pl-lista] input[data-pl-idx]");
    var n = 0;
    casillas.forEach(function (c) { if (c.checked) n += 1; });
    var base = playlistDatos ? (playlistDatos.entradas || []).length : 0;
    var conteo = document.querySelector("[data-pl-conteo]");
    if (conteo) {
      var texto = str(base === 1 ? "playlist.conteo.uno" : "playlist.conteo.varios")
        .replace("{n}", formatearNumero(base));
      if (n < base) texto += " · " +
        str("playlist.elegidos").replace("{n}", formatearNumero(n));
      conteo.textContent = texto;
    }
    var todos = document.querySelector("[data-pl-todos]");
    if (todos && casillas.length) todos.checked = n === casillas.length;
    var miauk = document.querySelector("[data-pl-miauk]");
    if (miauk) miauk.disabled = n === 0;
  }

  function encolarPlaylist() {
    if (!playlistDatos || !playlistDatos.es_playlist) return;
    var calidad = document.querySelector("[data-pl-calidad]");
    var valor = calidad ? calidad.value : "mejor";
    var esMusica = valor === "musica";
    var sel = selectorPlaylist(valor);
    var elegidas = [];
    (playlistDatos.entradas || []).forEach(function (entrada, i) {
      var c = document.querySelector(
        '[data-pl-lista] input[data-pl-idx="' + i + '"]');
      if (!c || !c.checked) return;
      elegidas.push({
        url_canonica: entrada.url_canonica,
        tipo: esMusica ? "musica" : "video",
        selector: sel,
        contenedor: esMusica ? null : "mp4",
        kbps: null,
        titulo: entrada.titulo || "",
        miniatura: (typeof entrada.miniatura === "string" &&
                    entrada.miniatura.indexOf("data:image/") === 0)
                   ? entrada.miniatura : "",
        con_subs: false,
        resolucion: esMusica || valor === "mejor" ? null : Number(valor),
      });
    });
    if (!elegidas.length) return;
    var snapshot = {
      url_canonica: playlistDatos.url_canonica,
      tipo: "video",
      selector: sel,
      contenedor: esMusica ? null : "mp4",
      kbps: null,
      titulo: playlistDatos.titulo || "",
      miniatura: "",
      con_subs: false,
      entradas: elegidas,
    };
    var boton = document.querySelector("[data-pl-miauk]");
    if (boton) { boton.disabled = true; boton.setAttribute("aria-busy", "true"); }
    whenReady(function () {
      window.pywebview.api.agregar_playlist(snapshot).then(function (r) {
        if (boton) boton.removeAttribute("aria-busy");
        if (!r || r.ok !== true) {
          if (boton) boton.disabled = false;
          mostrarError(r && r.error && r.error.mensaje,
                       r && r.error && r.error.codigo);
          mostrarPantalla("inicio");
          return;
        }
        mostrarAvisoCola(r.data && r.data.bloques);
        mostrarPantalla("cola");
      })["catch"](function () {
        if (boton) { boton.removeAttribute("aria-busy"); boton.disabled = false; }
        mostrarError(str("errores.generico"));
        mostrarPantalla("inicio");
      });
    });
  }

  // PASO 1: el análisis real (Fase 3B). Un análisis a la vez (A3): el botón
  // queda deshabilitado con aria-busy hasta que llegue la respuesta.
  //
  // Link completo con esquema (plan `plan.md`, paso 3.3): http(s) pasa tal
  // cual, `www.` y un dominio con ruta suman `https://`. Un dominio sin ruta
  // no cuenta (en una frase sería un falso positivo).
  var DOMINIO_URL = /^[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?:[/?#]\S*)?$/i;
  function normalizarUrl(url) {
    var texto = (url || "").trim();
    if (/^https?:\/\//i.test(texto)) return texto;
    if (texto.slice(0, 4).toLowerCase() === "www." &&
        DOMINIO_URL.test(texto.slice(4))) {
      return "https://" + texto;
    }
    if (texto.indexOf("/") !== -1 && DOMINIO_URL.test(texto)) {
      return "https://" + texto;
    }
    return null;
  }

  function analizar() {
    if (enAnalisis) return;
    var input = document.querySelector("#campo-link");
    var url = input ? input.value.trim() : "";
    limpiarError();
    if (!url) {
      mostrarError(str("errores.vacio"));
      return;
    }
    url = normalizarUrl(url);
    if (!url) {
      // Validación local sin llamar al motor (§7); el resto lo resuelve Python.
      mostrarError(str("errores.formato"));
      return;
    }
    if (input) input.value = url;  // la barra muestra el link completo
    enAnalisis = true;
    nLanzamiento += 1;
    var n = nLanzamiento;
    estadoBotones(true, false);
    limpiarVideo();
    mostrarVideoEstado("skeleton");
    whenReady(function () {
      window.pywebview.api.analizar(url).then(function (respuesta) {
        if (n !== nLanzamiento) return; // respuesta vieja descartada (§7)
        enAnalisis = false;
        if (!respuesta || respuesta.ok !== true) {
          estadoBotones(false, false);
          mostrarError(respuesta && respuesta.error && respuesta.error.mensaje,
                       respuesta && respuesta.error && respuesta.error.codigo);
          mostrarVideoEstado("vacio");
          return;
        }
        resultado = respuesta.data;
        if (resultado.es_playlist) {
          // Playlist (plan de playlists, Paso 5): la lista se elige en su
          // propia pantalla; el MIAUK! del paso 1 queda deshabilitado.
          estadoBotones(false, false);
          renderPlaylist(resultado);
          mostrarPantalla("playlist");
          return;
        }
        estadoBotones(false, true);
        renderVideo(resultado);
        mostrarVideoEstado("listo");
        renderCalidad(resultado);
        actualizarSubs(resultado.subtitulos && resultado.subtitulos.disponible,
                       resultado.subtitulos && resultado.subtitulos.idiomas);
      })["catch"](function () {
        // El puente devuelve {ok:false} siempre; esto cubre un fallo del
        // puente mismo (promesa rechazada): el botón no puede quedar muerto.
        if (n !== nLanzamiento) return;
        enAnalisis = false;
        estadoBotones(false, false);
        mostrarError(str("errores.generico"));
        mostrarVideoEstado("vacio");
      });
    });
  }

  // "Más opciones": muestra/oculta las resoluciones (aria-expanded es la fuente).
  function iniciarMasOpciones() {
    var boton = document.querySelector(".btn-mas");
    var panel = document.getElementById("mas-opciones");
    if (!boton || !panel) return;
    boton.addEventListener("click", function () {
      var abierto = boton.getAttribute("aria-expanded") === "true";
      boton.setAttribute("aria-expanded", String(!abierto));
      panel.hidden = abierto;
    });
  }

  // PASO 1: el botón X aparece solo con texto; Analizar es el único camino.
  function iniciarPaso1() {
    var input = document.querySelector("#campo-link");
    if (!input) return;
    var limpiar = document.querySelector("[data-limpiar]");
    var analizarBtn = botonAnalizar();

    function sincronizar() {
      var vacio = input.value.trim() === "";
      if (limpiar) limpiar.hidden = vacio;
      // Auditoría 23/11: vaciar el campo también limpia el error y la vista
      // previa; si no, el aviso (y su botón de Ajustes) queda pegado a un
      // link que la persona ya borró.
      if (vacio) {
        limpiarError();
        limpiarVideo();
        mostrarVideoEstado("vacio");
      }
    }

    input.addEventListener("input", sincronizar);
    input.addEventListener("keydown", function (evento) {
      if (evento.key === "Enter") analizar();
    });

    if (limpiar) {
      limpiar.addEventListener("click", function () {
        input.value = "";
        sincronizar();
        input.focus();
      });
    }

    if (analizarBtn) analizarBtn.addEventListener("click", analizar);

    // Con el foco EN el campo, el pegado es el del navegador: si lo pegado es
    // un link válido, se analiza solo (Fase 7, B2).
    input.addEventListener("paste", function () {
      window.setTimeout(function () {
        var texto = input.value.trim();
        if (!texto) return;
        whenReady(function () {
          window.pywebview.api.validar_texto(texto).then(function (r) {
            var datos = r && r.ok === true ? r.data : null;
            if (datos && datos.url) {
              input.value = datos.url;
              sincronizar();
              analizar();
            }
          });
        });
      }, 0);
    });

    // Estado inicial real: input vacío, sin datos de mentira (3B: la maqueta
    // de Fase 2 nacía con un link de maqueta; con el motor conectado eso engaña).
    sincronizar();
    estadoBotones(false, false);
  }

  // BARRA DE PORTAPAPELES (Fase 5 B2): el link lo lee Python (`link_portapapeles`)
  // y acá solo se ofrece. El contenido NUNCA sale de la máquina: el aviso
  // muestra el link, no el resto del texto, y se descarta con × o a los 10 s.
  var temporizadorBarra = 0;
  var finBarra = 0;
  var restanteBarra = 10000;
  var MS_BARRA = 10000;
  var linkDescartado = "";
  var linkBarraActual = "";  // link del detector, sin campo de texto (23/11/2026)
  var ultimoChequeo = 0;

  function ocultarBarraPortapapeles() {
    window.clearTimeout(temporizadorBarra);
    temporizadorBarra = 0;
    finBarra = 0;
    if (linkBarraActual) linkDescartado = linkBarraActual;
    linkBarraActual = "";
    var app = document.getElementById("app");
    if (app) app.classList.add("sin-inferior");
    // inert: la barra colapsada no debe recibir foco con Tab
    var barra = document.querySelector(".barra-inferior");
    if (barra) barra.inert = true;
  }

  // Fase 9, B6: el conteo de 10 s se pausa mientras se arrastra y sigue después.
  function programarBarra(ms) {
    window.clearTimeout(temporizadorBarra);
    restanteBarra = Math.max(0, ms);
    finBarra = Date.now() + restanteBarra;
    temporizadorBarra = window.setTimeout(ocultarBarraPortapapeles, restanteBarra);
  }

  function pausarBarra() {
    if (!temporizadorBarra) return;
    window.clearTimeout(temporizadorBarra);
    temporizadorBarra = 0;
    restanteBarra = Math.max(0, finBarra - Date.now());
  }

  // Frases del detector: se elige al azar con la misma probabilidad cada una
  // (ajustes 22/11/2026). La lista vive acá para mantener un solo lugar.
  var FRASES_BARRA = [
    "barra.aviso",
    "barra.avisoDivertido",
    "barra.avisoRawrr",
    "barra.avisoUps",
  ];

  function fraseAleatoriaDeBarra() {
    var clave = FRASES_BARRA[Math.floor(Math.random() * FRASES_BARRA.length)];
    return str(clave) || str("barra.aviso");
  }

  function mostrarBarraPortapapeles(url) {
    var app = document.getElementById("app");
    var aviso = document.querySelector(".barra-aviso");
    if (!app || !url) return;
    linkBarraActual = url;
    if (aviso) aviso.textContent = fraseAleatoriaDeBarra();
    var barra = document.querySelector(".barra-inferior");
    if (barra) {
      barra.inert = false;
      // Cada barra nueva vuelve a su lugar de origen (abajo a la derecha).
      barra.classList.remove("arrastrada");
      barra.style.left = "";
      barra.style.top = "";
    }
    app.classList.remove("sin-inferior");
    programarBarra(MS_BARRA);
  }

  // Arrastre con el mouse (pointer events) + flechas con el asa enfocada.
  function ponerBarra(barra, x, y) {
    var r = barra.getBoundingClientRect();
    var maxX = Math.max(0, window.innerWidth - r.width);
    var maxY = Math.max(0, window.innerHeight - r.height);
    x = Math.round(Math.min(Math.max(0, x), maxX));
    y = Math.round(Math.min(Math.max(0, y), maxY));
    barra.classList.add("arrastrada");
    barra.style.left = x + "px";
    barra.style.top = y + "px";
  }

  function acotarBarra() {
    var barra = document.querySelector(".barra-inferior");
    if (!barra || !barra.classList.contains("arrastrada")) return;
    var r = barra.getBoundingClientRect();
    ponerBarra(barra, r.left, r.top);  // re-acota si la ventana se achicó
  }

  function iniciarArrastreBarra() {
    var barra = document.querySelector(".barra-inferior");
    var asa = document.querySelector("[data-arrastrar-barra]");
    if (!barra || !asa) return;
    var origen = null;
    asa.addEventListener("pointerdown", function (evento) {
      if (evento.button !== 0) return;
      var r = barra.getBoundingClientRect();
      origen = { x: evento.clientX, y: evento.clientY, izq: r.left, arriba: r.top };
      try { asa.setPointerCapture(evento.pointerId); } catch (e) { /* sin captura */ }
      pausarBarra();
      evento.preventDefault();
    });
    asa.addEventListener("pointermove", function (evento) {
      if (!origen) return;
      ponerBarra(barra, origen.izq + evento.clientX - origen.x,
                 origen.arriba + evento.clientY - origen.y);
    });
    function soltar() {
      if (!origen) return;
      origen = null;
      programarBarra(restanteBarra);
    }
    asa.addEventListener("pointerup", soltar);
    asa.addEventListener("pointercancel", soltar);
    asa.addEventListener("keydown", function (evento) {
      var paso = evento.shiftKey ? 40 : 10;
      var r = barra.getBoundingClientRect();
      var dx = 0;
      var dy = 0;
      if (evento.key === "ArrowLeft") dx = -paso;
      else if (evento.key === "ArrowRight") dx = paso;
      else if (evento.key === "ArrowUp") dy = -paso;
      else if (evento.key === "ArrowDown") dy = paso;
      else return;
      evento.preventDefault();
      ponerBarra(barra, r.left + dx, r.top + dy);
    });
    window.addEventListener("resize", acotarBarra);
  }

  // Botón "Miauk" de la barra: pone el link en el campo y ANALIZA (spec §4:
  // el "Miauk" de la barra analiza, no descarga).
  function usarLinkDeBarra() {
    var campo = document.querySelector("#campo-link");
    if (!linkBarraActual || !campo) return;
    campo.value = linkBarraActual;
    campo.dispatchEvent(new Event("input"));
    ocultarBarraPortapapeles();
    // El botón rápido de Miauk! además de analizar, lleva a Inicio para que
    // la previsualización se vea ahí (tanda 22/11/2026).
    mostrarPantalla("inicio");
    analizar();
  }

  // Botón "Pegar" del campo: trae el link del portapapeles en el momento.
  function pegarDelPortapapeles() {
    whenReady(function () {
      window.pywebview.api.link_portapapeles().then(function (respuesta) {
        if (!respuesta || respuesta.ok !== true || !respuesta.data) return;
        var url = respuesta.data.url;
        var campo = document.querySelector("#campo-link");
        if (!url || !campo) return;
        campo.value = url;
        campo.dispatchEvent(new Event("input"));
        campo.focus();
        ocultarBarraPortapapeles();
      });
    });
  }

  // Al abrir la app y al volver a la ventana: si hay un link nuevo, se ofrece.
  function revisarPortapapeles() {
    var ahora = Date.now();
    if (ahora - ultimoChequeo < 1500) return;
    ultimoChequeo = ahora;
    var barra = document.querySelector(".barra-inferior");
    if (barra && !barra.inert) return;            // ya se está mostrando
    whenReady(function () {
      window.pywebview.api.link_portapapeles().then(function (respuesta) {
        if (!respuesta || respuesta.ok !== true || !respuesta.data) return;
        var url = respuesta.data.url;
        if (!url || url === linkDescartado) return;
        var campo = document.querySelector("#campo-link");
        if (campo && campo.value.trim() === url) return;
        mostrarBarraPortapapeles(url);
      });
    });
  }

  // ---------- Ctrl+V y arrastrar y soltar (Fase 7, B2) ----------
  // El portapapeles lo lee Python SÓLO cuando la persona aprieta Ctrl+V o
  // suelta algo. Nunca se registra el contenido; solo se usa el link.

  function esCampoDeTexto(el) {
    if (!el) return false;
    return el.tagName === "INPUT" || el.tagName === "TEXTAREA" ||
      el.isContentEditable === true;
  }

  function analizarLink(link) {
    var campo = document.querySelector("#campo-link");
    if (!campo || !link) return;
    mostrarPantalla("inicio");
    campo.value = link;
    campo.dispatchEvent(new Event("input"));
    analizar();
  }

  function iniciarPegado() {
    document.addEventListener("keydown", function (evento) {
      var tecla = (evento.key || "").toLowerCase();
      if (tecla !== "v" || !(evento.ctrlKey || evento.metaKey)) return;
      if (evento.shiftKey || evento.altKey) return;
      if (recorrido.abierto) return;   // el recorrido manda mientras está abierto
      // Con el foco en un campo de texto manda el pegado normal; ese caso lo
      // resuelve el "paste" del campo (arriba).
      if (esCampoDeTexto(document.activeElement)) return;
      evento.preventDefault();
      whenReady(function () {
        window.pywebview.api.pegar_link().then(function (r) {
          var datos = r && r.ok === true ? r.data : null;
          if (!datos || !datos.url) {
            mostrarError(str("pegar.noLink"));
            return;
          }
          analizarLink(datos.url);
        });
      });
    });
  }

  function iniciarSoltar() {
    var capa = document.querySelector("[data-soltar]");
    var profundidad = 0;

    function traeAlgo(evento) {
      var dt = evento.dataTransfer;
      if (!dt || !dt.types) return false;
      var tipos = Array.prototype.slice.call(dt.types);
      return tipos.indexOf("Files") >= 0 ||
        tipos.indexOf("text/plain") >= 0 ||
        tipos.indexOf("text/uri-list") >= 0;
    }

    function textoDe(evento) {
      var dt = evento.dataTransfer;
      if (!dt) return "";
      return dt.getData("text/uri-list") || dt.getData("text/plain") || "";
    }

    function esconder() {
      profundidad = 0;
      if (capa) capa.hidden = true;
    }

    document.addEventListener("dragenter", function (evento) {
      evento.preventDefault();
      if (!traeAlgo(evento)) return;
      profundidad += 1;
      if (capa) capa.hidden = false;
    });

    document.addEventListener("dragover", function (evento) {
      // Sin esto el navegador abre el archivo o navega al link soltado.
      evento.preventDefault();
      if (evento.dataTransfer && traeAlgo(evento)) {
        evento.dataTransfer.dropEffect = "copy";
      }
    });

    document.addEventListener("dragleave", function () {
      profundidad = Math.max(0, profundidad - 1);
      if (!profundidad) esconder();
    });

    document.addEventListener("drop", function (evento) {
      evento.preventDefault();   // nunca dejar que el navegador abra nada
      esconder();
      var tipos = evento.dataTransfer
        ? Array.prototype.slice.call(evento.dataTransfer.types) : [];
      if (tipos.indexOf("Files") >= 0) {
        mostrarPantalla("inicio");
        mostrarError(str("soltar.archivo"));
        return;
      }
      var texto = textoDe(evento);
      whenReady(function () {
        window.pywebview.api.validar_texto(texto).then(function (r) {
          var datos = r && r.ok === true ? r.data : null;
          if (!datos || !datos.url) {
            mostrarPantalla("inicio");
            mostrarError(str("soltar.noLink"));
            return;
          }
          analizarLink(datos.url);
        });
      });
    });
  }

  // ---------- RECORRIDO GUIADO (Fase 7, C) ----------
  // No es una pantalla de bienvenida: son 8 pasos que señalan cosas reales.
  // Se muestra la PRIMERA vez (ajuste interno `recorrido_visto`) y se repite
  // desde Acerca → "Ver el recorrido". Un paso cuyo elemento no se ve se saltea.
  var PASOS_RECORRIDO = [
    { pantalla: "inicio", objetivo: "#campo-link",
      titulo: "recorrido.p1.titulo", texto: "recorrido.p1.texto" },
    { pantalla: "inicio", objetivo: 'section[aria-labelledby="t-paso2"]',
      titulo: "recorrido.p2.titulo", texto: "recorrido.p2.texto" },
    { pantalla: "inicio", objetivo: 'section[aria-labelledby="t-paso3"]',
      titulo: "recorrido.p3.titulo", texto: "recorrido.p3.texto" },
    { pantalla: "inicio", objetivo: ".columna-derecha",
      titulo: "recorrido.p4.titulo", texto: "recorrido.p4.texto" },
    { pantalla: "inicio", objetivo: '.nav-item[data-pantalla="cola"]',
      titulo: "recorrido.p5.titulo", texto: "recorrido.p5.texto" },
    { pantalla: "inicio", objetivo: '.nav-item[data-pantalla="historial"]',
      titulo: "recorrido.p6.titulo", texto: "recorrido.p6.texto" },
    { pantalla: "ajustes", objetivo: '.nav-item[data-pantalla="ajustes"]',
      titulo: "recorrido.p7.titulo", texto: "recorrido.p7.texto" },
    { pantalla: "inicio", objetivo: "[data-refresh]",
      titulo: "recorrido.p8.titulo", texto: "recorrido.p8.texto" }
  ];

  var recorrido = { abierto: false, pasos: [], paso: 0, antes: null,
                    pantallaAntes: "inicio" };

  function seVe(el) {
    // No alcanza con `el.hidden`: los botones del menú llevan hidden pero su
    // CSS los muestra igual, así que se mide el estilo real.
    if (!el) return false;
    var r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    var estilo = window.getComputedStyle(el);
    return estilo.display !== "none" && estilo.visibility !== "hidden";
  }

  function pantallaVisible() {
    var secciones = document.querySelectorAll("section[data-pantalla]");
    for (var i = 0; i < secciones.length; i += 1) {
      if (!secciones[i].hidden) return secciones[i].getAttribute("data-pantalla");
    }
    return "inicio";
  }

  function recolectarPasos() {
    var lista = [];
    var antes = pantallaVisible();
    for (var i = 0; i < PASOS_RECORRIDO.length; i += 1) {
      var paso = PASOS_RECORRIDO[i];
      mostrarPantalla(paso.pantalla);
      if (seVe(document.querySelector(paso.objetivo))) lista.push(paso);
    }
    mostrarPantalla(antes);
    return lista;
  }

  function ubicarRecorrido(el, caja) {
    var anillo = document.querySelector("[data-recorrido-foco]");
    var r = el.getBoundingClientRect();
    var aire = 6;
    var margen = 16;
    var hueco = 14;
    var alto = caja.offsetHeight || 190;
    var ancho = caja.offsetWidth || 340;
    var vw = window.innerWidth;
    var vh = window.innerHeight;
    var puesto = null;
    // Primero se prueba con el elemento entero; si no hay lugar para el cartel
    // sin taparlo, se resalta su parte de arriba (el título) y se reintenta.
    var alturas = [r.height, Math.min(r.height, 140)];
    for (var i = 0; i < alturas.length && !puesto; i += 1) {
      var altoFoco = Math.max(alturas[i], 24);
      var borde = { left: r.left - aire, top: r.top - aire,
                    right: r.left + r.width + aire,
                    bottom: r.top + altoFoco + aire };
      var candidatos = [
        { left: borde.left, top: borde.bottom + hueco },          // abajo
        { left: borde.left, top: borde.top - alto - hueco },      // arriba
        { left: borde.right + hueco, top: borde.top },            // derecha
        { left: borde.left - ancho - hueco, top: borde.top }      // izquierda
      ];
      // En la barra lateral, el cartel va a la derecha: abajo taparía los
      // demás botones del menú.
      if (r.right < vw * 0.25) {
        candidatos = [candidatos[2], candidatos[0], candidatos[1],
                      candidatos[3]];
      }
      for (var j = 0; j < candidatos.length; j += 1) {
        var c = candidatos[j];
        if (c.left < margen || c.top < margen) continue;
        if (c.left + ancho > vw - margen) continue;
        if (c.top + alto > vh - margen) continue;
        puesto = { left: c.left, top: c.top, altoFoco: altoFoco };
        break;
      }
    }
    if (!puesto) {
      // Sin lugar alrededor (pantalla muy chica): se acomoda como se pueda.
      puesto = {
        left: Math.min(Math.max(margen, r.left), vw - ancho - margen),
        top: Math.min(Math.max(margen, r.top), vh - alto - margen),
        altoFoco: Math.min(r.height, 140)
      };
    }
    anillo.style.top = (r.top - aire) + "px";
    anillo.style.left = (r.left - aire) + "px";
    anillo.style.width = (r.width + aire * 2) + "px";
    anillo.style.height = (puesto.altoFoco + aire * 2) + "px";
    caja.style.top = puesto.top + "px";
    caja.style.left = puesto.left + "px";
  }

  function irAPaso(indice) {
    var pasos = recorrido.pasos;
    if (indice >= pasos.length) {
      cerrarRecorrido();
      return;
    }
    if (indice < 0) indice = 0;
    var paso = pasos[indice];
    mostrarPantalla(paso.pantalla);
    var el = document.querySelector(paso.objetivo);
    if (!seVe(el)) {
      // Cambió algo mientras el recorrido estaba abierto: se saltea.
      pasos.splice(indice, 1);
      if (!pasos.length) {
        cerrarRecorrido();
        return;
      }
      irAPaso(Math.min(indice, pasos.length - 1));
      return;
    }
    recorrido.paso = indice;
    document.querySelector("[data-recorrido-indicador]").textContent =
      str("recorrido.indicador").replace("{n}", String(indice + 1))
        .replace("{total}", String(pasos.length));
    document.querySelector("[data-recorrido-titulo]").textContent = str(paso.titulo);
    document.querySelector("[data-recorrido-texto]").textContent = str(paso.texto);
    var anterior = document.querySelector("[data-recorrido-anterior]");
    var siguiente = document.querySelector("[data-recorrido-siguiente]");
    anterior.hidden = indice === 0;
    siguiente.textContent = str(indice === pasos.length - 1
      ? "recorrido.entendido" : "recorrido.siguiente");
    ubicarRecorrido(el, document.querySelector("[data-recorrido-caja]"));
    siguiente.focus();
  }

  function abrirRecorrido() {
    if (recorrido.abierto) return false;
    // Se guardan ANTES de recolectarPasos: esa función cambia de pantalla y
    // se lleva el foco puesto (mostrarPantalla enfoca el título).
    var antes = document.activeElement;
    var pantallaAntes = pantallaVisible();
    var pasos = recolectarPasos();
    if (!pasos.length) return false;
    recorrido.abierto = true;
    recorrido.pasos = pasos;
    recorrido.antes = antes;
    recorrido.pantallaAntes = pantallaAntes;
    document.querySelector("[data-recorrido]").hidden = false;
    document.querySelector("[data-recorrido-foco]").hidden = false;
    irAPaso(0);
    return true;
  }

  function cerrarRecorrido() {
    if (!recorrido.abierto) return;
    recorrido.abierto = false;
    document.querySelector("[data-recorrido]").hidden = true;
    document.querySelector("[data-recorrido-foco]").hidden = true;
    mostrarPantalla(recorrido.pantallaAntes);
    var volver = recorrido.antes;
    recorrido.antes = null;
    // En una tarea aparte: mostrarPantalla enfoca el título de la pantalla y
    // ese foco no debe pisar el del botón que abrió el recorrido.
    window.setTimeout(function () {
      if (volver && document.contains(volver) && seVe(volver)) {
        volver.focus();
        return;
      }
      var campo = document.querySelector("#campo-link");
      if (campo && seVe(campo)) campo.focus();
    }, 0);
  }

  function iniciarRecorrido() {
    var abrir = document.querySelector("[data-acerca-recorrido]");
    if (abrir) abrir.addEventListener("click", function () { abrirRecorrido(); });
    var saltar = document.querySelector("[data-recorrido-saltar]");
    if (saltar) saltar.addEventListener("click", cerrarRecorrido);
    var anterior = document.querySelector("[data-recorrido-anterior]");
    if (anterior) anterior.addEventListener("click", function () {
      irAPaso(recorrido.paso - 1);
    });
    var siguiente = document.querySelector("[data-recorrido-siguiente]");
    if (siguiente) siguiente.addEventListener("click", function () {
      irAPaso(recorrido.paso + 1);
    });
    // Foco atrapado SOLO mientras está abierto; Escape lo cierra.
    document.addEventListener("keydown", function (evento) {
      if (!recorrido.abierto) return;
      if (evento.key === "Escape") {
        evento.preventDefault();
        cerrarRecorrido();
        return;
      }
      if (evento.key !== "Tab") return;
      var caja = document.querySelector("[data-recorrido-caja]");
      if (!caja) return;
      var botones = caja.querySelectorAll("button:not([hidden])");
      if (!botones.length) return;
      var primero = botones[0];
      var ultimo = botones[botones.length - 1];
      if (evento.shiftKey && document.activeElement === primero) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault();
        primero.focus();
      }
    });
    window.addEventListener("resize", function () {
      if (!recorrido.abierto) return;
      var paso = recorrido.pasos[recorrido.paso];
      var el = paso ? document.querySelector(paso.objetivo) : null;
      if (el) ubicarRecorrido(el, document.querySelector("[data-recorrido-caja]"));
    });
  }

  // Panel "Guardar en" (Fase 2D.3): si la ruta no entra en la columna, se  // abrevia por el MEDIO (ej. "Descargas\Miauki YT" → "Descarga…Miauki YT").
  function abreviarRutaEl(el, completo) {
    el.textContent = completo;
    if (!el.clientWidth || el.scrollWidth <= el.clientWidth) return;
    var inicio = Math.floor(completo.length / 2);
    var fin = inicio;
    while (el.scrollWidth > el.clientWidth && (inicio > 0 || fin < completo.length)) {
      if (inicio > 0) inicio--;
      if (fin < completo.length) fin++;
      el.textContent = completo.slice(0, inicio) + "…" + completo.slice(fin);
    }
  }

  function abreviarRutas() {
    document.querySelectorAll(".col-ruta-texto").forEach(function (el) {
      var completo = el.getAttribute("data-ruta-completa");
      if (completo) abreviarRutaEl(el, completo);
    });
  }

  function mostrarRuta(ruta) {
    document.querySelectorAll(".col-ruta-texto").forEach(function (el) {
      el.setAttribute("data-ruta-completa", ruta);
      abreviarRutaEl(el, ruta);
    });
    // D4: el globo de "Guardar en" muestra la ruta completa (el texto se abrevia).
    document.querySelectorAll(".col-ruta").forEach(function (el) {
      el.setAttribute("data-tooltip", ruta);
      el.setAttribute("aria-label", str("col.guardarEn") + ": " + ruta);
    });
  }

  // Ajustes reales (settings vía el puente): ruta y subtítulos (§6, decisión e).
  // El recorrido ya se mostró: se anota para no repetirlo en cada apertura.
  function marcarRecorridoVisto() {
    if (ajustes.recorrido_visto === true) return;
    ajustes.recorrido_visto = true;
    whenReady(function () {
      window.pywebview.api.cambiar_ajuste("recorrido_visto", true)
        .then(function (respuesta) {
          if (respuesta && respuesta.ok === true) ajustes = respuesta.data;
        });
    });
  }

  // Botones "Cambiar" y "Abrir carpeta" de la columna derecha (Inicio).
  // "Cambiar" usa el mismo puente que Ajustes (selector + validación) y
  // sincroniza por mostrarRuta; "Abrir carpeta" usa la ruta de los ajustes
  // que Python ya valida, no el texto de la interfaz.
  function iniciarColumnaDerecha() {
    var cambiar = document.querySelector("[data-cambiar-carpeta]");
    if (cambiar) cambiar.addEventListener("click", function () {
      whenReady(function () {
        window.pywebview.api.cambiar_carpeta().then(function (r) {
          if (r && r.ok === true && r.data) mostrarRuta(r.data);
        });
      });
    });
    var abrir = document.querySelector("[data-abrir-carpeta]");
    if (abrir) abrir.addEventListener("click", function () {
      whenReady(function () {
        window.pywebview.api.abrir_carpeta();
      });
    });
    // Refresh manual (plan de ajustes UI, paso 4): recarga la ventana al
    // instante, sin dialogo; carpeta y ajustes siguen porque son del puente.
    var refrescar = document.querySelector("[data-refresh]");
    if (refrescar) refrescar.addEventListener("click", function () {
      window.location.reload();
    });
  }

  // Cartel suave si la app se traba (tanda 20/11/2026, paso 2): si el puente
  // deja de contestar 10 s y no hay análisis ni descargas en curso, se ofrece
  // Refrescar. "Seguir esperando" lo cierra; si el puente vuelve, se va solo.
  var analisisEnCurso = false;
  var activasCola = 0;

  function mostrarTraba() {
    var aviso = document.querySelector("[data-traba]");
    if (!aviso) return;
    aviso.hidden = false;
    var boton = aviso.querySelector("[data-traba-refrescar]");
    if (boton) boton.focus();
  }

  function ocultarTraba() {
    var aviso = document.querySelector("[data-traba]");
    if (aviso) aviso.hidden = true;
  }

  function iniciarTraba() {
    var aviso = document.querySelector("[data-traba]");
    if (!aviso || !window.MiaukiVigia) return;
    aviso.querySelector("[data-traba-refrescar]").addEventListener("click",
      function () { window.location.reload(); });
    aviso.querySelector("[data-traba-esperar]").addEventListener("click",
      function () { ocultarTraba(); });
    whenReady(function () {
      window.MiaukiVigia.crear({
        consultar: function () { return window.pywebview.api.cola_actual(); },
        trabajando: function () { return analisisEnCurso || activasCola > 0; },
        alAvisar: mostrarTraba,
        alVolver: ocultarTraba
      }).iniciar();
    });
  }

  // Botones globales de la Cola (plan archivos y cola, paso 2): pausan,
  // reanudan o cancelan todo, y el tacho borra el historial de la Cola sin
  // tocar archivos en disco.
  function alternar(selector, visible) {
    var el = document.querySelector(selector);
    if (el) el.hidden = !visible;
  }

  function iniciarGlobalesCola() {
    var acciones = [
      ["[data-cola-pausar-todo]", "pausar_todo"],
      ["[data-cola-reanudar-todo]", "reanudar_todo"],
      ["[data-cola-cancelar-todo]", "cancelar_todo"],
      ["[data-cola-limpiar-historial]", "limpiar_historial_cola"],
    ];
    acciones.forEach(function (par) {
      var boton = document.querySelector(par[0]);
      if (boton) boton.addEventListener("click", function () {
        whenReady(function () {
          window.pywebview.api[par[1]]();
        });
      });
    });
  }

  // Cerrar vista previa (plan de ajustes UI, paso 5): el × de la tarjeta
  // oculta la vista previa SOLO en esta sesion (variable, no localStorage);
  // limpiarVideo() la reactiva al analizar de nuevo, incluso el mismo link.
  // Tamaño de fuente (plan archivos y cola, paso 3): "Un poco más grande"
  // escala toda la interfaz un 10% con la clase font-grande en la raíz
  // (html): las medidas de letra están en rem. Acerca de (paso 4) suma su
  // +10% propio en CSS.
  function aplicarTamanoFuente(valor) {
    document.documentElement.classList.toggle("font-grande",
      valor === "grande");
  }

  function iniciarCierreVista() {
    var cerrar = document.querySelector("[data-cerrar-preview]");
    if (cerrar) cerrar.addEventListener("click", function () {
      var tarjeta = document.querySelector(".video-listo");
      if (tarjeta) tarjeta.hidden = true;
    });
  }

  // Idioma de la interfaz (tanda 22/11/2026, paso 6): el ajuste guardado manda.
  // Auditoría 23/11: se recarga con `?idioma=<lang>` y no con el almacenamiento
  // local, que en el .exe (WebView2 en modo privado) no siempre sobrevive a la
  // recarga. El ajuste real está en Python y se aplica al abrir.
  function sincronizarIdioma(guardado) {
    var idioma = guardado === "en" ? "en" : "es";
    if (idioma === window.MiaukiIDIOMA) return;
    if (window.MiaukiIdioma && window.MiaukiIdioma.guardar) {
      window.MiaukiIdioma.guardar(idioma);   // caché para la próxima apertura
    }
    window.location.replace(window.location.pathname + "?idioma=" + idioma);
  }

  function cargarAjustes() {    whenReady(function () {
      window.pywebview.api.obtener_ajustes().then(function (respuesta) {
        if (!respuesta || respuesta.ok !== true) return;
        ajustes = respuesta.data;
        if (ajustes.carpeta_descargas) mostrarRuta(ajustes.carpeta_descargas);
        aplicarTamanoFuente(ajustes.tamano_fuente);
        sincronizarIdioma(ajustes.idioma_interfaz);
        // Recorrido guiado: solo la primera vez (Fase 7, C). Se marca visto al
        // mostrarlo, así no reaparece si se cierra la app en el medio.
        if (ajustes.recorrido_visto !== true) {
          marcarRecorridoVisto();
          window.setTimeout(function () { abrirRecorrido(); }, 500);
        }
        if (typeof ajustes.incluir_subs === "boolean") {
          var input = document.querySelector('.col-bloque-subs input[type="checkbox"]');
          if (input && !input.disabled) input.checked = ajustes.incluir_subs;
        }
      });
    });
  }

  // Subtítulos: data-subs del BLOQUE gobierna el aspecto; el interruptor
  // escribe el ajuste real incluir_subs (settings) — sin memoria propia.
  function actualizarSubs(disponible, idiomas) {
    var bloque = document.querySelector(".col-bloque-subs");
    if (!bloque) return;
    var input = bloque.querySelector('input[type="checkbox"]');
    var fila = bloque.querySelector(".col-subs");
    var lista = bloque.querySelector("[data-subs-idiomas]");
    if (disponible) {
      bloque.setAttribute("data-subs", "si");
      if (input) {
        input.disabled = false;
        input.checked = ajustes.incluir_subs !== false;
      }
      if (lista) {
        var idiomasListos = (idiomas || []).slice(0, 6);
        var texto = str("col.subsIdiomas");
        if (idiomasListos.length) {
          texto += " " + idiomasListos.join(", ");
          if ((idiomas || []).length > 6) texto += "…";
          lista.textContent = texto;
          lista.hidden = false;
        } else {
          lista.hidden = true;
        }
      }
    } else {
      bloque.setAttribute("data-subs", "no");
      if (input) {
        input.disabled = true;
        input.checked = false;
      }
      if (lista) lista.hidden = true;
      if (fila) fila.hidden = false;
    }
  }

  function iniciarSubs() {
    var input = document.querySelector('.col-bloque-subs input[type="checkbox"]');
    if (!input) return;
    input.addEventListener("change", function () {
      whenReady(function () {
        window.pywebview.api.cambiar_ajuste("incluir_subs", input.checked)
          .then(function (respuesta) {
            if (!respuesta || respuesta.ok !== true) {
              // Si el guardado falla, el interruptor vuelve al ajuste real.
              input.checked = ajustes.incluir_subs !== false;
              return;
            }
            ajustes = respuesta.data;
          });
      });
    });
  }

  // Eventos Python→JS (3d.11): "cola" mueve la insignia y dibuja la lista;
  // "progreso" se guarda por id (Fase 6 lo usa para el avance).
  var progresoActual = {};
  var ESTADOS_ACTIVOS = { espera: 1, descargando: 1, procesando: 1, pausa: 1 };

  function textoConteo(n) {
    if (n === 1) return str("cola.conteo.uno");
    return str("cola.conteo.varios").replace("{n}", String(n));
  }

  function etiquetaEstado(estado) {
    return str("cola.estado." + estado) || estado || "";
  }

  // ----- Progreso por ítem (porción 5) -----
  // Estados que muestran la barra. El evento "progreso" llega ~4 veces por
  // segundo: la barra se mueve con una transición CSS corta (suave sin rAF).
  var CON_PROGRESO = { descargando: 1, procesando: 1, pausa: 1 };

  // D4: cada estado tiene su ícono (el texto sigue al lado) y su color en CSS.
  var ESTADO_ICONO = {
    espera: "tiempo",
    descargando: "descarga",
    procesando: "formato",
    pausa: "pausar",
    terminada: "listo",
    error: "alerta",
    interrumpida: "alerta",
    cancelada: "limpiar",
  };

  function filaEstado(item) {
    var estado = document.createElement("p");
    estado.className = "cola-estado";
    estado.appendChild(icono(ESTADO_ICONO[item.estado] || "tiempo",
                             "cola-estado-ico"));
    var texto = document.createElement("span");
    texto.textContent = etiquetaEstado(item.estado);
    estado.appendChild(texto);
    return estado;
  }

  function porcentajeDe(p) {
    if (!p) return 0;
    if (p.fase === "proceso") return 100; // descarga lista: se está uniendo con ffmpeg
    if (typeof p.porcentaje !== "number") return 0;
    return Math.max(0, Math.min(100, p.porcentaje));
  }

  function textoProgreso(p) {
    if (!p || p.fase === "proceso") return "";
    var partes = [];
    if (typeof p.porcentaje === "number") {
      partes.push(formatearNumero(p.porcentaje, 0) + " %");
    }
    if (typeof p.velocidad === "number" && p.velocidad > 0) {
      partes.push(formatearBytes(p.velocidad) + "/s");
    }
    if (typeof p.restante === "number" && p.restante > 0) {
      partes.push(str("cola.quedan").replace("{t}", formatearDuracion(p.restante)));
    }
    if (typeof p.total === "number" && p.total > 0) {
      partes.push(formatearBytes(p.total));
    }
    return partes.join(" · ");
  }

  function esIndeterminada(p) {
    // "procesando" (uniendo con ffmpeg) sí sabe que va al 100 %: barra llena.
    return !p || (p.fase !== "proceso" && typeof p.porcentaje !== "number");
  }

  function pintarBarra(barra, relleno, p) {
    // Indeterminada: el ancho lo pone el CSS (el inline lo pisaría).
    if (esIndeterminada(p)) {
      barra.setAttribute("data-indeterminada", "si");
      relleno.style.width = "";
    } else {
      barra.removeAttribute("data-indeterminada");
      relleno.style.width = porcentajeDe(p) + "%";
    }
  }

  function barraDeItem(item) {
    var caja = document.createElement("div");
    caja.className = "cola-progreso";
    var barra = document.createElement("div");
    barra.className = "cola-barra";
    var p = progresoActual[item.id];
    var relleno = document.createElement("span");
    relleno.className = "cola-barra-fill";
    pintarBarra(barra, relleno, p);
    barra.appendChild(relleno);
    var datos = document.createElement("p");
    datos.className = "cola-datos";
    datos.textContent = textoProgreso(p);
    caja.appendChild(barra);
    caja.appendChild(datos);
    return caja;
  }

  function actualizarBarraItem(ident, p) {
    var li = document.querySelector('[data-cola-id="' + ident + '"]');
    if (!li) return; // ítem borrado/repintado: el evento tardío no hace nada
    var barra = li.querySelector(".cola-barra");
    var relleno = li.querySelector(".cola-barra-fill");
    if (barra && relleno) pintarBarra(barra, relleno, p);
    var datos = li.querySelector(".cola-datos");
    if (datos) datos.textContent = textoProgreso(p);
  }

  // Acciones por estado (spec §Cola: cancelar con X, reintento circular,
  // borrar; más pausar/reanudar y, en las terminadas, abrir carpeta/archivo).
  var ACCIONES = {
    espera: ["pausar", "cancelar"],
    descargando: ["pausar", "cancelar"],
    procesando: ["cancelar"],
    pausa: ["reanudar", "cancelar"],
    error: ["reintentar", "quitar"],
    interrumpida: ["reintentar", "quitar"],
    terminada: ["carpeta", "archivo", "quitar"],
    cancelada: ["quitar"],
  };

  var ACCION_INFO = {
    pausar: { icono: "pausar", texto: "cola.accion.pausar" },
    reanudar: { icono: "reanudar", texto: "cola.accion.reanudar" },
    cancelar: { icono: "limpiar", texto: "cola.accion.cancelar" },
    reintentar: { icono: "reintentar", texto: "cola.accion.reintentar" },
    quitar: { icono: "borrar", texto: "cola.accion.quitar" },
    carpeta: { icono: "carpeta", texto: "cola.accion.abrirCarpeta" },
    archivo: { icono: "abrir", texto: "cola.accion.mostrarArchivo" },
  };

  var SVGNS = "http://www.w3.org/2000/svg";

  function icono(nombre, clase) {
    var svg = document.createElementNS(SVGNS, "svg");
    svg.setAttribute("class", clase || "cola-ico");
    svg.setAttribute("aria-hidden", "true");
    var use = document.createElementNS(SVGNS, "use");
    use.setAttribute("href", "assets/icons/" + nombre + ".svg#ico-" + nombre);
    svg.appendChild(use);
    return svg;
  }

  // Dato de la fila del Historial con su ícono (el texto sigue siendo texto).
  function datoConIcono(nombreIcono, texto) {
    var span = document.createElement("span");
    span.className = "hist-dato";
    span.appendChild(icono(nombreIcono, "hist-ico"));
    var valor = document.createElement("span");
    valor.textContent = texto;
    span.appendChild(valor);
    return span;
  }

  function tipoIcono(tipo) {
    if (tipo === "musica") return "musica";
    if (tipo === "imagen") return "imagen";
    return "video";
  }

  function dominioDe(url) {
    try {
      return new URL(url).hostname.replace(/^www\./, "");
    } catch (e) {
      return "";
    }
  }

  // Sitio amigable + ícono de marca. "otro" NUNCA se muestra: va el dominio
  // real del link o, si no se puede leer, "Sitio web".
  function sitioDeHistorial(e) {
    if (e.sitio && e.sitio !== "otro" && SITIOS[e.sitio]) {
      return { icono: e.sitio, texto: SITIOS[e.sitio] };
    }
    return { icono: "globo",
             texto: dominioDe(e.url_canonica) || str("historial.sitioWeb") };
  }

  function llamarCola(metodo, ident, alTerminar) {
    whenReady(function () {
      var llamada = window.pywebview.api[metodo](ident);
      if (!llamada || !llamada.then) return;
      llamada.then(function () {
        if (alTerminar) alTerminar();
      })["catch"](function () {
        if (alTerminar) alTerminar();
      });
    });
  }

  function llamarAbrir(metodo, ruta) {
    var arg = (typeof ruta === "string" && ruta) ? ruta : null;
    if (metodo === "mostrar_archivo" && arg === null) return;
    whenReady(function () {
      var llamada = window.pywebview.api[metodo](arg);
      if (llamada && llamada.then) llamada["catch"](function () {});
    });
  }

  function botonTexto(texto, clase) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "cola-btn " + clase;
    b.textContent = texto;
    return b;
  }

  // Cancelar en una descarga que YA avanzó pide confirmación breve en línea
  // (en espera o en pausa no hace falta: no se perdió nada todavía).
  function confirmarCancelar(item, contenedor) {
    contenedor.textContent = "";
    var aviso = document.createElement("span");
    aviso.className = "cola-confirmar";
    aviso.setAttribute("role", "status");
    aviso.textContent = str("cola.confirmarCancelar");
    var si = botonTexto(str("cola.confirmarSi"), "cola-btn-sube");
    var no = botonTexto(str("cola.confirmarNo"), "cola-btn-sube");
    si.addEventListener("click", function () {
      si.disabled = true;
      llamarCola("cancelar_descarga", item.id, function () { si.disabled = false; });
    });
    no.addEventListener("click", function () { pintarCola(ultimosItems); });
    contenedor.appendChild(aviso);
    contenedor.appendChild(si);
    contenedor.appendChild(no);
    si.focus();
  }

  function ejecutarAccion(accion, item, contenedor, boton) {
    if (accion === "cancelar" &&
        (item.estado === "descargando" || item.estado === "procesando")) {
      confirmarCancelar(item, contenedor);
      return;
    }
    if (boton) boton.disabled = true;
    var soltar = boton ? function () { boton.disabled = false; } : null;
    switch (accion) {
      case "pausar": llamarCola("pausar_descarga", item.id, soltar); break;
      case "reanudar": llamarCola("reanudar_descarga", item.id, soltar); break;
      case "cancelar": llamarCola("cancelar_descarga", item.id, soltar); break;
      case "reintentar": llamarCola("reintentar_descarga", item.id, soltar); break;
      case "quitar": llamarCola("borrar_descarga", item.id, soltar); break;
      case "carpeta": llamarAbrir("abrir_carpeta", item.ruta); break;
      case "archivo": llamarAbrir("mostrar_archivo", item.ruta); break;
      default: if (soltar) soltar();
    }
  }

  function accionesDeItem(item) {
    var cont = document.createElement("div");
    cont.className = "cola-acciones";
    (ACCIONES[item.estado] || []).forEach(function (accion) {
      var info = ACCION_INFO[accion];
      if (!info) return;
      var boton = document.createElement("button");
      boton.type = "button";
      boton.className = "cola-btn";
      boton.setAttribute("data-accion", accion);
      boton.setAttribute("aria-label", str(info.texto));
      boton.title = str(info.texto);
      boton.setAttribute("data-tooltip", str(info.texto));
      boton.appendChild(icono(info.icono));
      boton.addEventListener("click", function () {
        ejecutarAccion(accion, item, cont, boton);
      });
      cont.appendChild(boton);
    });
    return cont;
  }

  // Ítem de la Cola (§7: los datos solo entran por textContent/createElement,
  // nunca por marcado crudo). Por ahora muestra miniatura, título y estado;
  // las acciones (porción 4) y el progreso (porción 5) se agregan después.
  // Botón "Actualizar motor" dentro de una fila de la Cola (Fase 7, A3):
  // se muestra solo cuando el error real del motor lo pide.
  function botonActualizarMotor() {
    var boton = document.createElement("button");
    boton.type = "button";
    boton.className = "error-accion";
    boton.textContent = str("motor.actualizar");
    boton.addEventListener("click", function () {
      if (window.MiaukiUI && window.MiaukiUI.buscarMotor) {
        window.MiaukiUI.buscarMotor(boton, function (datos) {
          if (datos && datos.accion === "actualizada") avisarMotor(str("motor.aviso"));
        });
      }
    });
    return boton;
  }

  function filaDeItem(item) {
    var li = document.createElement("li");
    li.className = "cola-item vidrio";
    li.setAttribute("data-cola-id", item.id);
    li.setAttribute("data-estado", item.estado || "espera");

    var mini = document.createElement("img");
    mini.className = "cola-mini";
    mini.alt = "";
    var uri = item.miniatura;
    if (typeof uri === "string" && uri.indexOf("data:image/") === 0) {
      mini.src = uri;
    } else {
      mini.hidden = true;
    }
    li.appendChild(mini);

    var cuerpo = document.createElement("div");
    cuerpo.className = "cola-cuerpo";

    var titulo = document.createElement("p");
    titulo.className = "cola-titulo";
    titulo.textContent = item.titulo || item.url_canonica || str("cola.sinTitulo");
    cuerpo.appendChild(titulo);

    cuerpo.appendChild(filaEstado(item));
    // Datos del archivo descargado (pedido 08/11/2026): peso real, formato,
    // sitio de origen y fecha/hora. Se muestra lo que ya se sabe en cada estado.
    // Bloque (plan de ajustes UI, paso 6.3): "Bloque X/Y" al inicio de la fila.
    var partes = [];
    if (item.bloque) partes.push(str("cola.bloque") + " " + item.bloque);
    if (item.sitio || item.url_canonica) {
      partes.push(sitioDeHistorial(item).texto);
    }
    if (item.contenedor) partes.push(String(item.contenedor).toUpperCase());
    if (item.peso > 0) partes.push(formatearBytes(item.peso));
    if (item.fecha) partes.push(fechaHistorial(item.fecha));
    partes = partes.filter(function (x) { return !!x; });
    if (partes.length) {
      var datos = document.createElement("p");
      datos.className = "cola-datos";
      datos.textContent = partes.join(" · ");
      cuerpo.appendChild(datos);
    }
    if (CON_PROGRESO[item.estado]) cuerpo.appendChild(barraDeItem(item));

    if (item.error && item.error.codigo === "motor_viejo") {
      cuerpo.appendChild(botonActualizarMotor());
    }

    li.appendChild(cuerpo);
    li.appendChild(accionesDeItem(item));
    return li;
  }

  var ultimosItems = [];

  function pintarCola(items) {
    var lista = document.querySelector("[data-cola-lista]");
    if (!lista) return;
    ultimosItems = Array.isArray(items) ? items : [];

    // F5 Parte 0 punto 3: repintar borra los botones y el foco caería al body
    // (quien navega con teclado tendría que volver a tabular después de cada
    // cambio de estado). Se recuerda qué botón tenía el foco y se le devuelve
    // al botón equivalente del ítem repintado.
    var foco = document.activeElement;
    var focoId = null, focoAccion = null;
    if (foco && foco.classList && foco.classList.contains("cola-btn")) {
      var liFoco = foco.closest(".cola-item");
      focoId = liFoco ? liFoco.getAttribute("data-cola-id") : null;
      focoAccion = foco.getAttribute("data-accion");
    }

    while (lista.firstChild) lista.removeChild(lista.firstChild);

    var activos = 0;
    var terminadas = 0;
    items.forEach(function (item) {
      if (!item || !item.id) return;
      if (ESTADOS_ACTIVOS[item.estado]) activos += 1;
      if (item.estado === "terminada") terminadas += 1;
      lista.appendChild(filaDeItem(item));
    });

    if (focoId && focoAccion) {
      var devuelto = lista.querySelector(
        '[data-cola-id="' + focoId + '"] .cola-btn[data-accion="' + focoAccion + '"]');
      if (devuelto) devuelto.focus();
    }

    var vacia = document.querySelector("[data-cola-vacia]");
    if (vacia) vacia.hidden = items.length > 0;

    var conteo = document.querySelector("[data-cola-conteo]");
    if (conteo) conteo.textContent = items.length ? textoConteo(activos) : "";

    // Botones globales (plan archivos y cola, paso 2): cada uno aparece solo
    // cuando hay algo que hacer; el tacho exige cero descargas activas.
    var enPausa = 0, cancelables = 0, borrables = 0;
    items.forEach(function (item) {
      if (!item || !item.id) return;
      var e = item.estado;
      if (e === "pausa") enPausa += 1;
      if (ESTADOS_ACTIVOS[e]) cancelables += 1;
      if (e === "terminada" || e === "error" || e === "cancelada"
          || e === "interrumpida") borrables += 1;
    });
    alternar("[data-cola-pausar-todo]",
      activos - enPausa > 0);           // espera + descargando/procesando
    alternar("[data-cola-reanudar-todo]", enPausa > 0);
    alternar("[data-cola-cancelar-todo]", cancelables > 0);
    alternar("[data-cola-limpiar-historial]",
      borrables > 0 && activos === 0);

    var limpiar = document.querySelector("[data-cola-limpiar]");
    if (limpiar) limpiar.hidden = terminadas === 0;

    // Resumen de salteos (plan de playlists, decisión de Maki, Paso 6): los
    // videos con error se agrupan por causa — "5 porque el enlace es privado,
    // 3 porque el video fue eliminado…" — en vez de leer fila por fila.
    var resumen = document.querySelector("[data-cola-resumen]");
    if (resumen) {
      var grupos = {};
      var conProblema = 0;
      items.forEach(function (item) {
        if (item && item.estado === "error" && item.error && item.error.codigo) {
          conProblema += 1;
          grupos[item.error.codigo] = (grupos[item.error.codigo] || 0) + 1;
        }
      });
      if (conProblema > 0) {
        var partes = Object.keys(grupos).map(function (codigo) {
          return formatearNumero(grupos[codigo]) + " " +
            (str("causa." + codigo) || str("causa.error_desconocido"));
        });
        resumen.textContent =
          str("playlist.resumenSalteados").replace("{n}", formatearNumero(conProblema))
          + ": " + partes.join(", ") + ".";
        resumen.hidden = false;
      } else {
        resumen.hidden = true;
        resumen.textContent = "";
      }
    }

    // F5 B5: si cambió el peso real descargado del link abierto, se actualiza.
    if (resultado) actualizarInfo();
  }

  function alLlegarCola(items) {
    if (!Array.isArray(items)) return;
    var n = 0;
    var vivos = {};
    items.forEach(function (item) {
      if (!item || !item.id) return;
      vivos[item.id] = 1;
      if (ESTADOS_ACTIVOS[item.estado]) n += 1;
    });
    // Poda: sin esto, un progreso tardío de un ítem ya borrado quedaría
    // guardado y podría pintarse si su id reapareciera.
    Object.keys(progresoActual).forEach(function (ident) {
      if (!vivos[ident]) delete progresoActual[ident];
    });
    window.MiaukiUI.actualizarCola(n);
    pintarCola(items);
  }

  // Aviso "Agregada a la cola" + "Ver cola" (porción 6). Va debajo del campo
  // del link y se oculta solo a los pocos segundos.
  var MS_AVISO = 4000;
  var temporizadorAviso = null;

  function ocultarAvisoCola() {
    var aviso = document.querySelector("[data-aviso-cola]");
    if (aviso) aviso.hidden = true;
    var ayuda = document.querySelector(".ayuda-tenue");
    if (ayuda) ayuda.hidden = false; // vuelve la ayuda al mismo renglón
    if (temporizadorAviso) {
      window.clearTimeout(temporizadorAviso);
      temporizadorAviso = null;
    }
  }

  function mostrarAvisoCola(bloques) {
    var aviso = document.querySelector("[data-aviso-cola]");
    if (!aviso) return;
    var texto = document.querySelector("[data-aviso-texto]");
    // Se escribe al mostrarlo (no al cargar) para que la región viva lo anuncie.
    if (texto) {
      texto.textContent = bloques > 1
        ? str("cola.agregadaBloques").replace("{n}", formatearNumero(bloques))
        : str("cola.agregada");
    }
    // F5 P0 (8c): el aviso reemplaza a la ayuda -> la tarjeta 1 no cambia de alto.
    var ayuda = document.querySelector(".ayuda-tenue");
    if (ayuda) ayuda.hidden = true;
    aviso.hidden = false;
    if (temporizadorAviso) window.clearTimeout(temporizadorAviso);
    temporizadorAviso = window.setTimeout(ocultarAvisoCola, MS_AVISO);
  }

  // Destello breve del contador al sumar una descarga (respeta movimiento reducido).
  function destellarCola() {
    var boton = document.querySelector('.nav-item[data-pantalla="cola"]');
    if (!boton) return;
    boton.classList.remove("destello");
    void boton.offsetWidth; // fuerza reinicio de la animación
    boton.classList.add("destello");
    window.setTimeout(function () { boton.classList.remove("destello"); }, 700);
  }

  // Al abrir la app la lista ya puede tener ítems: se pintan con el estado
  // real de la cola (el evento "cola" solo llega cuando algo cambia).
  function cargarColaInicial() {
    whenReady(function () {
      window.pywebview.api.cola_actual().then(function (respuesta) {
        if (respuesta && respuesta.ok === true && Array.isArray(respuesta.data)) {
          alLlegarCola(respuesta.data);
        }
      });
    });
  }

  function alLlegarProgreso(datos) {
    if (!datos || !datos.id) return;
    // Si el ítem ya no está en pantalla (cancelado y borrado), el aviso
    // tardío se descarta: no se guarda ni se recrea nada.
    if (!document.querySelector('[data-cola-id="' + datos.id + '"]')) return;
    progresoActual[datos.id] = datos;
    actualizarBarraItem(datos.id, datos);
  }

  // ----- HISTORIAL (Fase 6, B2) -----
  // Los datos llegan del puente por ID (nunca se manda una ruta). Todo entra
  // por textContent/createElement; la miniatura solo si es data:image/.
  // Ajustes 21/11: si el archivo no está o no hay portada, se muestra una de
  // las tres gatitas (elegida de forma estable según el id, para variar).
  var GATITOS = [
    "assets/img/Icos/Gatita miauki1.png",
    "assets/img/Icos/Gatita miauki2.png",
    "assets/img/Icos/Gatita miauki3.png",
  ];

  function gatitoPara(id) {
    var texto = String(id || "");
    var h = 0;
    for (var i = 0; i < texto.length; i++) {
      h = (h * 31 + texto.charCodeAt(i)) >>> 0;
    }
    return GATITOS[h % GATITOS.length];
  }

  function fechaHistorial(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    function dos(n) { return (n < 10 ? "0" : "") + n; }
    return dos(d.getDate()) + "/" + dos(d.getMonth() + 1) + "/" + d.getFullYear() +
      " " + dos(d.getHours()) + ":" + dos(d.getMinutes());
  }

  function pedirPuente(metodo, argumentos, alTerminar) {
    whenReady(function () {
      var llamada = window.pywebview.api[metodo].apply(window.pywebview.api,
                                                      argumentos || []);
      if (!llamada || !llamada.then) {
        if (alTerminar) alTerminar(null);
        return;
      }
      llamada.then(alTerminar)["catch"](function () {
        if (alTerminar) alTerminar(null);
      });
    });
  }

  function botonHistorial(iconoNombre, etiqueta, accion, alHacer) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "cola-btn";
    b.setAttribute("data-hist-accion", accion);
    b.setAttribute("aria-label", etiqueta);
    b.title = etiqueta;
    b.setAttribute("data-tooltip", etiqueta);
    b.appendChild(icono(iconoNombre));
    b.addEventListener("click", function () { alHacer(b); });
    return b;
  }

  function tipoEnPalabras(tipo) {
    if (tipo === "musica") return str("paso3.musica");
    if (tipo === "imagen") return str("paso3.imagen");
    return str("paso3.video");
  }

  function filaHistorial(e) {
    var li = document.createElement("li");
    li.className = "hist-item vidrio";
    li.setAttribute("data-hist-id", e.id);
    var falta = e.existe === false;
    if (falta) li.setAttribute("data-falta", "si");

    var mini;
    if (typeof e.miniatura === "string" && e.miniatura.indexOf("data:image/") === 0) {
      mini = document.createElement("img");
      mini.className = "hist-mini";
      mini.alt = "";
      mini.src = e.miniatura;
    } else {
      // Sin miniatura (o archivo ausente): gatito de respaldo, nunca un
      // recuadro vacío.
      mini = document.createElement("img");
      mini.className = "hist-mini hist-mini-gatito";
      mini.alt = "";
      mini.src = gatitoPara(e.id);
    }
    li.appendChild(mini);

    var cuerpo = document.createElement("div");
    cuerpo.className = "hist-cuerpo";
    var titulo = document.createElement("p");
    titulo.className = "hist-titulo";
    titulo.textContent = e.titulo || str("historial.sinTitulo");
    titulo.title = titulo.textContent;
    cuerpo.appendChild(titulo);

    var meta = document.createElement("p");
    meta.className = "hist-meta";
    meta.appendChild(datoConIcono(tipoIcono(e.tipo), tipoEnPalabras(e.tipo)));
    var detalle = [e.calidad, (e.contenedor || "").toUpperCase()]
      .filter(function (x) { return !!x; }).join(" · ");
    if (detalle) {
      var spanDetalle = document.createElement("span");
      spanDetalle.textContent = detalle;
      meta.appendChild(spanDetalle);
    }
    var sitio = sitioDeHistorial(e);
    meta.appendChild(datoConIcono(sitio.icono, sitio.texto));
    [fechaHistorial(e.fecha),
     e.peso > 0 ? formatearBytes(e.peso) : ""].forEach(function (texto) {
      if (!texto) return;
      var span = document.createElement("span");
      span.textContent = texto;
      meta.appendChild(span);
    });
    cuerpo.appendChild(meta);
    if (falta) {
      var aviso = document.createElement("p");
      aviso.className = "hist-falta";
      aviso.textContent = str("historial.sinArchivo");
      cuerpo.appendChild(aviso);
    }
    li.appendChild(cuerpo);

    var acciones = document.createElement("div");
    acciones.className = "hist-acciones";
    acciones.appendChild(botonHistorial(
      "reintentar", str("historial.accion.bajar"), "bajar",
      function (boton) {
        boton.disabled = true;
        pedirPuente("volver_a_bajar", [e.id], function (r) {
          boton.disabled = false;
          if (r && r.ok === true) mostrarPantalla("cola");
        });
      }));
    var carpeta = botonHistorial("carpeta", str("historial.accion.carpeta"),
      "carpeta", function () {
        pedirPuente("abrir_carpeta_historial", [e.id]);
      });
    var archivo = botonHistorial("abrir", str("historial.accion.archivo"),
      "archivo", function () {
        pedirPuente("mostrar_archivo_historial", [e.id]);
      });
    carpeta.disabled = falta;
    archivo.disabled = falta;
    acciones.appendChild(carpeta);
    acciones.appendChild(archivo);
    acciones.appendChild(botonHistorial(
      "borrar", str("historial.accion.quitar"), "quitar",
      function () { quitarFilaHistorial(e.id); }));
    li.appendChild(acciones);
    return li;
  }

  function actualizarConteoHistorial(n) {
    var conteo = document.querySelector("[data-hist-conteo]");
    if (conteo) {
      conteo.textContent = n === 1 ? str("historial.conteo.uno")
        : str("historial.conteo.varios").replace("{n}", String(n));
    }
    var vacia = document.querySelector("[data-hist-vacia]");
    if (vacia) vacia.hidden = n > 0;
    var borrar = document.querySelector("[data-hist-borrar]");
    if (borrar) borrar.hidden = n <= 0;
    var confirmar = document.querySelector("[data-hist-confirmar]");
    if (confirmar) confirmar.hidden = true;
  }

  function pintarHistorial(entradas) {
    var lista = document.querySelector("[data-hist-lista]");
    if (!lista) return;
    lista.textContent = "";
    var fragmento = document.createDocumentFragment();
    (entradas || []).forEach(function (e) {
      fragmento.appendChild(filaHistorial(e));
    });
    lista.appendChild(fragmento);
    actualizarConteoHistorial((entradas || []).length);
  }

  function cargarHistorial() {
    pedirPuente("listar_historial", [], function (r) {
      if (!r || r.ok !== true || !Array.isArray(r.data)) return;
      pintarHistorial(r.data);
    });
  }

  // Quitar UNA fila: se saca el <li> (no se repinta la lista de 500) y el foco
  // pasa a la fila siguiente (o a la anterior, o al título).
  function quitarFilaHistorial(ident) {
    var li = document.querySelector('[data-hist-id="' + ident + '"]');
    if (!li) return;
    pedirPuente("quitar_del_historial", [ident], function (r) {
      if (!r || r.ok !== true) return;
      // El vecino se busca recién ahora: mientras el puente respondía pudo
      // quitarse otra fila y el que se guardó antes quedaría fuera del DOM.
      var vecino = li.nextElementSibling || li.previousElementSibling;
      var lista = li.parentNode;
      lista.removeChild(li);
      actualizarConteoHistorial(lista.children.length);
      var destino = vecino && vecino.querySelector
        ? vecino.querySelector('[data-hist-accion="quitar"]') : null;
      if (!destino) destino = document.querySelector("#t-pantalla-historial");
      if (destino) destino.focus();
    });
  }

  function iniciarHistorial() {
    var pantalla = document.querySelector(".pantalla-historial");
    if (!pantalla) return;
    var borrar = pantalla.querySelector("[data-hist-borrar]");
    var confirmar = pantalla.querySelector("[data-hist-confirmar]");
    var si = pantalla.querySelector("[data-hist-si]");
    var no = pantalla.querySelector("[data-hist-no]");
    if (borrar && confirmar) {
      borrar.addEventListener("click", function () {
        borrar.hidden = true;
        confirmar.hidden = false;
        if (si) si.focus();
      });
    }
    if (no) no.addEventListener("click", function () {
      confirmar.hidden = true;
      borrar.hidden = false;
      borrar.focus();
    });
    if (si) si.addEventListener("click", function () {
      si.disabled = true;
      pedirPuente("borrar_historial", [], function (r) {
        si.disabled = false;
        if (r && r.ok === true) pintarHistorial([]);
      });
    });
    var inicio = pantalla.querySelector("[data-hist-inicio]");
    if (inicio) inicio.addEventListener("click", function () {
      mostrarPantalla("inicio");
    });
  }

  window.MiaukiManejadores = {
    cola: alLlegarCola,
    progreso: alLlegarProgreso,
    historial: function (datos) {
      // Solo si la pantalla está a la vista: no se repinta lo que no se ve.
      var pantalla = document.querySelector('[data-pantalla="historial"]');
      if (pantalla && !pantalla.hidden && datos && datos.cambio) cargarHistorial();
    },
    motor: function (datos) {
      // La comprobación del inicio encontró una versión nueva (Fase 7, A3):
      // aviso discreto, sin interrumpir lo que la persona está haciendo.
      if (datos && datos.actualizado) avisarMotor(str("motor.aviso"));
    },
  };

  // ÚNICO punto de entrada para el contador de la Cola de Descargas.
  // La Fase 4 lo llama con el evento "cola" (decisión 3d.14: cuenta los
  // ítems activos). Si es 0 o menor, se oculta.
  window.MiaukiUI = {
    // Recorrido guiado (Fase 7, C): se puede abrir desde Acerca.
    verRecorrido: function () {
      return abrirRecorrido();
    },
    recorridoAbierto: function () {
      return recorrido.abierto;
    },
    actualizarCola: function (n) {
      var insignia = document.querySelector("[data-cola-contador]");
      if (!insignia) return;
      var valor = Math.max(0, Math.floor(Number(n) || 0));
      activasCola = valor;
      var anterior = Math.max(0, Math.floor(Number(insignia.textContent) || 0));
      insignia.textContent = String(valor);
      insignia.hidden = valor <= 0;
      if (valor > anterior) destellarCola();
    },
    // Último progreso visto de un ítem (sin dibujar; Fase 6 lo usa).
    progresoDe: function (ident) {
      return progresoActual[ident] || null;
    },
    // Estados de la tarjeta de video: "vacio" | "skeleton" | "listo".
    mostrarVideoEstado: mostrarVideoEstado,
    // Barra de portapapeles (Fase 2D): mostrar(url) y ocultar().
    mostrarBarraPortapapeles: mostrarBarraPortapapeles,
    ocultarBarraPortapapeles: ocultarBarraPortapapeles,
    // Subtítulos: true = disponibles, false = no disponibles.
    actualizarSubs: actualizarSubs,
    // Ruta real de los ajustes (Fase 3B).
    mostrarRuta: mostrarRuta,
    // Navegación entre pantallas (Fase 4C Parte B, porción 1).
    mostrarPantalla: mostrarPantalla,
    // Dibujo de la lista de la Cola (porción 3).
    pintarCola: pintarCola,
  };

  // F5 P0 (8d): tooltip propio para los botones con solo ícono (acciones de la
  // Cola) y los de "Guardar en". El `title` del sistema no aparece al navegar
  // con teclado, así que dibujamos un globo propio (position:fixed, no lo
  // recorta el overflow de la lista). Es solo visual: el nombre accesible de
  // cada botón ya está en su aria-label.
  function iniciarTooltips() {
    var globo = document.createElement("div");
    globo.className = "globo";
    globo.setAttribute("aria-hidden", "true");
    globo.hidden = true;
    document.body.appendChild(globo);
    var dueño = null;

    function mostrar(el) {
      var texto = el.getAttribute("data-tooltip") ||
        el.getAttribute("aria-label") || (el.textContent || "").trim();
      if (!texto) return;
      dueño = el;
      globo.textContent = texto;
      globo.hidden = false;
      var b = el.getBoundingClientRect();
      var g = globo.getBoundingClientRect();
      var x = Math.min(Math.max(8, b.left + b.width / 2 - g.width / 2),
        window.innerWidth - g.width - 8);
      var y = b.top - g.height - 8;
      if (y < 8) y = Math.min(b.bottom + 8, window.innerHeight - g.height - 8);
      globo.style.left = x + "px";
      globo.style.top = y + "px";
    }

    function ocultar(el) {
      if (dueño !== el) return;
      dueño = null;
      globo.hidden = true;
    }

    function conTooltip(evento) {
      return evento.target && evento.target.closest
        ? evento.target.closest("[data-tooltip]") : null;
    }

    document.addEventListener("mouseover", function (e) {
      var el = conTooltip(e);
      if (el) mostrar(el);
    });
    document.addEventListener("mouseout", function (e) {
      var el = conTooltip(e);
      if (el) ocultar(el);
    });
    document.addEventListener("focusin", function (e) {
      var el = conTooltip(e);
      if (el) mostrar(el);
    });
    document.addEventListener("focusout", function (e) {
      var el = conTooltip(e);
      if (el) ocultar(el);
    });
  }

  // AJUSTES (Fase 5 B3): cada control escribe el ajuste real por el puente.
  // No hay copia local: lo que se muestra es lo que devuelve settings.
  function iniciarAjustes() {
    var pantalla = document.querySelector(".pantalla-ajustes");
    if (!pantalla) return;
    var ruta = pantalla.querySelector("[data-ajuste-ruta]");
    var estado = pantalla.querySelector("[data-ajuste-estado]");

    function avisar(clave, tarjeta) {
      if (!estado) return;
      // D5: el aviso ("Guardado.") aparece en la misma tarjeta que se tocó,
      // no al pie de la pantalla. Se mueve el único role="status" (así no hay
      // dos regiones vivas anunciando lo mismo).
      if (tarjeta && estado.parentNode !== tarjeta) tarjeta.appendChild(estado);
      estado.textContent = str(clave);
      if (clave === "ajustes.error") estado.setAttribute("data-error", "si");
      else estado.removeAttribute("data-error");
    }

    function tarjetaDe(el) {
      return el && el.closest ? el.closest(".ajuste") : null;
    }

    function pintar(ajustesNuevos) {
      if (!ajustesNuevos) return;
      if (ruta && ajustesNuevos.carpeta_descargas) {
        ruta.textContent = ajustesNuevos.carpeta_descargas;
      }
      pantalla.querySelectorAll("[data-ajuste]").forEach(function (el) {
        var clave = el.getAttribute("data-ajuste");
        if (!(clave in ajustesNuevos)) return;
        if (el.type === "checkbox") el.checked = ajustesNuevos[clave] === true;
        else el.value = String(ajustesNuevos[clave]);
      });
      pintarArchivo(nombreDeArchivo(ajustesNuevos.archivo_cookies));
      aplicarTamanoFuente(ajustesNuevos.tamano_fuente);   // cambia al instante
      sincronizarIdioma(ajustesNuevos.idioma_interfaz);   // y el idioma también
    }

    function guardar(clave, valor, tarjeta) {
      whenReady(function () {
        window.pywebview.api.cambiar_ajuste(clave, valor).then(function (r) {
          if (!r || r.ok !== true) { avisar("ajustes.error", tarjeta); return; }
          pintar(r.data);
          avisar("ajustes.guardado", tarjeta);
        });
      });
    }

    pantalla.querySelectorAll("[data-ajuste]").forEach(function (el) {
      el.addEventListener("change", function () {
        guardar(el.getAttribute("data-ajuste"),
                el.type === "checkbox" ? el.checked : el.value,
                tarjetaDe(el));
      });
    });

    var boton = pantalla.querySelector("[data-ajuste-carpeta]");
    if (boton) boton.addEventListener("click", function () {
      whenReady(function () {
        window.pywebview.api.cambiar_carpeta().then(function (r) {
          if (!r || r.ok !== true) { avisar("ajustes.error", tarjetaDe(boton)); return; }
          if (!r.data) return;                 // canceló o la carpeta no sirve
          if (ruta) ruta.textContent = r.data;
          mostrarRuta(r.data);
          avisar("ajustes.guardado", tarjetaDe(boton));
        });
      });
    });

    function pintarArchivo(nombre) {
      var linea = pantalla.querySelector("[data-cookies-archivo]");
      var quitar = pantalla.querySelector("[data-cookies-quitar]");
      if (linea) {
        linea.textContent = nombre
          ? str("ajustes.cookiesConArchivo").replace("{nombre}", nombre)
          : str("ajustes.cookiesSinArchivo");
      }
      if (quitar) quitar.hidden = !nombre;
    }

    function nombreDeArchivo(camino) {
      if (!camino) return "";
      var partes = String(camino).split(/[\\/]/);
      return partes[partes.length - 1] || "";
    }

    var elegir = pantalla.querySelector("[data-cookies-elegir]");
    if (elegir) elegir.addEventListener("click", function () {
      var tarjeta = tarjetaDe(elegir);
      whenReady(function () {
        window.pywebview.api.elegir_archivo_cookies().then(function (r) {
          if (!r || r.ok !== true) {
            // El puente devuelve el código del error (archivo faltante o inválido).
            if (estado && r && r.mensaje) {
              estado.textContent = r.mensaje;
              estado.setAttribute("data-error", "si");
              if (tarjeta && estado.parentNode !== tarjeta) tarjeta.appendChild(estado);
            } else {
              avisar("ajustes.error", tarjeta);
            }
            return;
          }
          if (!r.data || !r.data.archivo) return;      // canceló el selector
          pintarArchivo(nombreDeArchivo(r.data.archivo));
          avisar("ajustes.guardado", tarjeta);
        });
      });
    });

    var quitarArchivo = pantalla.querySelector("[data-cookies-quitar]");
    if (quitarArchivo) quitarArchivo.addEventListener("click", function () {
      var tarjeta = tarjetaDe(quitarArchivo);
      whenReady(function () {
        window.pywebview.api.quitar_archivo_cookies().then(function (r) {
          if (!r || r.ok !== true) { avisar("ajustes.error", tarjeta); return; }
          pintarArchivo("");
          avisar("ajustes.guardado", tarjeta);
        });
      });
    });

    var appBuscar = pantalla.querySelector("[data-app-buscar]");
    if (appBuscar) appBuscar.addEventListener("click", function () {
      var estadoApp = pantalla.querySelector("[data-app-estado]");
      whenReady(function () {
        window.pywebview.api.comprobar_actualizacion_app().then(function (r) {
          if (!estadoApp) return;
          if (!r || r.ok !== true || r.data.configurado !== true) {
            estadoApp.textContent = str("app.update.sinFuente");
            return;
          }
          estadoApp.textContent = str("app.update.sinNovedades");
        });
      });
    });

    whenReady(function () {
      window.pywebview.api.obtener_ajustes().then(function (r) {
        if (r && r.ok === true) pintar(r.data);
      });
    });
  }

  // ACERCA DE (Fase 5 B4 + 5C A4): todo sale de app_info o del puente.
  function iniciarAcerca() {
    var pantalla = document.querySelector(".pantalla-acerca");
    if (!pantalla) return;
    var estado = pantalla.querySelector("[data-acerca-estado]");
    var lista = pantalla.querySelector("[data-acerca-lista]");
    var detalles = pantalla.querySelector("[data-acerca-detalles]");
    var lleno = false;

    function poner(selector, texto) {
      var el = pantalla.querySelector(selector);
      if (el) el.textContent = texto == null ? "" : String(texto);
    }

    function avisar(clave) {
      if (estado) estado.textContent = clave ? str(clave) : "";
    }

    function abrir(metodo, claveError, argumento) {
      pedirPuente(metodo, argumento ? [argumento] : [], function (r) {
        avisar(r && r.ok === true ? "" : claveError);
      });
    }

    function llenarDetalles() {
      if (lleno) return;
      lleno = true;
      pedirPuente("detalles_tecnicos", [window.MiaukiIDIOMA || "es"], function (r) {
        if (!r || r.ok !== true || !Array.isArray(r.data) || !lista) {
          lleno = false;
          return;
        }
        r.data.forEach(function (linea) {
          var li = document.createElement("li");
          li.textContent = linea;
          lista.appendChild(li);
        });
      });
    }

    whenReady(function () {
      window.pywebview.api.info(window.MiaukiIDIOMA || "es").then(function (r) {
        if (!r || r.ok !== true || !r.data) return;
        poner("[data-acerca-nombre]", r.data.nombre);
        poner("[data-acerca-version]", "v" + r.data.version + " · " + r.data.anio);
        poner("[data-acerca-descripcion]", r.data.descripcion);
        poner("[data-acerca-gracias]", r.data.texto_gracias);
        poner("[data-acerca-legal]", r.data.texto_legal);
        if (r.data.licencia) poner("[data-acerca-licencia]", r.data.licencia);
        var alias = r.data.donacion && r.data.donacion.alias;
        poner("[data-apoyar-alias]", alias || "");
        var copiar = pantalla.querySelector("[data-apoyar-copiar]");
        if (copiar) copiar.hidden = !alias;
        var usdt = r.data.donacion && r.data.donacion.usdt;
        poner("[data-apoyar-usdt-dato]", usdt || "");
        var copiarUsdt = pantalla.querySelector("[data-apoyar-usdt]");
        if (copiarUsdt) copiarUsdt.hidden = !usdt;
        var apoyo = pantalla.querySelector("[data-acerca-apoyo]");
        if (apoyo) apoyo.hidden = !(r.data.enlaces && r.data.enlaces.paypal && alias) && !usdt;
      });
    });

    var instagram = pantalla.querySelector("[data-acerca-instagram]");
    if (instagram) instagram.addEventListener("click", function () {
      abrir("abrir_enlace", "acerca.errorEnlace", "instagram");
    });
    var registros = pantalla.querySelector("[data-acerca-registros]");
    if (registros) registros.addEventListener("click", function () {
      abrir("abrir_registros", "acerca.errorRegistros");
    });
    var facebook = pantalla.querySelector("[data-acerca-facebook]");
    if (facebook) facebook.addEventListener("click", function () {
      abrir("abrir_enlace", "acerca.errorEnlace", "facebook");
    });
    var licencias = pantalla.querySelector("[data-acerca-licencias]");
    if (licencias) licencias.addEventListener("click", function () {
      abrir("abrir_enlace", "acerca.errorEnlace", "licencias");
    });
    // Donación (09/11/2026): PayPal por la lista blanca de Python y el alias
    // de transferencia copiado por el puente (el JS nunca arma el texto).
    var paypal = pantalla.querySelector("[data-apoyar-paypal]");
    if (paypal) paypal.addEventListener("click", function () {
      abrir("abrir_enlace", "acerca.errorEnlace", "paypal");
    });
    var copiarAlias = pantalla.querySelector("[data-apoyar-copiar]");
    if (copiarAlias) copiarAlias.addEventListener("click", function () {
      pedirPuente("copiar_alias", [], function (r) {
        if (r && r.ok === true && r.data && r.data.copiado) avisar("apoyar.copiado");
        else avisar("apoyar.sinCopiar");
      });
    });
    var copiarUsdt = pantalla.querySelector("[data-apoyar-usdt]");
    if (copiarUsdt) copiarUsdt.addEventListener("click", function () {
      pedirPuente("copiar_usdt", [], function (r) {
        if (r && r.ok === true && r.data && r.data.copiado) avisar("apoyar.copiado");
        else avisar("apoyar.sinCopiar");
      });
    });
    // Acceso chiquito al pie de la barra lateral: lleva a Acerca de.
    var apoyar = document.querySelector("[data-apoyar]");
    if (apoyar) apoyar.addEventListener("click", function () {
      mostrarPantalla("acerca");
      if (paypal) paypal.focus();
    });
    if (detalles) detalles.addEventListener("toggle", function () {
      if (detalles.open) llenarDetalles();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    aplicarTextos();
    iniciarTooltips();
    abreviarRutas();
    window.addEventListener("resize", abreviarRutas);
    iniciarPaso1();
    iniciarSegmentados();
    iniciarMasOpciones();
    iniciarSubs();
    iniciarColumnaDerecha();
    iniciarGlobalesCola();
    iniciarCierreVista();
    iniciarTraba();
    cargarAjustes();
    cargarColaInicial();
    iniciarAjustes();
    iniciarAcerca();
    iniciarMotor();
    iniciarPegado();
    iniciarSoltar();
    iniciarArrastreBarra();
    iniciarRecorrido();
    iniciarHistorial();
    var miauk = botonMiauk();
    if (miauk) miauk.addEventListener("click", encolar);

    // Pantalla de lista de reproducción (plan de playlists, Paso 5).
    var plMiauk = document.querySelector("[data-pl-miauk]");
    if (plMiauk) plMiauk.addEventListener("click", encolarPlaylist);
    var plTodos = document.querySelector("[data-pl-todos]");
    if (plTodos) plTodos.addEventListener("change", function () {
      var marcado = plTodos.checked;
      document.querySelectorAll("[data-pl-lista] input[data-pl-idx]")
        .forEach(function (c) { c.checked = marcado; });
      pintarPlaylistSeleccion();
    });

    var cerrar = document.querySelector("[data-cerrar-barra]");
    if (cerrar) cerrar.addEventListener("click", ocultarBarraPortapapeles);

    var irAjustes = document.querySelector("[data-error-ajustes]");
    if (irAjustes) irAjustes.addEventListener("click", function () {
      mostrarPantalla("ajustes");
    });

    // A3: la barra flotante se descarta con teclado (Escape), sin atrapar foco.
    document.addEventListener("keydown", function (evento) {
      if (evento.key !== "Escape") return;
      var barra = document.querySelector(".barra-inferior");
      if (barra && !barra.inert) ocultarBarraPortapapeles();
    });

    var usar = document.querySelector(".barra-miauk");
    if (usar) usar.addEventListener("click", usarLinkDeBarra);

    var pegar = document.querySelector(".campo-pegar");
    if (pegar) pegar.addEventListener("click", pegarDelPortapapeles);

    revisarPortapapeles();
    window.addEventListener("focus", revisarPortapapeles);

    var verCola = document.querySelector("[data-ver-cola]");
    if (verCola) verCola.addEventListener("click", function () {
      ocultarAvisoCola();
      mostrarPantalla("cola");
    });

    // "Limpiar" de la Cola (F5: antes no hacía nada): saca las terminadas
    // y las canceladas; el evento "cola" repinta la lista.
    var limpiarCola = document.querySelector("[data-cola-limpiar]");
    if (limpiarCola) limpiarCola.addEventListener("click", function () {
      whenReady(function () {
        window.pywebview.api.limpiar_descargas().then(function (r) {
          if (r && r.ok === true) cargarColaInicial();
        });
      });
    });

    // Maqueta de la barra: solo con ?portapapeles=1 (el .exe nunca la muestra).
    if (/[?&]portapapeles=1/.test(window.location.search)) {
      mostrarBarraPortapapeles(str("barra.demoUrl"));
    }

    var nav = document.querySelector(".nav-lateral");
    if (!nav) return;
    // Los <button> ya responden a Enter y Espacio con un clic nativo;
    // acá solo nos quedamos con el clic para mover la píldora.
    nav.addEventListener("click", function (evento) {
      var item = evento.target.closest(".nav-item");
      if (item) seleccionar(item);
    });
  });
})();
