import mysql.connector
import pandas as pd
from datetime import datetime, date, timedelta
from calendar import monthrange
from decimal import Decimal  # para manejar bien los Decimals


# ============================
# Parámetros de conexión
# ============================

DB_CONFIG = {
    "host": "haycash-prod.cluster-cymmiznbjsjw.us-east-1.rds.amazonaws.com",          # <-- pon aquí tu host real
    "user": "daniel.negrete",       # <-- tu usuario
    "password": "xX9SumNUXV09,527%7wI",  # <-- tu password
    "database": "calculados",
    "port": 63306,
}

# ============================
# Utilidades de fechas
# ============================

def parse_fecha_ev(fecha_ev_str: str) -> date:
    """
    Acepta 'YYYY-MM' o 'YYYY-MM-DD' y regresa la fecha_ev como
    último día de ese mes (date).
    """
    fecha_ev_str = fecha_ev_str.strip()
    if len(fecha_ev_str) == 7:  # 'YYYY-MM'
        year, month = map(int, fecha_ev_str.split("-"))
        last_day = monthrange(year, month)[1]
        return date(year, month, last_day)
    elif len(fecha_ev_str) == 10:  # 'YYYY-MM-DD'
        dt = datetime.strptime(fecha_ev_str, "%Y-%m-%d").date()
        last_day = monthrange(dt.year, dt.month)[1]
        return date(dt.year, dt.month, last_day)
    else:
        raise ValueError("fecha_ev debe ser 'YYYY-MM' o 'YYYY-MM-DD'")


def month_bounds(any_date: date):
    """
    Regresa (primer_dia_mes, primer_dia_mes_siguiente) para el mes de any_date.
    """
    first_day = date(any_date.year, any_date.month, 1)
    if any_date.month == 12:
        next_month = date(any_date.year + 1, 1, 1)
    else:
        next_month = date(any_date.year, any_date.month + 1, 1)
    return first_day, next_month


def same_month_prev_year(any_date: date):
    """
    Regresa fecha_ev_anio_anterior con mismo mes y último día de mes.
    """
    prev_year = any_date.year - 1
    last_day_prev = monthrange(prev_year, any_date.month)[1]
    return date(prev_year, any_date.month, last_day_prev)


def calc_yoy(curr, prev):
    """
    Devuelve crecimiento YoY en porcentaje como Decimal.
    Maneja curr/prev como Decimal, int o float.
    """
    if prev in (0, None) or curr is None:
        return None

    curr_dec = curr if isinstance(curr, Decimal) else Decimal(str(curr))
    prev_dec = prev if isinstance(prev, Decimal) else Decimal(str(prev))

    if prev_dec == 0:
        return None

    # 100 * (curr - prev) / prev  (regresamos el valor ya en "porcentaje")
    return (Decimal(100) * (curr_dec - prev_dec) / prev_dec)


# ============================
# Cálculo de métricas FINANCIEROS
# ============================

