analisis_tecnico.py

Resumen breve del modelo GRU  
Tu modelo es una red neuronal recurrente pensada para series de tiempo (precios). La idea es: mirar una ventana de datos pasados y aprender patrones temporales para predecir valores futuros.

Cómo funciona el tuyo (paso a paso)
1. Descarga precios históricos con Yahoo Finance en analisis_tecnico.py.  
2. Escala el precio de cierre a rango 0-1 con MinMaxScaler en analisis_tecnico.py.  
3. Construye secuencias usando lookback y pred_len en analisis_tecnico.py.  
4. Divide en entrenamiento y prueba en analisis_tecnico.py.  
5. Entrena el modelo GRU con EarlyStopping en analisis_tecnico.py.  
6. Evalúa con MAE y RMSE en analisis_tecnico.py.  

Arquitectura exacta que tienes
Está definida en analisis_tecnico.py.

Capas:
1. Input(shape=(lookback, 1))  
2. GRU(64, return_sequences=True)  
3. Dropout(0.2)  
4. GRU(32)  
5. Dropout(0.2)  
6. Dense(16, activation="relu")  
7. Dense(pred_len)

Interpretación rápida:
- Capas totales: 7 (incluyendo Input y Dropout).
- Capas entrenables principales: 4 (2 GRU + 2 Dense).
- Unidades:
1. Primera GRU: 64
2. Segunda GRU: 32
3. Dense intermedia: 16
4. Salida: pred_len (por defecto 7)

Qué es cada concepto
- Dropout: durante entrenamiento apaga aleatoriamente un porcentaje de neuronas (aquí 20%) para reducir sobreajuste. Está en analisis_tecnico.py.  
- Dense: capa totalmente conectada que combina lo aprendido para producir la salida final. Está en analisis_tecnico.py.  
- Optimizer: algoritmo que ajusta los pesos para minimizar el error. En tu caso es Adam, en analisis_tecnico.py.  
- Loss: función que mide qué tan mal predice el modelo. En tu caso es mean_squared_error (MSE), también en analisis_tecnico.py.  

Parámetros por defecto actuales
Están en la firma de la función analisis_tecnico.py:
1. lookback = 343
2. pred_len = 7
3. test_size = 0.15
4. epochs = 30
5. batch_size = 32

Si quieres, te explico ahora cómo elegir buenos valores de lookback y pred_len para tu acción específica (por ejemplo PFAVAL.CL) sin sobreentrenar.

Perfecto. Para tu caso (acciones como PFAVAL.CL), la elección de `lookback` y `pred_len` define el equilibrio entre memoria útil y ruido.

**Idea clave**
- `lookback`: cuántos días pasados mira el modelo.
- `pred_len`: cuántos días hacia adelante intenta predecir.

Mientras más largo sea el horizonte (`pred_len`), más difícil y menos precisa suele ser la predicción.

**Cómo elegir `lookback` (regla práctica)**
1. Empieza con valores moderados: 30, 60, 90.
2. Si el activo tiene ciclos más lentos, prueba 120 o 180.
3. Evita arrancar de una con 343 porque:
- aumenta costo de entrenamiento,
- puede meter demasiado ruido histórico,
- sube riesgo de sobreajuste si no hay suficientes datos.

Para acciones locales con liquidez media, un buen rango inicial suele ser:
- `lookback` entre 60 y 120.

**Cómo elegir `pred_len`**
1. Si quieres señales tácticas de corto plazo: usa 1 a 3.
2. Si quieres visión semanal: usa 5 a 7.
3. Más de 10-15 días en GRU simple suele degradar bastante.

Rango recomendado para empezar:
- `pred_len` entre 1 y 5.
- Si necesitas 7, úsalo, pero espera mayor error.

**Combinaciones iniciales recomendadas**
1. `lookback=60`, `pred_len=1` (baseline robusto)
2. `lookback=90`, `pred_len=3` (compromiso)
3. `lookback=120`, `pred_len=5` (horizonte algo mayor)

**Cómo detectar sobreentrenamiento en tu entrenamiento**
Mira estas señales:
1. `loss` de entrenamiento baja, pero `val_loss` deja de bajar o sube.
2. `best_val_loss` ocurre muy temprano y luego empeora.
3. Muy buen resultado en train, pero MAE/RMSE flojo en test.

**Qué hacer para evitar sobreajuste**
1. Mantén `EarlyStopping` (ya lo tienes, excelente).
2. No subas demasiado epochs; 20-40 suele ser buen inicio.
3. Conserva Dropout (0.2 está bien para comenzar).
4. No uses `lookback` excesivo si no tienes años de datos limpios.
5. Evalúa siempre en ventana temporal futura (como ya haces con split final).
6. Opcional útil: prueba una métrica naive como “mañana = hoy” para comparar si GRU realmente aporta.

