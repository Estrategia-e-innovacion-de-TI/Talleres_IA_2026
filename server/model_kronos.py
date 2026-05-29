import sys
import os
import yfinance as yf
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# ============================================================
# PATH
# ============================================================

# current_dir = Path(__file__).resolve().parent
# project_path = current_dir / "Kronos"
# sys.path.append(str(project_path))


import sys
from pathlib import Path

# Subir hasta la carpeta GitHub
ruta_base = Path(__file__).resolve().parents[2]
# Agregar al path
sys.path.append(str(ruta_base))

from Kronos.model.kronos import Kronos, KronosTokenizer, KronosPredictor

# ============================================================
# LOAD MODEL ONLY ONCE
# ============================================================

print("Loading Kronos model...")

tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-tokenizer-base")
model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
predictor = KronosPredictor(model, tokenizer, max_context= 512)

print("Kronos model loaded.")

# ============================================================
# MAIN FUNCTION
# ============================================================

def run_kronos_prediction(
    ticker: str,
    start_date: str,
    end_date: str,
    lookback: int = 343,
    pred_len: int = 7,
    temperature: float = 1.0,
    top_p: float = 0.9,
    sample_count: int = 5
):

    # ========================================================
    # DOWNLOAD DATA
    # ========================================================

    df = yf.download(
        ticker,
        start=start_date,
        end=end_date
    )

    if df.empty:
        raise ValueError(f"No se encontraron datos para {ticker} en el rango solicitado")

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

    fecha_col = "Date" if "Date" in df.columns else "date"
    if fecha_col not in df.columns:
        raise ValueError("No se encontro columna de fecha en los datos descargados")

    df[fecha_col] = pd.to_datetime(df[fecha_col])
    df = df.rename(
        columns={
            fecha_col: "date",
            "Close": "close",
            "High": "high",
            "Low": "low",
            "Open": "open",
            "Volume": "volume",
        }
    )

    required_cols = ["date", "open", "high", "low", "close", "volume"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Faltan columnas requeridas en el dataset: {missing_cols}")

    df = df[required_cols].dropna().reset_index(drop=True)

    if len(df) < lookback:
        raise ValueError(
            f"No hay suficientes datos para lookback={lookback}. Disponibles: {len(df)}"
        )

    # Save CSV
    df.to_csv(f"{ticker}.csv", index=False)

    # ========================================================
    # PREPARE INPUTS
    # ========================================================

    x_df = df.loc[
        len(df) - lookback:,
        ['open', 'high', 'low', 'close', 'volume']
    ].reset_index(drop=True)

    x_timestamp = df.loc[
        len(df) - lookback:,
        'date'
    ].reset_index(drop=True)

    ultima_fecha = pd.Timestamp(df['date'].iloc[-1])
    y_timestamp = pd.bdate_range(
        start=ultima_fecha + pd.offsets.BDay(1),
        periods=pred_len
    )
    y_timestamp = pd.Series(y_timestamp)

    # ========================================================
    # PREDICT
    # ========================================================

    pred_df = predictor.predict(
        df=x_df,
        x_timestamp=x_timestamp,
        y_timestamp=y_timestamp,
        pred_len=pred_len,
        T=temperature,
        top_p=top_p,
        sample_count=sample_count
    )

    # ========================================================
    # VISUALIZATION
    # ========================================================

    def plot_prediction(df, pred_df):

        pred_df = pred_df.copy()
        pred_df.index = df.index[-pred_df.shape[0]:]

        sr_close = df['close']
        sr_pred_close = pred_df['close']

        sr_close.name = 'Ground Truth'
        sr_pred_close.name = "Prediction"

        sr_volume = df['volume']
        sr_pred_volume = pred_df['volume']

        sr_volume.name = 'Ground Truth'
        sr_pred_volume.name = "Prediction"

        close_df = pd.concat(
            [sr_close, sr_pred_close],
            axis=1
        )

        volume_df = pd.concat(
            [sr_volume, sr_pred_volume],
            axis=1
        )

        fig, (ax1, ax2) = plt.subplots(
            2,
            1,
            figsize=(8, 6),
            sharex=True
        )

        ax1.plot(
            close_df['Ground Truth'],
            label='Ground Truth',
            color='blue',
            linewidth=1.5
        )

        ax1.plot(
            close_df['Prediction'],
            label='Prediction',
            color='red',
            linewidth=1.5
        )

        ax1.set_ylabel(
            'Close Price',
            fontsize=14
        )

        ax1.legend(
            loc='lower left',
            fontsize=12
        )

        ax1.grid(True)

        ax2.plot(
            volume_df['Ground Truth'],
            label='Ground Truth',
            color='blue',
            linewidth=1.5
        )

        ax2.plot(
            volume_df['Prediction'],
            label='Prediction',
            color='red',
            linewidth=1.5
        )

        ax2.set_ylabel(
            'Volume',
            fontsize=14
        )

        ax2.legend(
            loc='upper left',
            fontsize=12
        )

        ax2.grid(True)

        plt.tight_layout()

        chart_path = f"{ticker}_forecast.png"

        plt.savefig(chart_path)

        plt.close()

        return chart_path

    # ========================================================
    # RESULTS
    # ========================================================

    print("Forecasted Data Head:")

    print(pred_df.head())

    # Combine historical and forecasted data for plotting
    df_plot = df.loc[len(df) - lookback:]

    chart_path = plot_prediction(
        df_plot,
        pred_df
    )

    forecast_records = pred_df.to_dict(orient="records")
    forecast_dates = [pd.Timestamp(ts).date().isoformat() for ts in y_timestamp]
    for idx, row in enumerate(forecast_records):
        if idx < len(forecast_dates):
            row["date"] = forecast_dates[idx]

    return {
        "ticker": ticker,
        "forecast": forecast_records,
        "chart_path": chart_path
    }

# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    result = run_kronos_prediction(
        ticker="PFAVAL.CL",
        start_date="2025-01-01",
        end_date="2026-05-28"
    )

    print(result)

 