"""Exportación a CSV, Excel y PDF."""
import io

import pandas as pd
from fpdf import FPDF


def _t(s):
    return str(s).encode("latin-1", "replace").decode("latin-1")


def tabla(df):
    v = df.copy()
    v["fecha"] = v["fecha"].dt.strftime("%Y-%m-%d")
    return v[["fecha", "tipo", "descripcion", "categoria", "subtipo", "monto"]]


def a_csv(df):
    return tabla(df).to_csv(index=False).encode("utf-8-sig")


def a_excel(df, resumen):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        tabla(df).to_excel(w, sheet_name="Movimientos", index=False)
        resumen.to_excel(w, sheet_name="Resumen mensual", index=False)
        for ws in w.book.worksheets:
            for col in ws.columns:
                ancho = max(len(str(c.value or "")) for c in col) + 2
                ws.column_dimensions[col[0].column_letter].width = min(ancho, 45)
    return buf.getvalue()


def a_pdf(titulo, d, limite):
    ing = d[d.tipo == "Ingreso"].monto.sum()
    gas = d[d.tipo == "Gasto"].monto.sum()
    p = FPDF()
    p.add_page()
    p.set_auto_page_break(True, 15)
    fila = dict(new_x="LMARGIN", new_y="NEXT")
    p.set_font("Helvetica", "B", 18)
    p.set_text_color(31, 95, 191)
    p.cell(0, 12, _t("MiPresupuesto - Resumen mensual"), **fila)
    p.set_font("Helvetica", "", 12)
    p.set_text_color(0)
    p.cell(0, 8, _t(titulo), **fila)
    p.ln(4)
    datos = [("Ingresos", f"S/ {ing:,.2f}"), ("Gastos", f"S/ {gas:,.2f}"), ("Balance", f"S/ {ing - gas:,.2f}")]
    if limite > 0:
        datos += [("Presupuesto mensual", f"S/ {limite:,.2f}"), ("Presupuesto utilizado", f"{gas / limite:.0%}")]
    for k, v in datos:
        p.cell(60, 8, _t(k))
        p.cell(0, 8, _t(v), **fila)
    cats = d[d.tipo == "Gasto"].groupby("categoria").monto.sum().sort_values(ascending=False)
    if not cats.empty:
        p.ln(4)
        p.set_font("Helvetica", "B", 12)
        p.cell(0, 8, "Gastos por categoria", **fila)
        p.set_font("Helvetica", "", 11)
        for c, m in cats.items():
            p.cell(60, 7, _t(c))
            p.cell(0, 7, f"S/ {m:,.2f}", **fila)
    p.ln(4)
    p.set_font("Helvetica", "B", 12)
    p.cell(0, 8, "Movimientos", **fila)
    anchos = [25, 20, 75, 40, 30]
    p.set_font("Helvetica", "B", 10)
    for a, h in zip(anchos, ["Fecha", "Tipo", "Descripcion", "Categoria", "Monto"]):
        p.cell(a, 7, h, border="B", align="R" if h == "Monto" else "L")
    p.ln()
    p.set_font("Helvetica", "", 10)
    for r in d.sort_values("fecha").itertuples():
        vals = [f"{r.fecha:%d/%m/%Y}", r.tipo, r.descripcion[:40], r.categoria, f"S/ {r.monto:,.2f}"]
        for i, (a, v) in enumerate(zip(anchos, vals)):
            p.cell(a, 6, _t(v), align="R" if i == 4 else "L")
        p.ln()
    return bytes(p.output())
