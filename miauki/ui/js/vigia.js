/* Watchdog suave (tanda 20/11/2026, paso 2).
   Si el puente de pywebview deja de contestar y no hay trabajo en curso,
   aparece un cartel con "Refrescar" y "Seguir esperando". No recarga nada
   solo: el cartel se va solo si el puente vuelve a contestar.
   No conoce el DOM ni el puente: recibe consultar(), trabajando() y dos
   avisos. Así se puede probar en serio (tests/test_traba.py). */
(function (raiz) {
  "use strict";

  // espera: ms sin respuesta para avisar; cada: ms entre latidos.
  function crear(opciones) {
    var o = opciones || {};
    var espera = o.espera || 10000;
    var cada = o.cada || 5000;
    var consultar = o.consultar;
    var trabajando = o.trabajando || function () { return false; };
    var alAvisar = o.alAvisar || function () {};
    var alVolver = o.alVolver || function () {};
    var pendienteDesde = 0;
    var avisando = false;
    var temporizador = null;

    function latir() {
      var ahora = Date.now();
      // Durante análisis o descargas no se molesta: el avance es la señal.
      if (!trabajando()) {
        if (!pendienteDesde && !avisando) {
          pendienteDesde = ahora;
          consultar().then(function () {
            pendienteDesde = 0;
            if (avisando) {
              avisando = false;
              alVolver();
            }
          }, function () {
            // Un rechazo es una respuesta: la app está viva.
            pendienteDesde = 0;
          });
        } else if (!avisando && ahora - pendienteDesde >= espera) {
          avisando = true;
          alAvisar();
        }
      }
      temporizador = setTimeout(latir, cada);
    }

    return {
      iniciar: function () {
        if (temporizador) return;
        temporizador = setTimeout(latir, cada);
      },
      detener: function () {
        if (temporizador) clearTimeout(temporizador);
        temporizador = null;
      },
      avisando: function () { return avisando; }
    };
  }

  raiz.MiaukiVigia = { crear: crear };
})(typeof window !== "undefined" ? window : globalThis);