def calcular_metricas_financieras(fecha_ev_str: str):
    """
    Calcula los 14 valores de la pestaña 'Financieros' y regresa
    listas para 'Valor capital' y 'Valor pagare'.
    """
    fecha_ev = parse_fecha_ev(fecha_ev_str)  # último día del mes
    fecha_ev_ym = f"{fecha_ev.year}-{fecha_ev.month:02d}"  # para credit_movements.period_ym
    inicio_mes, inicio_mes_siguiente = month_bounds(fecha_ev)

    # mismo mes año anterior
    fecha_ev_prev = same_month_prev_year(fecha_ev)
    inicio_mes_prev, inicio_mes_prev_siguiente = month_bounds(fecha_ev_prev)

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    params = {
        "fecha_ev": fecha_ev,
        "inicio_mes": inicio_mes,
        "inicio_mes_siguiente": inicio_mes_siguiente,
        "fecha_ev_prev": fecha_ev_prev,
        "inicio_mes_prev": inicio_mes_prev,
        "inicio_mes_prev_siguiente": inicio_mes_prev_siguiente,
        "period_ym": fecha_ev_ym,
    }

    # ---------- VALOR CAPITAL ----------

    # 1) Monto colocado desde el inicio (capital)
    cur.execute(
        """
        SELECT COALESCE(SUM(capital), 0)
        FROM calculados.credits_details
        WHERE started_at <= %(fecha_ev)s
        """,
        params,
    )
    capital_monto_colocado_desde_inicio = cur.fetchone()[0]

    # 2) Monto amortizado desde el inicio (capital_return hasta fecha_ev)
    cur.execute(
        """
        SELECT COALESCE(SUM(capital_return), 0)
        FROM calculados.credit_movements
        WHERE period_ym <= %(period_ym)s
        """,
        params,
    )
    capital_monto_amortizado_desde_inicio = cur.fetchone()[0]

    # 3) Cartera total (due_capital_total en RX_cartera_historico en fecha_ev)
    cur.execute(
        """
        SELECT COALESCE(SUM(due_capital_total), 0)
        FROM calculados.RX_cartera_historico
        WHERE mes = %(fecha_ev)s
        """,
        params,
    )
    capital_cartera_total = cur.fetchone()[0]

    # 4) Cartera vencida (tabla_v_total.saldo/gamma con dias_atraso > 90 en fecha_ev)
    cur.execute(
        """
        SELECT COALESCE(SUM(
            CASE WHEN gamma <> 0 THEN saldo / gamma ELSE 0 END
        ), 0)
        FROM calculados.tabla_v_total
        WHERE date = %(fecha_ev)s
          AND dias_atraso > 90
        """,
        params,
    )
    capital_cartera_vencida = cur.fetchone()[0]

    # 5) Colocación del mes (capital, started_at en mes de fecha_ev)
    cur.execute(
        """
        SELECT COALESCE(SUM(capital), 0)
        FROM calculados.credits_details
        WHERE started_at >= %(inicio_mes)s
          AND started_at < %(inicio_mes_siguiente)s
        """,
        params,
    )
    capital_colocacion_mes = cur.fetchone()[0]

    # 6) Colocación del mes año anterior (capital, mismo mes año previo)
    cur.execute(
        """
        SELECT COALESCE(SUM(capital), 0)
        FROM calculados.credits_details
        WHERE started_at >= %(inicio_mes_prev)s
          AND started_at < %(inicio_mes_prev_siguiente)s
        """,
        params,
    )
    capital_colocacion_mes_prev = cur.fetchone()[0]

    # 7) Crecimiento YoY colocación (capital)
    capital_yoy = calc_yoy(capital_colocacion_mes, capital_colocacion_mes_prev)

    # ---------- VALOR PAGARÉ ----------

    # 1) Monto colocado desde el inicio (vp)
    cur.execute(
        """
        SELECT COALESCE(SUM(vp), 0)
        FROM calculados.credits_details
        WHERE started_at <= %(fecha_ev)s
        """,
        params,
    )
    vp_monto_colocado_desde_inicio = cur.fetchone()[0]

    # 2) Monto amortizado desde el inicio (Valor pagaré)
    cur.execute(
        """
        SELECT COALESCE(SUM(cobranza_total), 0)
        FROM calculados.RX_cobranza
        WHERE Mes <= %(fecha_ev)s
        """,
        params,
    )
    vp_monto_amortizado_desde_inicio = cur.fetchone()[0]

    # 3) Cartera total (due_vp_total en RX_cartera_historico en fecha_ev)
    cur.execute(
        """
        SELECT COALESCE(SUM(due_vp_total), 0)
        FROM calculados.RX_cartera_historico
        WHERE mes = %(fecha_ev)s
        """,
        params,
    )
    vp_cartera_total = cur.fetchone()[0]

    # 4) Cartera vencida (tabla_v_total.saldo con dias_atraso > 90 en fecha_ev)
    cur.execute(
        """
        SELECT COALESCE(SUM(saldo), 0)
        FROM calculados.tabla_v_total
        WHERE date = %(fecha_ev)s
          AND dias_atraso > 90
        """,
        params,
    )
    vp_cartera_vencida = cur.fetchone()[0]

    # 5) Colocación del mes (vp)
    cur.execute(
        """
        SELECT COALESCE(SUM(vp), 0)
        FROM calculados.credits_details
        WHERE started_at >= %(inicio_mes)s
          AND started_at < %(inicio_mes_siguiente)s
        """,
        params,
    )
    vp_colocacion_mes = cur.fetchone()[0]

    # 6) Colocación del mes año anterior (vp)
    cur.execute(
        """
        SELECT COALESCE(SUM(vp), 0)
        FROM calculados.credits_details
        WHERE started_at >= %(inicio_mes_prev)s
          AND started_at < %(inicio_mes_prev_siguiente)s
        """,
        params,
    )
    vp_colocacion_mes_prev = cur.fetchone()[0]

    # 7) Crecimiento YoY colocación (vp)
    vp_yoy = calc_yoy(vp_colocacion_mes, vp_colocacion_mes_prev)

    cur.close()
    conn.close()

    filas = [
        "Monto colocado desde el incio",
        "Monto amortizado desde el inicio",
        "Cartera total",
        "Cartera vencida",
        "Colocacion mes",
        "Colocacion mes año anterior",
        "Crecimiento YoY de colocacion",
    ]

    valores_capital = [
        capital_monto_colocado_desde_inicio,
        capital_monto_amortizado_desde_inicio,
        capital_cartera_total,
        capital_cartera_vencida,
        capital_colocacion_mes,
        capital_colocacion_mes_prev,
        capital_yoy,
    ]

    valores_vp = [
        vp_monto_colocado_desde_inicio,
        vp_monto_amortizado_desde_inicio,
        vp_cartera_total,
        vp_cartera_vencida,
        vp_colocacion_mes,
        vp_colocacion_mes_prev,
        vp_yoy,
    ]

    return filas, valores_capital, valores_vp


