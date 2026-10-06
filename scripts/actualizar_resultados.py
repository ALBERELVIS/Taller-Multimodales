"""Rellena la sección de resultados del README y la diapositiva de métricas del pitch deck.

Lee los ficheros que escriben los notebooks en `artifacts/` y sustituye lo que hay entre
`<!-- RESULTADOS -->` y `<!-- /RESULTADOS -->` (README.md) y entre `<!-- METRICAS -->` y
`<!-- /METRICAS -->` (docs/pitch_deck.md). Así las cifras de la documentación salen siempre de
la última ejecución de los notebooks.

    python scripts/actualizar_resultados.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
NB = "notebooks"


def load(name: str) -> dict:
    path = ART / name
    if not path.exists():
        sys.exit(f"Falta {path}: ejecuta antes el notebook correspondiente.")
    return json.loads(path.read_text(encoding="utf-8"))


def f(x: float, d: int = 3) -> str:
    return "–" if x is None or x != x else f"{x:.{d}f}".replace(".", ",")


def replace_block(path: Path, tag: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"(<!-- {tag} -->\n).*?(\n<!-- /{tag} -->)", re.S)
    if not pattern.search(text):
        sys.exit(f"No encuentro el bloque {tag} en {path}")
    path.write_text(pattern.sub(lambda m: m.group(1) + body.strip("\n") + m.group(2), text), encoding="utf-8")
    print(f"actualizado {path.relative_to(ROOT)} ({tag})")


tn, voz, sel = load("tacticnet.json"), load("voz_sintetica.json"), load("seleccion_modelos.json")
abl, fus, bench = load("ablacion.json"), load("fusion.json"), load("benchmarks.json")

rows = {(r["configuración"], r["pesos"]): r for r in abl["ablacion"]}
CONFIGS = ["Solo reglas", "Solo TacticNet", "Solo Qwen3", "Texto: TacticNet + Qwen3 + reglas",
           "Texto + campañas (texto e imagen)", "Todo (texto + imagen + audio)", "Todo + regla dura (aplicación)"]
fin = abl["final"]
br, au = abl["bootstrap"]["a_priori"]["mejora_brier"], abl["bootstrap"]["a_priori"]["mejora_auc"]
br_loo = abl["bootstrap"]["loo"]["mejora_brier"]
significant = br[1] > 0 or au[1] > 0
LABELS = {"tacticnet": "TacticNet", "llm": "Qwen3", "reglas": "las reglas"}
best = LABELS.get(abl["bootstrap"]["mejor_individual"], abl["bootstrap"]["mejor_individual"])

sem = abl["semaforo"]
real = sorted({k for col in sem.values() for k in col})
sem_rows = [f"| {r} | " + " | ".join(str(sem.get(c, {}).get(r, 0)) for c in ("verde", "ambar", "rojo")) + " |" for r in real]
fn = sem.get("verde", {}).get("estafa", 0)
fp = sem.get("rojo", {}).get("legítimo", 0)

cmp_ = tn["comparativa"]
seeds = tn["test_manual_5_semillas"]
unseen = [e for e in voz["experimentos"] if "no visto" in e["protocolo"] and e["modelo"] == "VozSinteticaNet"]
indist = [e for e in voz["experimentos"] if "Dentro" in e["protocolo"] and e["modelo"] == "VozSinteticaNet"]

turbo = [r for r in sel["asr"] if "turbo" in r["modelo"]]
base = [r for r in sel["asr"] if r["modelo"] == "whisper-base"]
mean = lambda rs, k: sum(r[k] for r in rs) / len(rs)  # noqa: E731
ret = sel["recuperacion"]
llm = sel["llm"]
vlm = sel["vlm"]

flows = bench["flujos"]
hw = bench["hardware"].split(" · ")
hardware = f"{hw[0]} y {hw[-1]}" if len(hw) > 1 else hw[0]
up = sorted(e["AUC"] for e in unseen if e["audio"] == "telefono")
unseen_phone = f"{f(up[0], 2)}-{f(up[-1], 2)}" if len(up) > 1 else f(up[0], 2)

combo, solo_q = rows.get(("Texto: TacticNet + Qwen3 + reglas", "iniciales")), rows.get(("Solo Qwen3", "iniciales"))
if combo and solo_q and combo["Brier"] < solo_q["Brier"]:
    combo_txt = (f"En la ablación multimodal, sumar TacticNet y las reglas a Qwen3 baja el Brier de {f(solo_q['Brier'])} "
                 f"a {f(combo['Brier'])}.")
elif combo and solo_q:
    combo_txt = (f"En la ablación multimodal, sumar TacticNet y las reglas a Qwen3 no mejora el Brier ({f(solo_q['Brier'])} "
                 f"frente a {f(combo['Brier'])}): su aportación es la latencia y la explicación por tácticas.")
else:
    combo_txt = ""

readme = f"""
Todas las cifras salen de los notebooks ejecutados (`python scripts/actualizar_resultados.py` regenera esta sección).
El conjunto de prueba es un **test escrito a mano** que nunca se usa para entrenar ni para elegir umbrales.

