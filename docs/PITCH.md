# Helios · pitch técnico

---

## 1. El problema

Un gestor independiente no analiza una compañía: analiza un expediente. El PDF de resultados, la captura del gráfico, la conferencia en audio y cuatro noticias no viven en el mismo sitio. Leerlos por separado es lento y es fácil citar de memoria una cifra que no está en el documento.

---

## 2. A quién

B2B. Gestor independiente y family office pequeño. No es una app de trading para particulares. El usuario ya tiene criterio; le falta una mesa que junte las pruebas.

---

## 3. Qué es Helios

Una mesa local. Subes el expediente o cargas el caso demo. Helios encadena modelos especializados y devuelve tres cosas: una tesis con citas, una infografía fiel y un briefing de voz.

El sesgo de mesa —Vigilar, Constructivo, Defensivo o Neutral— lo decide una regla sobre margen, drawdown y riesgo. El modelo de lenguaje redacta. No inventa el veredicto ni las cifras.

---

## 4. Por qué multimodal

Cada modalidad aporta una prueba distinta.

- El PDF fija ingresos, margen, capex, deuda y guía.
- El gráfico y la serie muestran la caída desde máximos.
- El audio de la conferencia confirma el riesgo operativo y se puede citar por minuto.
- La prensa repite o matiza el mismo hecho.
- La pregunta posterior busca en texto y, si habla del gráfico, también en la imagen.

Una sola llamada a un chat no enseña cuál modelo hizo qué. Helios muestra la etapa, el modelo y los segundos.

---

## 5. Por qué local

El argumento comercial es de cumplimiento. El audio de la conferencia y el PDF del cliente no salen hacia una API de pago. Transcripción, visión y redacción corren en Ollama y Whisper, en la máquina del gestor.

La voz del briefing usa, por defecto, una voz neuronal gratuita y sin clave. Se puede dejar en la voz del sistema, o apagarla, si el audio tampoco puede salir.

---

## 6. El caso que se puede medir

NorteGrid (NRGX) es ficticia. Por eso hay verdad terreno: 842 millones de ingresos, margen EBITDA del 28,4%, capex 310, deuda neta 540, guía 910-940 y un retraso de 6 meses en Cabo Prior. La serie trae un drawdown plantado del 18%.

El cuaderno de evaluación mide el acierto del extractor, el error de la transcripción, el porcentaje de cifras de la tesis que existen en las fuentes, la latencia por etapa y el coste.

---

## 7. Control de cifras

Antes de publicar, cada frase pasa un filtro. Si contiene un número que no está en el PDF, en la prensa o en la serie, la frase no sale. La interfaz dice cuántas retiró. Eso es el producto, no un apéndice.

La infografía se dibuja con código a partir de la ficha. Un modelo generativo de imagen no puede inventar un 18% que la serie no ha calculado.

---

## 8. Viabilidad

Coste marginal de un análisis en local: electricidad. A 65 W y 0,18 EUR/kWh, un análisis de unos minutos son fracciones de céntimo. El mismo encadenado de visión, texto, transcripción y voz, valorado con una tarifa hipotética de API, sale más caro y además saca el dato del despacho.

Latencia objetivo: el PDF y la infografía, al instante; visión y transcripción, por debajo de un minuto y medio en CPU; la voz, en segundos.

Ingreso: suscripción por puesto. El gestor paga por la mesa, no por token.

---

## 9. Cumplimiento

No es asesoramiento según MiFID II. El aviso va en la nota, en la lámina y en el audio. El caso demo está etiquetado como sintético. Privacidad: el expediente se procesa en local, con la excepción explícita y desactivable de la voz neuronal.

---

## 10. Qué se enseña en la defensa

1. Cargar NorteGrid y recorrer las etapas.
2. Enseñar el control de cifras al 100% en la tesis publicada.
3. Preguntar por Cabo Prior y por el drawdown, y señalar la fuente.
4. Reproducir el briefing.
5. Abrir el cuaderno de evaluación si piden el número, no la demo.