# ============================
# Cálculo de "Indicadores relevantes"
# ============================

def calcular_indicadores_relevantes(fecha_ev_str: str):
    fecha_ev = parse_fecha_ev(fecha_ev_str)

    start_ytd = date(fecha_ev.year, 1, 1)
    start_ltm = fecha_ev - timedelta(days=365)

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Duración promedio
    cur.execute(
        """
        SELECT AVG(plazo)
        FROM calculados.credits_details
        WHERE started_at >= %(start_ytd)s
          AND started_at <= %(fecha_ev)s
          AND credit_id NOT IN (1,2,3,4,5)
        """,
        {"start_ytd": start_ytd, "fecha_ev": fecha_ev},
    )
    dur_ytd = cur.fetchone()[0]

    cur.execute(
        """
        SELECT AVG(plazo)
        FROM calculados.credits_details
        WHERE started_at >= %(start_ltm)s
          AND started_at <= %(fecha_ev)s
          AND credit_id NOT IN (1,2,3,4,5)
        """,
        {"start_ltm": start_ltm, "fecha_ev": fecha_ev},
    )
    dur_ltm = cur.fetchone()[0]

    cur.execute(
        """
        SELECT AVG(plazo)
        FROM calculados.credits_details
        WHERE started_at <= %(fecha_ev)s
          AND credit_id NOT IN (1,2,3,4,5)
        """,
        {"fecha_ev": fecha_ev},
    )
    dur_hist = cur.fetchone()[0]

    # Ticket promedio
    cur.execute(
        """
        SELECT AVG(capital)
        FROM calculados.credits_details
        WHERE started_at >= %(start_ytd)s
          AND started_at <= %(fecha_ev)s
        """,
        {"start_ytd": start_ytd, "fecha_ev": fecha_ev},
    )
    ticket_ytd = cur.fetchone()[0]

    cur.execute(
        """
        SELECT AVG(capital)
        FROM calculados.credits_details
        WHERE started_at >= %(start_ltm)s
          AND started_at <= %(fecha_ev)s
        """,
        {"start_ltm": start_ltm, "fecha_ev": fecha_ev},
    )
    ticket_ltm = cur.fetchone()[0]

    cur.execute(
        """
        SELECT AVG(capital)
        FROM calculados.credits_details
        WHERE started_at <= %(fecha_ev)s
        """,
        {"fecha_ev": fecha_ev},
    )
    ticket_hist = cur.fetchone()[0]

    # Número de clientes / créditos activos
    cur.execute(
        """
        SELECT
          COALESCE(SUM(num_clientes_activos), 0),
          COALESCE(SUM(num_creditos_activos), 0)
        FROM calculados.RX_cartera_historico
        WHERE mes = %(fecha_ev)s
        """,
        {"fecha_ev": fecha_ev},
    )
    res = cur.fetchone()
    num_clientes_activos = res[0]
    num_creditos_activos = res[1]

    cur.close()
    conn.close()

    filas = [
        "Duracion promedio del financiamiento (meses)",
        "Ticket promedio",
        "Numero de clientes activos",
        "Numero de creditos activos",
    ]

    col_ytd = [dur_ytd, ticket_ytd, num_clientes_activos, num_creditos_activos]
    col_ltm = [dur_ltm, ticket_ltm, num_clientes_activos, num_creditos_activos]
    col_hist = [dur_hist, ticket_hist, num_clientes_activos, num_creditos_activos]

    return filas, col_ytd, col_ltm, col_hist