**Setup recomendado para tu siguiente prueba**
1. `lookback=90`
2. `pred_len=3`
3. `epochs=30`
4. `batch_size=32`
5. `test_size=0.2` (si quieres evaluación un poco más exigente)

Si quieres, te propongo una mini tabla de experimentos (3 corridas) y te digo exactamente cómo decidir el ganador sin sesgo.

Excelente. Aquí tienes una mini tabla de 3 corridas y una regla objetiva para elegir el ganador sin sesgo.

Plan de experimentos (mantén fijo `epochs=30`, `batch_size=32`, `test_size=0.2`)
1. Experimento A: `lookback=60`, `pred_len=1`
2. Experimento B: `lookback=90`, `pred_len=3`
3. Experimento C: `lookback=120`, `pred_len=5`

Qué registrar en cada corrida
1. `MAE`
2. `RMSE`
3. `best_val_loss`
4. `epochs_trained` (cuándo paró EarlyStopping)
5. Tiempo de entrenamiento (opcional, pero útil)

Regla de decisión sin sesgo
1. Prioriza el menor `RMSE` en test.
2. Si la diferencia de RMSE entre dos modelos es menor a 5%, elige el de menor `MAE`.
3. Si todavía están muy parejos, elige el más simple/rápido (menor `lookback` o menor tiempo).
4. Descarta cualquier modelo donde:
- `val_loss` sea inestable o suba claramente al final,
- o `epochs_trained` sea muy bajo por parada temprana con mal RMSE.

Lectura rápida esperada
1. A suele ganar en precisión inmediata (corto plazo).
2. B suele ser mejor compromiso entre estabilidad y horizonte.
3. C suele capturar más contexto, pero puede meter ruido y tardar más.

Si quieres, te doy una plantilla de tabla para que solo pegues los resultados y te digo cuál gana automáticamente.

Muy buena pregunta. Te lo explico directo y simple:

1. `GRU(64)` y `GRU(32)`  
- Esos números son la cantidad de unidades/neuronas ocultas de cada capa GRU.  
- `64` significa: esa capa aprende 64 “features temporales” internas.  
- `32` significa: la segunda capa resume en 32 features.  
- Más unidades = más capacidad para aprender patrones, pero más riesgo de sobreajuste y más costo computacional.

2. `return_sequences=True` o `False`
- `True`: la capa devuelve toda la secuencia temporal, o sea una salida por cada paso del tiempo.
  - Forma típica: `(batch, timesteps, units)`
- `False`: devuelve solo el último estado temporal (el resumen final).
  - Forma típica: `(batch, units)`

Por eso en tu arquitectura:
- primera GRU usa `return_sequences=True` para pasar toda la secuencia a la segunda GRU,
- segunda GRU usa `False` para entregar un vector resumen a las capas Dense.

3. `input_shape=(ventana, 1)`
- `ventana` = cuántos pasos de tiempo entran (lookback).
- `1` = cuántas features por paso temporal (en tu caso solo `Close`).
- Si usaras más variables por día (por ejemplo `Close`, `Volume`, `High`), sería algo como `input_shape=(ventana, 3)`.

4. Otros optimizers comunes (además de `adam`)
- `SGD`: simple y estable, a veces requiere más tuning de learning rate.
- `RMSprop`: muy usado en RNNs clásicas.
- `AdamW`: variante moderna de Adam con mejor regularización (weight decay).
- `Adagrad`: adapta learning rate por parámetro, útil en ciertos casos dispersos.
- `Adadelta`, `Nadam`, `Ftrl`: menos comunes, pero disponibles.

Para series de tiempo con GRU/LSTM, normalmente se prueba:
1. `Adam` (baseline)
2. `RMSprop`
3. `AdamW`

5. Otros loss comunes para regresión (además de `mean_squared_error`)
- `MAE` (`mean_absolute_error`): menos sensible a outliers.
- `Huber`: mezcla ventajas de MSE y MAE, muy buena opción robusta.
- `MSLE`: útil cuando importan errores relativos/logarítmicos.
- `MAPE`: error porcentual (cuidado si hay valores cercanos a cero).

Recomendación práctica para tu caso:
1. Empieza con `optimizer="adam"` y `loss="huber"` si tienes picos/ruido.
2. Si quieres castigar fuerte errores grandes, usa `loss="mse"`.
3. Si quieres robustez contra outliers, `loss="mae"` o `huber`.

Si quieres, te propongo 3 combinaciones optimizer/loss para probar en tu GRU y te digo cuál conviene según el comportamiento que veas en MAE/RMSE.