"""Regenera las capturas de docs/img/ con la aplicación en marcha (`ARRANCAR.bat`).

Abre Edge o Chrome sin ventana, ejecuta un caso de demostración como lo haría una
persona y guarda las vistas Cliente, Analista y «Cómo funciona».

    python scripts/capturas.py [--caso "WhatsApp"] [--pregunta "..."]
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from diputado import config  # noqa: E402

OUT = ROOT / "docs" / "img"
PORT = 9333
BROWSERS = [
    Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
]


class Page:
    def __init__(self, ws_url: str):
        self.ws = connect(ws_url, max_size=2**28, open_timeout=30, ping_interval=None)
        self.n = 0

    def send(self, method: str, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv(timeout=600))
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expr: str):
        r = self.send("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        return r.get("result", {}).get("value")

    def wait(self, expr: str, timeout: float, every: float = 1.0) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.js(expr):
                return True
            time.sleep(every)
        return False

    def click_text(self, selector: str, text: str) -> bool:
        return self.js(f"""(() => {{ const el = [...document.querySelectorAll({json.dumps(selector)})]
            .find(e => e.innerText && e.innerText.includes({json.dumps(text)})); if (el) {{ el.click(); return true; }} return false; }})()""")

    def shot(self, name: str, width: int = 1400) -> Path:
        h = self.js("Math.ceil(document.documentElement.scrollHeight)")
        self.send("Emulation.setDeviceMetricsOverride", width=width, height=h, deviceScaleFactor=1.5, mobile=False)
        time.sleep(1.5)
        data = self.send("Page.captureScreenshot", format="png", captureBeyondViewport=True)["data"]
        self.send("Emulation.setDeviceMetricsOverride", width=width, height=1000, deviceScaleFactor=1.5, mobile=False)
        path = OUT / f"{name}.png"
        path.write_bytes(base64.b64decode(data))
        print("  ✓", path.relative_to(ROOT), f"({h} px de alto)")
        return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--caso", default="WhatsApp", help="texto del caso de demostración a ejecutar")
    ap.add_argument("--pregunta", default="¿Cuántas estafas en rojo hemos detectado por canal?")
    ap.add_argument("--url", default=f"http://127.0.0.1:{config.APP_PORT}/?__theme=light")
    args = ap.parse_args()

    exe = next((b for b in BROWSERS if b.exists()), None) or shutil.which("msedge") or shutil.which("chrome")
    if not exe:
        sys.exit("No encuentro Edge ni Chrome.")
    OUT.mkdir(parents=True, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="dd_capturas_")
    proc = subprocess.Popen([str(exe), "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
                             "--window-size=1400,1000", "--hide-scrollbars", "--mute-audio", "--lang=es-ES",
                             "--accept-lang=es-ES,es", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=2))
                page_t = next(t for t in targets if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.5)
        else:
            sys.exit("El navegador no ha arrancado.")
        p = Page(page_t["webSocketDebuggerUrl"])
        p.send("Page.enable")
        p.send("Emulation.setLocaleOverride", locale="es-ES")
        p.send("Network.setUserAgentOverride", userAgent=p.js("navigator.userAgent") or "Mozilla/5.0", acceptLanguage="es-ES,es")
        p.send("Emulation.setDeviceMetricsOverride", width=1400, height=1000, deviceScaleFactor=1.5, mobile=False)
        p.send("Page.navigate", url=args.url)
        if not p.wait("!!document.querySelector('#dd-analyze')", 60):
            sys.exit(f"La aplicación no responde en {args.url}. ¿Está arrancada?")
        print("Esperando a que los modelos estén listos…")
        p.wait("(document.querySelector('#dd-status')||{}).innerText?.includes('Todo listo')", 900, 3)

        print(f"Cliente: caso «{args.caso}»")
        if not p.click_text("label:has(input[type=radio])", args.caso):
            sys.exit(f"No encuentro el caso «{args.caso}».")
        time.sleep(3)
        p.js("document.querySelector('#dd-analyze').click()")
        t0 = time.time()
        if not p.wait("!!document.querySelector('.dd-progress .dd-spin')", 60, 0.5):
            sys.exit("El análisis no ha empezado: ¿se ha cargado el caso de demostración?")
        done = ("(() => { const p = document.querySelector('.dd-progress'); return p && !p.querySelector('.dd-spin')"
                " && !!p.querySelector('.dd-chip') && !!document.querySelector('video'); })()")
        if not p.wait(done, 900, 2):
            print("  (aviso) el análisis no ha terminado en 15 min; capturamos el estado actual")
        print(f"  análisis completo en {time.time() - t0:.0f} s")
        p.js("document.querySelectorAll('audio, video').forEach(m => m.pause()); window.scrollTo(0, 0)")
        p.shot("cliente")

        print("Analista")
        p.click_text("button[role=tab]", "Analista del banco")
        time.sleep(3)
        p.js(f"""(() => {{ const ta = [...document.querySelectorAll('textarea')].find(t => t.placeholder && t.closest('.block')
            && t.closest('.block').innerText.includes('Pregunta')); if (!ta) return false;
            ta.value = {json.dumps(args.pregunta)}; ta.dispatchEvent(new Event('input', {{bubbles: true}})); return true; }})()""")
        time.sleep(1)
        p.click_text("button", "Consultar")
        p.wait("!!document.querySelector('.cm-content') && document.querySelector('.cm-content').innerText.toUpperCase().includes('SELECT')", 300, 2)
        time.sleep(2)
        p.shot("analista")

        print("Cómo funciona")
        p.click_text("button[role=tab]", "Cómo funciona")
        time.sleep(3)
        p.shot("flujo")
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