# ============================
# Cálculo de "Colocacion mensual"
# ============================

def calcular_colocacion_mensual(fecha_ev_str: str) -> pd.DataFrame:
    fecha_ev = parse_fecha_ev(fecha_ev_str)
    fecha_ev_ym = f"{fecha_ev.year}-{fecha_ev.month:02d}"
    start_global = date(2025, 1, 1)

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    # credits_details
    cur.execute(
        """
        SELECT
          DATE_FORMAT(started_at, '%Y-%m') AS Mes,
          COALESCE(SUM(capital), 0) AS valor_capital_total,
          COALESCE(SUM(vp), 0)      AS valor_pagare_total
        FROM calculados.credits_details
        WHERE started_at >= %s
          AND started_at <= %s
        GROUP BY DATE_FORMAT(started_at, '%Y-%m')
        """,
        (start_global, fecha_ev),
    )
    rows = cur.fetchall()
    df_cd = pd.DataFrame(rows, columns=["Mes", "Valor capital total", "Valor pagare total"])

    # RX_colocacion_nuevos
    cur.execute(
        """
        SELECT
          DATE_FORMAT(period_month, '%Y-%m') AS Mes,
          COALESCE(SUM(colocacion_nuevos_amount), 0) AS Nuevo
        FROM calculados.RX_colocacion_nuevos
        WHERE period_month >= %s
          AND period_month <= %s
        GROUP BY DATE_FORMAT(period_month, '%Y-%m')
        """,
        (start_global, fecha_ev),
    )
    rows = cur.fetchall()
    df_nuevos = pd.DataFrame(rows, columns=["Mes", "Nuevo"])

    # RX_colocacion_refinanciamientos
    cur.execute(
        """
        SELECT
          month_year AS Mes,
          COALESCE(SUM(refinanciamiento_amount), 0) AS Refinanciamiento
        FROM calculados.RX_colocacion_refinanciamientos
        WHERE month_year >= %s
          AND month_year <= %s
        GROUP BY month_year
        """,
        ("2025-01", fecha_ev_ym),
    )
    rows = cur.fetchall()
    df_ref = pd.DataFrame(rows, columns=["Mes", "Refinanciamiento"])

    # RX_colocacion_mensual
    cur.execute(
        """
        SELECT
          month_year AS Mes,
          COALESCE(SUM(tpv_amount), 0) AS TPV,
          COALESCE(SUM(dom_amount), 0) AS Domiciliado
        FROM calculados.RX_colocacion_mensual
        WHERE month_year >= %s
          AND month_year <= %s
        GROUP BY month_year
        """,
        ("2025-01", fecha_ev_ym),
    )
    rows = cur.fetchall()
    df_tpv = pd.DataFrame(rows, columns=["Mes", "TPV", "Domiciliado"])

    cur.close()
    conn.close()

    dfs = [df_cd, df_nuevos, df_ref, df_tpv]
    df_final = None
    for d in dfs:
        if d is None or d.empty:
            continue
        if df_final is None:
            df_final = d
        else:
            df_final = pd.merge(df_final, d, on="Mes", how="outer")

    if df_final is None:
        df_final = pd.DataFrame(
            columns=[
                "Mes",
                "Valor capital total",
                "Valor pagare total",
                "Nuevo",
                "Refinanciamiento",
                "TPV",
                "Domiciliado",
            ]
        )
        return df_final

    df_final["Mes"] = df_final["Mes"].astype(str)
    df_final["Mes_dt"] = pd.to_datetime(df_final["Mes"], format="%Y-%m", errors="coerce")
    df_final = df_final.sort_values("Mes_dt").drop(columns=["Mes_dt"])

    for col in ["Valor capital total", "Valor pagare total", "Nuevo", "Refinanciamiento", "TPV", "Domiciliado"]:
        if col in df_final.columns:
            df_final[col] = df_final[col].fillna(0)

    cols_order = [
        "Mes",
        "Valor capital total",
        "Valor pagare total",
        "Nuevo",
        "Refinanciamiento",
        "TPV",
        "Domiciliado",
    ]
    df_final = df_final.reindex(columns=cols_order)

    return df_final


