# -*- coding: utf-8 -*-
"""Chequeo de accesibilidad en la ventana REAL (spec 2D.3 §2).

Levanta la interfaz en pywebview + WebView2 (mismo stack que la app), espera
a que cargue y recorre el DOM vivo: TODO elemento interactivo tiene que tener
nombre accesible (aria-labelledby, aria-label, etiqueta <label>, texto
visible, title, placeholder o alt). A diferencia del test estático, acá se ve
lo que el navegador realmente computa: textos inyectados por JS, etiquetas
envolventes, aria-describedby, etc.

Uso (desde la raíz del proyecto):
    python tools/check_a11y_vivo.py

Sale con 0 si todos tienen nombre, 1 si falta alguno (imprime cuál).
"""
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import _entorno  # noqa: E402  (carpeta de datos temporal, nunca la real)

import webview  # noqa: E402

from miauki import paths  # noqa: E402
from miauki.api import Api  # noqa: E402

JS = """(function(){
  function texto(nodo, salto){
    var res = "";
    (function recorrer(n){
      for (var c = n.firstChild; c; c = c.nextSibling){
        if (c.nodeType === 3){ res += c.nodeValue; continue; }
        if (c.nodeType !== 1) continue;
        if (c === salto) continue;
        if (c.getAttribute && c.getAttribute("aria-hidden") === "true") continue;
        if (c.tagName === "IMG"){ var alt = c.getAttribute("alt"); if (alt) res += " " + alt; continue; }
        if (c.tagName === "INPUT" || c.tagName === "TEXTAREA" || c.tagName === "SELECT") continue;
        recorrer(c);
      }
    })(nodo);
    return res.replace(/\\s+/g, " ").trim();
  }
  function nombre(el){
    var lb = el.getAttribute("aria-labelledby");
    if (lb){
      var t = lb.split(/\\s+/).map(function(id){
        var n = document.getElementById(id);
        return n ? texto(n, null) : "";
      }).join(" ").replace(/\\s+/g, " ").trim();
      if (t) return t;
    }
    var al = (el.getAttribute("aria-label") || "").trim();
    if (al) return al;
    var etiqueta = (el.labels && el.labels.length) ? el.labels[0] : el.closest("label");
    if (etiqueta){
      var tl = texto(etiqueta, el);
      if (tl) return tl;
    }
    var tp = texto(el, null);
    if (tp) return tp;
    var extras = ["title", "placeholder", "alt"];
    for (var i = 0; i < extras.length; i++){
      var v = (el.getAttribute(extras[i]) || "").trim();
      if (v) return v;
    }
    return "";
  }
  var sel = 'button, a[href], input, select, textarea, ' +
            '[role="radio"], [role="switch"], [role="checkbox"], [role="link"], ' +
            '[role="button"], [role="tab"], [role="menuitem"], [role="option"], [role="slider"]';
  var piezas = [];
  document.querySelectorAll(sel).forEach(function(el){
    var clase = (typeof el.className === "string" && el.className.trim())
      ? "." + el.className.trim().split(/\\s+/).join(".") : "";
    piezas.push({
      q: (el.id ? "#" + el.id : el.tagName.toLowerCase() + clase),
      nombre: nombre(el),
      detalle: (el.getAttribute("aria-label") || el.textContent || "").replace(/\\s+/g, " ").trim().slice(0, 60)
    });
  });
  return JSON.stringify({
    total: piezas.length,
    sinNombre: piezas.filter(function(p){ return !p.nombre; }),
    piezas: piezas
  });
})()"""


def main() -> int:
    ruta, fuente = paths.fuente_interfaz()
    if not ruta.is_file():
        print(f"Falta la interfaz: {ruta}", file=sys.stderr)
        return 1

    ventana = webview.create_window(
        "chequeo a11y vivo", url=str(ruta), js_api=Api(),
        width=1600, height=900, resizable=False,
    )
    res = {}

    def trabajo():
        time.sleep(2.5)
        crudo = ventana.evaluate_js(JS)
        res["datos"] = json.loads(crudo) if isinstance(crudo, str) else crudo
        ventana.destroy()

    webview.start(gui="edgechromium", func=trabajo)

    datos = res.get("datos") or {}
    piezas = datos.get("piezas", [])
    sin = datos.get("sinNombre", [])

    print(f"Interfaz {fuente}: {datos.get('total', 0)} interactivos en el DOM vivo")
    for p in piezas:
        marca = "OK   " if p["nombre"] else "FALLO"
        print(f"[{marca}] {p['q'][:52]:<52} -> {p['nombre'] or '(sin nombre)'}")
    if sin:
        print(f"\n{len(sin)} interactivo(s) SIN nombre accesible.", file=sys.stderr)
        return 1
    print("\nTodos los interactivos tienen nombre accesible en la ventana real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
