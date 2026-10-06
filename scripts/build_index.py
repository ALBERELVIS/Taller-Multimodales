"""Prepara los datos locales: capturas e índice de campañas, base de casos y casos de demo."""

from __future__ import annotations

import sys

from diputado import config
from diputado.core import campaigns, cases_db
from diputado.data import demo_cases


def main() -> int:
    config.ensure_dirs()
    print("  Índice de campañas conocidas (e5 + SigLIP2)...")
    campaigns.build_index()
    print("  Base de casos con histórico sintético...")
    cases_db.init()
    if not all((config.DEMO_DIR / c["imagen"]).exists() for c in demo_cases.CASES if c.get("imagen")):
        print("  Capturas de la demo...")
        demo_cases.build_images()
    demo_cases.save_manifest()
    print("  Datos listos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