# ============================
# Cálculo de "Amortizacion mensual"
# ============================

def calcular_amortizacion_mensual(fecha_ev_str: str) -> pd.DataFrame:
    fecha_ev = parse_fecha_ev(fecha_ev_str)
    start_global = date(2025, 1, 1)

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    # cartera.conciliations
    cur.execute(
        """
        SELECT
          DATE_FORMAT(date, '%Y-%m') AS Mes,
          COALESCE(SUM(capital_return), 0)         AS Capital,
          COALESCE(SUM(collection_management), 0)  AS GC,
          COALESCE(SUM(iva), 0)                    AS IVA,
          COALESCE(SUM(is_lastpayment), 0)         AS Pagos_de_liquidacion
        FROM cartera.conciliations
        WHERE date >= %s
          AND date <= %s
        GROUP BY DATE_FORMAT(date, '%Y-%m')
        """,
        (start_global, fecha_ev),
    )
    rows = cur.fetchall()
    df_conc = pd.DataFrame(
        rows,
        columns=["Mes", "Capital", "GC", "IVA", "Pagos de liquidacion"]
    )

    # RX_cartera_historico
    cur.execute(
        """
        SELECT
          DATE_FORMAT(mes, '%Y-%m') AS Mes,
          COALESCE(SUM(due_capital_total), 0) AS Valor_de_la_cartera
        FROM calculados.RX_cartera_historico
        WHERE mes >= %s
          AND mes <= %s
        GROUP BY DATE_FORMAT(mes, '%Y-%m')
        """,
        (start_global, fecha_ev),
    )
    rows = cur.fetchall()
    df_cartera = pd.DataFrame(rows, columns=["Mes", "Valor de la cartera"])

    cur.close()
    conn.close()

    dfs = [df_conc, df_cartera]
    df_final = None
    for d in dfs:
        if d is None or d.empty:
            continue
        if df_final is None:
            df_final = d
        else:
            df_final = pd.merge(df_final, d, on="Mes", how="outer")

    if df_final is None:
        df_final = pd.DataFrame(
            columns=[
                "Mes",
                "Capital",
                "GC",
                "IVA",
                "Pagos de liquidacion",
                "Pago total",
                "Valor de la cartera",
            ]
        )
        return df_final

    df_final["Mes"] = df_final["Mes"].astype(str)
    df_final["Mes_dt"] = pd.to_datetime(df_final["Mes"], format="%Y-%m", errors="coerce")
    df_final = df_final.sort_values("Mes_dt").drop(columns=["Mes_dt"])

    for col in ["Capital", "GC", "IVA", "Pagos de liquidacion", "Valor de la cartera"]:
        if col in df_final.columns:
            df_final[col] = df_final[col].fillna(0)

    df_final["Pago total"] = df_final.get("Capital", 0) + df_final.get("GC", 0) + df_final.get("IVA", 0)

    cols_order = [
        "Mes",
        "Capital",
        "GC",
        "IVA",
        "Pagos de liquidacion",
        "Pago total",
        "Valor de la cartera",
    ]
    df_final = df_final.reindex(columns=cols_order)

    return df_final


# ============================
# Cálculo de "Distribucion cartera" (giro / provincia)
# ============================

