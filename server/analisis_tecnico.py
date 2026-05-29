from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import GRU, Dense, Dropout, Input
from tensorflow.keras.models import Sequential


COLUMNA_OBJETIVO = "close"

def run_gru_prediction(
    ticker: str,
    start_date: str,
    end_date: str,
    lookback: int = 343,
    pred_len: int = 7,
    test_size: float = 0.15,
    epochs: int = 30,
    batch_size: int = 32
):

    if not ticker or not isinstance(ticker, str):
        raise ValueError("ticker debe ser un string no vacío")
    if lookback < 2:
        raise ValueError("lookback debe ser al menos 2")
    if pred_len < 1:
        raise ValueError("pred_len debe ser al menos 1")
    if not 0 < test_size < 1:
        raise ValueError("test_size debe estar entre 0 y 1")
    if epochs < 1 or batch_size < 1:
        raise ValueError("epochs y batch_size deben ser enteros positivos")

    # ========================================================
    # DOWNLOAD DATA
    # ========================================================

    df = yf.download(
        ticker,
        start=start_date,
        end=end_date
    )

    # df = yf.download(
    #     ticker,
    #     start=start_date,
    #     end=end_date,
    #     progress=False,
    #     auto_adjust=False,
    # )

    # ========================================================
    # CLEAN DATA
    # ========================================================

    # Eliminar filas multi index
    df.columns = df.columns.get_level_values(0)

    # Verificar duplicados en el índice
    duplicados = df.index.duplicated().sum()

    print(f"Duplicados en índice: {duplicados}")

    # Manejar nombres de columna
    df.columns.name = None

    df = df.reset_index()

    df.columns = [
        'date',
        'close',
        'high',
        'low',
        'open',
        'volume'
    ]

    if df.empty:
        raise ValueError(f"No se encontraron datos historicos para {ticker}")

    # if isinstance(df.columns, pd.MultiIndex):
    #     df.columns = df.columns.get_level_values(0)

    # df.columns.name = None
    # df = df.reset_index()

    if "date" not in df.columns or COLUMNA_OBJETIVO not in df.columns:
        raise ValueError(
            f"El dataset descargado no contiene las columnas requeridas: date y {COLUMNA_OBJETIVO}"
        )

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").dropna(subset=[COLUMNA_OBJETIVO]).reset_index(drop=True)

    if len(df) <= lookback + pred_len:
        raise ValueError(
            "No hay suficientes registros para entrenar el modelo con el lookback y pred_len solicitados"
        )

    csv_path = Path(f"{ticker}.csv")
    # df.to_csv(csv_path, index=False)

    serie = df[[COLUMNA_OBJETIVO]].values
    scaler = MinMaxScaler(feature_range=(0, 1))
    serie_scaled = scaler.fit_transform(serie)

    X, y = [], []
    for index in range(lookback, len(serie_scaled) - pred_len + 1):
        X.append(serie_scaled[index - lookback:index])
        y.append(serie_scaled[index + pred_len - 1])

    X = np.array(X)
    y = np.array(y)

    if len(X) < 2:
        raise ValueError("No se generaron suficientes secuencias para entrenar y validar")

    corte = int(len(X) * (1 - test_size))
    if corte <= 0 or corte >= len(X):
        raise ValueError("La division train/test resulto invalida; ajusta test_size o el rango de fechas")

    X_train, X_test = X[:corte], X[corte:]
    y_train, y_test = y[:corte], y[corte:]

    if len(X_test) == 0:
        raise ValueError("No hay datos de prueba disponibles; amplía el historial o reduce test_size")

    modelo = Sequential([
        Input(shape=(lookback, 1)),
        GRU(64, return_sequences=True),
        Dropout(0.2),
        GRU(32),
        Dropout(0.2),
        Dense(16, activation="relu"),
        Dense(pred_len),
    ])
    modelo.compile(optimizer="adam", loss="mean_squared_error")

    early_stop = EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True)
    historia = modelo.fit(
        X_train,
        y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=0.1,
        callbacks=[early_stop],
        verbose=0,
    )

    pred_scaled = modelo.predict(X_test, verbose=0)
    pred = scaler.inverse_transform(pred_scaled)
    real = scaler.inverse_transform(y_test)

    mae = float(mean_absolute_error(real, pred))
    rmse = float(np.sqrt(mean_squared_error(real, pred)))

    ultimos = df[[COLUMNA_OBJETIVO]].values[-lookback:]
    ultimos_scaled = scaler.transform(ultimos).reshape(1, lookback, 1)
    proxima_pred_scaled = modelo.predict(ultimos_scaled, verbose=0)
    proximo_precio = float(scaler.inverse_transform(proxima_pred_scaled)[0, 0])

    ultima_fecha = df["date"].max()
    proxima_fecha = (ultima_fecha + pd.tseries.offsets.BDay(pred_len)).date().isoformat()

    test_dates = df["date"].iloc[lookback + corte + pred_len - 1:lookback + corte + pred_len - 1 + len(real)]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=test_dates,
            y=real.flatten(),
            mode="lines",
            name="Real",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=test_dates,
            y=pred.flatten(),
            mode="lines",
            name="Prediccion",
        )
    )
    fig.update_layout(
        title=f"Prediccion GRU para {ticker}",
        xaxis_title="Fecha",
        yaxis_title="Precio de cierre",
        template="plotly_white",
    )

    chart_path = Path(f"{ticker}_gru_forecast.html")
    fig.write_html(chart_path, include_plotlyjs="cdn")

    forecast = []
    for fecha, valor_real, valor_predicho in zip(test_dates, real.flatten(), pred.flatten()):
        forecast.append(
            {
                "date": pd.Timestamp(fecha).date().isoformat(),
                "actual_close": float(valor_real),
                "predicted_close": float(valor_predicho),
            }
        )

    return {
        "ticker": ticker,
        "start_date": start_date,
        "end_date": end_date,
        "lookback": lookback,
        "pred_len": pred_len,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "metrics": {
            "mae": mae,
            "rmse": rmse,
            "best_val_loss": float(min(historia.history["val_loss"])),
            "epochs_trained": int(len(historia.history["loss"])),
            "epochs_requested": int(epochs),
        },
        "next_business_day_prediction": {
            "date": proxima_fecha,
            "predicted_close": proximo_precio,
        },
        "forecast": forecast,
        "chart_path": str(chart_path),
        "csv_path": str(csv_path),
    }

# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":
    result = run_gru_prediction(
        ticker="PFAVAL.CL",
        start_date="2025-01-01",
        end_date="2026-05-28",
    )

    print("Registrando tool predict_stock_gru")
    
    print(result)