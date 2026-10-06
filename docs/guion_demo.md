# Guion de la demo (≈ 3 minutos)

Guion para grabar el vídeo de la demostración con OBS Studio (o la Xbox Game Bar de Windows, `Win + G`).
Recomendamos grabar a 1920×1080 con el navegador a pantalla completa (`F11`) y el audio del sistema activado,
porque la aplicación **habla**.

## Antes de grabar

1. Arrancamos con `ARRANCAR.bat` y esperamos a que la cabecera diga **«Todo listo · 10 componentes · 100 % local»**
   (tarda unos minutos porque precarga los modelos, incluida SDXL-Turbo).
2. Hacemos un análisis de prueba cualquiera para que todo esté «en caliente».
3. Cerramos notificaciones de Windows (modo «No molestar»).

## Escena 1 · El problema (0:00 – 0:20)

> «Cada día, miles de personas reciben una llamada de su "banco" pidiéndoles un código, un SMS de Correos con
> una tasa de 1,99 € o un WhatsApp de su "hijo" con un número nuevo. Las estafas llegan por **voz, imagen y
> texto**, y las víctimas más frecuentes son personas mayores. Somos DiputadoDetector: un escudo antifraude
> multimodal que el banco integra en su app y que funciona **100 % en local**.»

*En pantalla:* la cabecera de la aplicación y la vista Cliente.

## Escena 2 · La llamada del falso banco (0:20 – 1:00)

1. En **Casos de demostración** elegimos «Llamada del "departamento de seguridad" del banco». La pestaña cambia
   sola a «¿Me están llamando?» y se carga el audio. Le damos al *play* dos segundos para que se oiga la voz.
2. Pulsamos **Analizar ahora**.

> «La voz es sintética, generada con Bark, y ha pasado por un canal telefónico simulado. Whisper la
> transcribe, CLAP y nuestro modelo Keras VozSinteticaNet analizan cómo suena, y Qwen3 razona sobre lo que
> dice.»

3. Aparece el semáforo **rojo** y se oye el aviso por voz. Señalamos la explicación y los consejos.

> «Lo que decide aquí es el contenido: nos piden el código de seis cifras que acaba de llegar por SMS, y eso
> activa una regla dura. Nuestro detector de voz sintética no está seguro con esta voz, que no vio al
> entrenar, y lo decimos abiertamente: por diseño solo puede sumar riesgo, nunca restarlo.»

## Escena 3 · El SMS de Correos (1:00 – 1:35)

1. Elegimos «SMS de Correos: paquete retenido por 1,99 €» y pulsamos **Analizar ahora**.

> «Ahora es una captura. Qwen2.5-VL la lee como lo haría una persona, nuestras reglas detectan que el dominio
> imita a Correos y la búsqueda multimodal con SigLIP2 la reconoce como una campaña conocida.»

2. Cuando llegan, mostramos la **infografía** (SDXL-Turbo, con control de calidad automático por SigLIP2) y el
   **vídeo-alerta**, y el botón «Compartir con mi familia».

## Escena 4 · No somos paranoicos (1:35 – 1:55)

1. Elegimos «SMS legítimo del banco (aviso de compra)» y analizamos.

> «Un buen detector también tiene que saber decir que no. Este aviso informativo, sin enlaces ni peticiones,
> sale en **verde**.»

## Escena 5 · La vista del analista del banco (1:55 – 2:40)

1. Pasamos a la pestaña **Analista del banco**.
2. Mostramos la **cronología del pipeline** (cada modelo con su latencia), el gráfico de **contribución de cada
   señal** (explicabilidad), las frases resaltadas y la galería de **campañas parecidas**.
3. Bajamos al panel y escribimos o elegimos: *«¿Cuáles son las 5 campañas más frecuentes este mes?»*.

> «El equipo de fraude puede preguntar a los datos en lenguaje natural. Un agente de smolagents con Qwen2.5
> escribe el SQL, que se ejecuta sobre una conexión de solo lectura.»

## Escena 6 · Pregúntame y cierre (2:40 – 3:00)

1. Volvemos a **Cliente → Pregúntame** y grabamos con el micrófono: *«¿Es normal que mi banco me pida el PIN por
   teléfono?»*. Se oye la respuesta.
2. Cierre:

> «Doce modelos coordinados, dos entrenados por nosotros en Keras, cinco modalidades de entrada y salida, y
> ningún dato sale del banco. DiputadoDetector: antes de pagar, de dar un código o de devolver una llamada,
> pregúntanos.»

*En pantalla:* la pestaña **Cómo funciona** con el diagrama de la arquitectura.

## Plan B

Si algo falla en directo, cada caso de demo es reproducible y podemos repetirlo. `scripts/smoke_test.py`
ejecuta los cinco casos de principio a fin y comprueba que el semáforo es el esperado.