def calcular_distribucion_cartera(fecha_ev_str: str):
    """
    Calcula dos tablas:
      - Por giro_del_cliente
      - Por province

    Solo créditos con:
        completed_at IS NULL
        AND deleted_at IS NULL
        AND suspended_at IS NULL
    """
    fecha_ev = parse_fecha_ev(fecha_ev_str)

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    # -----------------------------
    # BLOQUE: POR GIRO
    # -----------------------------
    cur.execute(
        """
        SELECT
          giro_del_cliente,
          COALESCE(SUM(capital), 0) AS monto
        FROM calculados.credits_details
        WHERE completed_at IS NULL
          AND deleted_at IS NULL
          AND suspended_at IS NULL
          AND giro_del_cliente IS NOT NULL
        GROUP BY giro_del_cliente
        """
    )
    rows = cur.fetchall()
    df_giro = pd.DataFrame(rows, columns=["giro_del_cliente", "monto"])

    total_giro = df_giro["monto"].sum() if not df_giro.empty else 0
    df_giro["% de la cartera"] = df_giro["monto"] / total_giro if total_giro else 0
    df_giro = df_giro.sort_values("monto", ascending=False).reset_index(drop=True)

    # -----------------------------
    # BLOQUE: POR PROVINCIA
    # -----------------------------
    cur.execute(
        """
        SELECT
          province,
          COALESCE(SUM(capital), 0) AS monto
        FROM calculados.credits_details
        WHERE completed_at IS NULL
          AND deleted_at IS NULL
          AND suspended_at IS NULL
          AND province IS NOT NULL
        GROUP BY province
        """
    )
    rows = cur.fetchall()
    df_prov = pd.DataFrame(rows, columns=["province", "monto"])

    total_prov = df_prov["monto"].sum() if not df_prov.empty else 0
    df_prov["% de la cartera"] = df_prov["monto"] / total_prov if total_prov else 0
    df_prov = df_prov.sort_values("monto", ascending=False).reset_index(drop=True)

    cur.close()
    conn.close()

    return df_giro, df_prov


# ============================
# Generar Excel (todas las pestañas)
# ============================