**Detección de estafas: ¿aporta la fusión multimodal?** ({abl['casos']} casos multimodales, audio e imagen,
[notebook 05]({NB}/05_orquestacion_y_ablacion.ipynb)). AUC y F1: más es mejor; Brier: menos es mejor.

| Configuración | AUC | F1 | Brier |
|---|---|---|---|
""" + "\n".join(
    f"| {c} | {f(rows[(c, 'iniciales')]['AUC'])} | {f(rows[(c, 'iniciales')]['F1'])} | {f(rows[(c, 'iniciales')]['Brier'])} |"
    for c in CONFIGS if (c, "iniciales") in rows) + f"""
| Aplicación (pesos finales de `artifacts/fusion.json`, medidos en la misma muestra: optimista) | {f(fin['AUC'])} | {f(fin['F1'])} | {f(fin['Brier'])} |

Las filas con pesos fijados **antes** del experimento son la comparación justa. Frente a la mejor señal individual
({best}), la fusión mejora el Brier en {f(br[0])} (IC 95 % por *bootstrap* pareado: {f(br[1])} a {f(br[2])}) y el
AUC en {f(au[0])} (IC 95 %: {f(au[1])} a {f(au[2])}). """ + (
    "La mejora es significativa." if significant else
    f"Con {abl['casos']} casos la tendencia es clara, pero los intervalos todavía incluyen el cero: lo declaramos tal cual.") + f"""
Reajustar los pesos con tan pocos casos sobreajusta (validación *leave-one-out*: {f(br_loo[0])} de Brier), y por
eso los pesos finales mezclan al 50 % los ajustados con los fijados a priori. Con el semáforo de la aplicación:

| Real \\ semáforo | verde | ámbar | rojo |
|---|---|---|---|
""" + "\n".join(sem_rows) + f"""

Errores graves: **{fn} estafas en verde** y **{fp} mensajes legítimos en rojo**.

**TacticNet (Keras)** sobre el test manual de texto ([notebook 02]({NB}/02_keras_tacticnet.ipynb)):

| Modelo | F1 estafa | ROC-AUC | Brier | F1 macro tácticas |
|---|---|---|---|---|
""" + "\n".join(
    f"| {k} | {f(v['F1 estafa'])} | {f(v['ROC-AUC'])} | {f(v['Brier'])} | {f(v['F1 macro tácticas'])} |"
    for k, v in cmp_.items() if k != "TacticNet sin calibrar") + f"""

Con 5 semillas, TacticNet obtiene F1 {f(seeds['F1 estafa']['mean'])} ± {f(seeds['F1 estafa']['std'])} y AUC
{f(seeds['ROC-AUC']['mean'])} ± {f(seeds['ROC-AUC']['std'])}. Qwen3 sin entrenamiento es el mejor clasificador
individual, pero tarda segundos y necesita la GPU; TacticNet responde en milisegundos en CPU y da las 7 tácticas
calibradas para la explicación. {combo_txt}

**VozSinteticaNet (Keras)** ([notebook 03]({NB}/03_keras_voz_sintetica.ipynb)): AUC
{f(indist[0]['AUC'])} con audio limpio y {f(indist[1]['AUC'])} por canal telefónico cuando conoce los generadores;
con un **generador no visto** cae a {unseen_phone} por teléfono.
Por eso es *experimental* y en la fusión solo puede subir el riesgo. La llamada de la demo obtiene
p = {f(voz['demo_call_p'], 2)}: no la reconoce como sintética y el veredicto lo deciden el contenido y la regla dura.

