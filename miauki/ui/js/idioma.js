// Elige el idioma de la interfaz antes de que app.js aplique los textos.
// Prioridad (tanda 22/11/2026, paso 6): el idioma elegido en Ajustes (guardado
// acá abajo), después `?idioma=en` (atajo de prueba) y, si no hay nada
// elegido, el idioma de Windows (navigator.language en WebView2).
(function () {
  var CLAVE = "miauki.idioma";

  function leerGuardado() {
    try {
      return window.localStorage.getItem(CLAVE) || "";
    } catch (e) {
      return "";   // sin almacenamiento local: manda el idioma del sistema
    }
  }

  // La usa app.js cuando el ajuste guardado no coincide con el que se aplicó.
  function guardar(idioma) {
    try {
      window.localStorage.setItem(CLAVE, idioma);
      return true;
    } catch (e) {
      return false;  // el ajuste real vive en Python; esto es solo caché
    }
  }

  var pedido = "";
  try {
    pedido = new URLSearchParams(window.location.search).get("idioma") || "";
  } catch (e) {
    pedido = "";
  }
  // `?idioma=` manda sobre la copia guardada: app.js recarga con ese parámetro
  // (auditoría 23/11: en el .exe el almacenamiento local no siempre persiste).
  var elegido = (pedido || leerGuardado()).toLowerCase();
  var idioma = elegido
    ? (elegido.indexOf("en") === 0 ? "en" : "es")
    : ((navigator.language || "es").toLowerCase().indexOf("es") === 0 ? "es" : "en");
  window.MiaukiIDIOMA = idioma;
  window.MiaukiIdioma = { actual: idioma, guardar: guardar };
  if (idioma === "en" && window.MiaukiSTR_EN) window.MiaukiSTR = window.MiaukiSTR_EN;
  document.documentElement.lang = idioma;
})();