def generar_excel_financieros(fecha_ev_str: str, nombre_archivo: str = "reporte_financiero.xlsx"):
    # FINANCIEROS
    filas_fin, valores_capital, valores_vp = calcular_metricas_financieras(fecha_ev_str)
    df_fin = pd.DataFrame({
        "Concepto": filas_fin,
        "Valor capital": valores_capital,
        "Valor pagare": valores_vp,
    })

    # INDICADORES
    filas_ind, col_ytd, col_ltm, col_hist = calcular_indicadores_relevantes(fecha_ev_str)
    df_ind = pd.DataFrame({
        "Indicador": filas_ind,
        "Year to date": col_ytd,
        "LTM last twelve months": col_ltm,
        "Historico desde el inicio": col_hist,
    })

    # COLOCACION MENSUAL
    df_col = calcular_colocacion_mensual(fecha_ev_str)

    # AMORTIZACION MENSUAL
    df_amort = calcular_amortizacion_mensual(fecha_ev_str)

    # DISTRIBUCION CARTERA
    df_giro, df_prov = calcular_distribucion_cartera(fecha_ev_str)

    with pd.ExcelWriter(nombre_archivo, engine="xlsxwriter") as writer:
        workbook = writer.book
        currency_fmt = workbook.add_format({"num_format": "$#,##0.00"})
        num_2dec_fmt = workbook.add_format({"num_format": "0.00"})
        int_fmt = workbook.add_format({"num_format": "#,##0"})
        percent_fmt = workbook.add_format({"num_format": "0.00%"})

        # === Financieros ===
        df_fin.to_excel(writer, sheet_name="Financieros", index=False)
        ws_fin = writer.sheets["Financieros"]
        ws_fin.set_column("B:C", 18)

        for row_idx in range(1, len(df_fin) + 1):
            concepto = df_fin.iloc[row_idx - 1, 0]
            if concepto == "Crecimiento YoY de colocacion":
                continue
            val_cap = df_fin.iloc[row_idx - 1, 1]
            val_vp = df_fin.iloc[row_idx - 1, 2]
            if val_cap is not None:
                ws_fin.write_number(row_idx, 1, float(val_cap), currency_fmt)
            if val_vp is not None:
                ws_fin.write_number(row_idx, 2, float(val_vp), currency_fmt)

        # === Indicadores relevantes ===
        df_ind.to_excel(writer, sheet_name="Indicadores relevantes", index=False)
        ws_ind = writer.sheets["Indicadores relevantes"]
        ws_ind.set_column("A:A", 45)
        ws_ind.set_column("B:D", 20)

        for row_idx in range(1, len(df_ind) + 1):
            indicador = df_ind.iloc[row_idx - 1, 0]
            vals = df_ind.iloc[row_idx - 1, 1:4]
            if indicador.startswith("Duracion promedio"):
                fmt = num_2dec_fmt
            elif indicador.startswith("Ticket promedio"):
                fmt = currency_fmt
            else:
                fmt = int_fmt
            for col_off, val in enumerate(vals, start=1):
                if val is not None:
                    ws_ind.write_number(row_idx, col_off, float(val), fmt)

        # === Colocacion mensual ===
        df_col.to_excel(writer, sheet_name="Colocacion mensual", index=False)
        ws_col = writer.sheets["Colocacion mensual"]
        ws_col.set_column("A:A", 12)
        ws_col.set_column("B:G", 18)

        for row_idx in range(1, len(df_col) + 1):
            for col_idx in range(1, 7):
                val = df_col.iloc[row_idx - 1, col_idx]
                if val is not None:
                    ws_col.write_number(row_idx, col_idx, float(val), currency_fmt)

        # === Amortizacion mensual ===
        df_amort.to_excel(writer, sheet_name="Amortizacion mensual", index=False)
        ws_am = writer.sheets["Amortizacion mensual"]
        ws_am.set_column("A:A", 12)
        ws_am.set_column("B:G", 18)

        for row_idx in range(1, len(df_amort) + 1):
            for col_idx in range(1, 7):
                val = df_amort.iloc[row_idx - 1, col_idx]
                if val is not None:
                    ws_am.write_number(row_idx, col_idx, float(val), currency_fmt)

        # === Distribucion cartera (última pestaña) ===
        # Primer bloque: por giro_del_cliente, columnas A-C
        df_giro_ren = df_giro.rename(columns={"giro_del_cliente": "giro_del_cliente"})
        df_giro_ren.to_excel(
            writer,
            sheet_name="Distribucion cartera",
            index=False,
            startrow=0,
            startcol=0,
        )

        # Segundo bloque: por province, columnas E-G (col 4), dejando una columna D en blanco
        df_prov_ren = df_prov.rename(columns={"province": "province"})
        df_prov_ren.to_excel(
            writer,
            sheet_name="Distribucion cartera",
            index=False,
            startrow=0,
            startcol=4,
        )

        ws_dist = writer.sheets["Distribucion cartera"]
        ws_dist.set_column("A:A", 35)  # giro
        ws_dist.set_column("B:C", 18)
        ws_dist.set_column("E:E", 20)  # province
        ws_dist.set_column("F:G", 18)

        # Formatear bloque giro: columnas B moneda, C porcentaje
        for row_idx in range(1, len(df_giro) + 1):
            monto = df_giro.iloc[row_idx - 1, 1]
            perc = df_giro.iloc[row_idx - 1, 2]
            if monto is not None:
                ws_dist.write_number(row_idx, 1, float(monto), currency_fmt)
            if perc is not None:
                ws_dist.write_number(row_idx, 2, float(perc), percent_fmt)

        # Formatear bloque province: columnas F moneda, G porcentaje
        for row_idx in range(1, len(df_prov) + 1):
            monto = df_prov.iloc[row_idx - 1, 1]
            perc = df_prov.iloc[row_idx - 1, 2]
            if monto is not None:
                ws_dist.write_number(row_idx, 5, float(monto), currency_fmt)   # col F
            if perc is not None:
                ws_dist.write_number(row_idx, 6, float(perc), percent_fmt)    # col G

    print(f"Archivo generado: {nombre_archivo}")


if __name__ == "__main__":
    generar_excel_financieros("2025-12", "reporte_concejo_2025-12.xlsx")

