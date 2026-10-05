# TALLER: B5-T4

## Diseño y Prototipado de una Startup FinTech basada en IA Multimodal

## Datos básicos

- **Modalidad:** Grupos de 3 estudiantes.
- **Entrega:** A través del aula virtual, fecha límite 18:00 8 Octubre 2026.
- **El entregable:** Repositorio en GitHub con el código fuente del MVP funcional.

## 1. Objetivo de la práctica

El objetivo de este proyecto es concebir, diseñar e implementar una primera versión funcional (Producto Mínimo Viable o MVP) de una startup tecnológica en el sector financiero (FinTech), cuyo producto central sea una aplicación interactiva impulsada por modelos de inteligencia artificial multimodal.

Los estudiantes deberán desarrollar una visión holística que aúne visión de negocio (propuesta de valor, viabilidad y necesidades reales de mercado) con una ingeniería de software avanzada capaz de orquestar múltiples modelos de IA (lenguaje, visión computacional, audio/voz y generación multimodal) dentro de una aplicación usable, coherente e intuitiva.

## 2. Contexto del problema

El sector financiero tradicionalmente procesa y genera información dispersa en formatos muy heterogéneos: balances e informes anuales en PDF, gráficos de velas y series temporales, conferencias de resultados y juntas de accionistas en audio, videos de opiniones, noticias de prensa y datos tabulares de mercado. La eclosión de los modelos fundacionales multimodales abre una oportunidad histórica para reinventar servicios.

No obstante, construir un producto FinTech no se limita a conectar una única API de chat conversacional, sino a articular flujos de trabajo multimodales complejos donde distintas modalidades de entrada y salida colaboren para aportar un valor diferencial tangible a un usuario final de forma ágil, fluida y tecnológicamente viable.

## 3. Entorno técnico y modelos de IA disponibles

Se fomenta la integración de modelos abiertos (Hugging Face, vLLM, Ollama), APIs comerciales (OpenAI, Anthropic, Google Gemini, Mistral, ElevenLabs, Whisper, etc.) o modelos propios, diseñados y entrenados por el grupo. Las modalidades a considerar en la solución incluyen, entre otras:

- **Texto a texto:** Razonamiento financiero, síntesis de noticias, análisis regulatorio o asesoramiento conversacional.
- **Imagen/Documento a texto (Visión):** Lectura óptica y extracción de balances contables, gráficos de cotizaciones, facturas, tickets de gastos o identificación de documentos oficiales.
- **Texto a imagen:** Generación de infografías financieras personalizadas, diagramas de composición de carteras o representaciones visuales intuitivas de riesgo.
- **Audio a texto (Voz a texto):** Transcripción e indexación de llamadas con clientes, juntas de accionistas o comandos de voz para interactuar con la aplicación.
- **Texto a audio (Voz sintetizada):** Respuestas de agentes de voz, resúmenes ejecutivos diarios por audio o podcasts financieros automatizados para el usuario.
- **Modalidades cruzadas / Búsqueda multimodal:** Indexación semántica multimodal (embeddings tipo CLIP), vídeo-análisis de webinars bursátiles o generación de reportes multimedia automatizados.

## 4. Tarea del estudiante

El equipo de trabajo deberá desarrollar la startup cubriendo los siguientes bloques:

### 4.1. Definición esquemática de la idea y propuesta de valor

- **Definición esquemática del producto:** Presentar un esquema visual y descriptivo del problema financiero a resolver, el público objetivo (B2C, B2B o B2B2C) y la propuesta de valor diferencial que aporta la multimodalidad.
- **Viabilidad técnica y económica:** Justificar la viabilidad de la solución analizando costes de inferencia y consumo de APIs, latencias requeridas para una experiencia de usuario fluida, marco regulatorio financiero (compliance, privacidad de datos bancarios) y modelo de monetización.

### 4.2. Riqueza multimodal y orquestación de modelos

- **Diversidad de modalidades:** Cuantas más modalidades de entrada y salida se integren con sentido y coherencia dentro de la aplicación, mayor será la puntuación obtenida.
- **Pluralidad y orquestación multi-modelo:** Se puntuará con mayor nota el uso y encadenamiento coordinado de múltiples modelos especializados frente a llamadas aisladas a un único modelo monolítico.

### 4.3. Desarrollo del MVP y usabilidad real

- **Primera versión ejecutable / MVP:** El proyecto debe presentar una aplicación operativa real.
- **Nivel de usabilidad e interacción real:** Se evaluará el diseño de la interfaz (UI), la fluidez de los flujos de usuario (UX), la claridad en la navegación y la robustez del sistema.
- **Despliegue y prueba Plug-and-Play:** La aplicación debe incluir scripts de arranque directo y ficheros de dependencias completos (`requirements.txt` o `Dockerfile`).

### 4.4. Repositorio de código y documentación técnica

- **README y Pitch Deck técnico:** Fichero README exhaustivo en GitHub con capturas de pantalla, diagrama de flujo de datos multimodales y descripción de la arquitectura.
- **Calidad y modularidad del código:** Separación limpia entre la capa de conexión con modelos de IA, la lógica de negocio y la interfaz de usuario.

## 5. Entregables

1. **Repositorio de GitHub:** Código fuente completo del MVP organizado de forma estructurada.
2. **Demostración funcional:** Aplicación desplegada en la nube o demo grabada/interactiva en vivo que evidencie la usabilidad y la integración real de las distintas modalidades.
