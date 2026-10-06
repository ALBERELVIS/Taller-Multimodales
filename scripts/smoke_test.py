"""Prueba de humo: ejecutamos los casos de demostración de principio a fin.

Uso:  python scripts/smoke_test.py [--sin-media] [--solo ID]

Comprueba que cada caso termina sin errores, que el semáforo coincide con el esperado
y (salvo con --sin-media) que se generan la voz, la infografía y el vídeo.
Escribe un resumen en outputs/smoke_test.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from diputado import config  # noqa: E402

config.ensure_dirs()
config.ensure_ffmpeg_on_path()

from diputado.ai import ollama_server  # noqa: E402
from diputado.core import cases_db, pipeline  # noqa: E402
from diputado.core.schemas import CaseInput  # noqa: E402
from diputado.data import demo_cases  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-media", action="store_true", help="no generar voz, infografía ni vídeo")
    ap.add_argument("--solo", default=None, help="id de un único caso")
    args = ap.parse_args()

    ollama_server.ensure_server(install_if_missing=False)
    cases_db.init()
    rows, failures = [], 0
    for c in demo_cases.load():
        if args.solo and c["id"] != args.solo:
            continue
        if c.get("audio") and not Path(c["audio_path"]).exists():
            print(f"[AVISO] {c['id']}: falta {c['audio_path']}, lo saltamos")
            continue
        t0 = time.perf_counter()
        case = CaseInput(text=c.get("texto"), image=c.get("imagen_path"), audio=c.get("audio_path"), source="smoke")
        r = pipeline.run(case)
        t_analysis = time.perf_counter() - t0
        if not args.sin_media:
            for _ in pipeline.outputs(r, video=True):
                pass
        ok = r.level == c["esperado"] and not r.errors
        if not args.sin_media:
            ok = ok and bool(r.audio_out and r.infographic and r.video)
        failures += not ok
        row = {
            "id": c["id"], "esperado": c["esperado"], "nivel": r.level, "riesgo": round(r.risk, 3),
            "analisis_s": round(t_analysis, 1), "total_s": round(time.perf_counter() - t0, 1),
            "senales": {k: round(v, 3) for k, v in r.signal_inputs.items()},
            "regla_dura": r.hard_rule, "errores": r.errors,
            "voz": r.audio_out, "infografia": r.infographic, "video": r.video,
            "etapas": [(s.etapa, s.modelo, s.ms) for s in r.timeline],
        }
        rows.append(row)
        print(f"[{' OK ' if ok else 'FALLO'}] {c['id']:<22} esperado={c['esperado']:<6} obtenido={r.level:<6} "
              f"riesgo={r.risk:.2f} análisis={t_analysis:.1f}s total={row['total_s']}s")
        for e in r.errors:
            print("        error:", e)
    out = config.OUTPUTS_DIR / "smoke_test.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(rows) - failures}/{len(rows)} casos correctos · detalle en {out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