**Selección de modelos** ([notebook 04]({NB}/04_seleccion_de_modelos.ipynb)):

| Tarea | Elegido | Alternativa | Resultado |
|---|---|---|---|
| Transcripción | whisper-large-v3-turbo (GPU) | whisper-base (CPU) | WER {f(mean(turbo, 'WER'), 2)} frente a {f(mean(base, 'WER'), 2)}; RTF {f(mean(turbo, 'RTF'), 2)} frente a {f(mean(base, 'RTF'), 2)} |
| Lectura de imagen | qwen2.5vl:7b | {' · '.join(k for k in vlm if k != 'qwen2.5vl:7b') or '–'} | """ + " · ".join(
    f"{k}: CER {f(v['CER'])}" + (f", enlaces exactos {v['enlace_exacto'] * 100:.0f} %" if "enlace_exacto" in v else "") + f", {f(v['s'], 1)} s"
    for k, v in vlm.items()) + f""" |
| Búsqueda visual de campañas | SigLIP2 | CLIP | Recall@3 {f(ret['siglip imagen→imagen']['Recall@3'], 2)} frente a {f(ret['clip imagen→imagen']['Recall@3'], 2)}; MRR {f(ret['siglip imagen→imagen']['MRR'], 2)} frente a {f(ret['clip imagen→imagen']['MRR'], 2)} |
| Razonamiento | qwen3:8b | qwen2.5:7b | F1 {f(llm['qwen3:8b']['F1'])} frente a {f(llm['qwen2.5:7b']['F1'])} |
| Aviso por voz | MMS-TTS | Bark | Mismo WER de ida y vuelta ({f(sel['tts']['MMS-TTS']['WER ida y vuelta'])}); RTF {f(sel['tts']['MMS-TTS']['RTF'], 2)} frente a {f(sel['tts']['Bark']['RTF'], 1)} |
| Infografía | SDXL-Turbo, 2 pasos | 1 y 4 pasos | SigLIP2 {f(sel['sdxl']['1']['SigLIP2'])} · {f(sel['sdxl']['2']['SigLIP2'])} · {f(sel['sdxl']['4']['SigLIP2'])} |

**Latencia en caliente** en un portátil con {hardware} ([notebook 06]({NB}/06_latencia_vram_costes.ipynb)); pico de VRAM
{f(bench['vram_pico_gb'], 1)} GB:

| Flujo | Veredicto | Con voz, infografía y vídeo |
|---|---|---|
""" + "\n".join(f"| {k} | {f(v['veredicto_s'], 1)} s | {f(v['total_s'], 1)} s |" for k, v in flows.items())

pitch = f"""
| Experimento | Resultado |
|---|---|
| Fusión multimodal ({abl['casos']} casos, test manual, pesos a priori) | AUC **{f(rows[('Todo + regla dura (aplicación)', 'iniciales')]['AUC'])}** frente a {f(rows[('Solo Qwen3', 'iniciales')]['AUC'])} de la mejor señal sola · Brier {f(rows[('Todo + regla dura (aplicación)', 'iniciales')]['Brier'])} frente a {f(rows[('Solo Qwen3', 'iniciales')]['Brier'])} |
| Errores graves del semáforo | {fn} estafas en verde · {fp} legítimos en rojo |
| TacticNet (Keras) | AUC {f(cmp_['TacticNet (calibrado + umbrales)']['ROC-AUC'])} frente a {f(cmp_['TF-IDF + LogReg']['ROC-AUC'])} de TF-IDF, en milisegundos en CPU; sumado a Qwen3 y las reglas, Brier de {f(solo_q['Brier'])} a {f(combo['Brier'])} |
| VozSinteticaNet (Keras) | AUC {f(indist[1]['AUC'])} por teléfono; {unseen_phone} con un generador no visto (experimental) |
| Qwen3 frente a Qwen2.5 | F1 {f(llm['qwen3:8b']['F1'])} frente a {f(llm['qwen2.5:7b']['F1'])} |
| Veredicto en caliente (portátil 8 GB) | """ + " · ".join(f"{k.split(' (')[0]} {f(v['veredicto_s'], 0)} s" for k, v in flows.items()) + " |"

replace_block(ROOT / "README.md", "RESULTADOS", readme)
replace_block(ROOT / "docs" / "pitch_deck.md", "METRICAS", pitch)
