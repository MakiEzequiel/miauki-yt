// Puente con Python: comunicación Python↔JS (todas las fases).
//
// whenReady(cb): ejecuta cb cuando pywebview ya está disponible.
//   Ojo 1: pywebview.api aparece como objeto VACÍO antes de cargar los métodos,
//   por eso se chequea un método concreto (ping), no solo la existencia de api.
//   Ojo 2: pywebview despacha 'pywebviewready' en window (js/finish.js),
//   NO en document: hay que escuchar en window, si no nunca llega.
//   Uso: whenReady(function () { pywebview.api.ping()... });
// Reparto de eventos Python→JS (cola/progreso, decisión 3d.11): cada
// evento se pasa a su manejador registrado en window.MiaukiManejadores.
window.miaukiEventos = function (carga) {
  if (!carga || typeof carga !== "object") return;
  var manejadores = window.MiaukiManejadores || {};
  var fn = manejadores[carga.evento];
  if (typeof fn === "function") fn(carga.datos);
};

function whenReady(cb) {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.ping) {
    cb();
  } else {
    window.addEventListener("pywebviewready", function escucha() {
      window.removeEventListener("pywebviewready", escucha);
      cb();
    });
  }
}
window.whenReady = whenReady;
