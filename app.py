"""MiPresupuesto: finanzas personales. Ejecutar con: streamlit run app.py"""
import datetime as dt

import plotly.express as px
import streamlit as st

import database as db
import reportes

st.set_page_config(page_title="MiPresupuesto", page_icon="💰", layout="wide")
db.init()
S = st.session_state

AZUL, VERDE, AMARILLO, ROJO = "#1F5FBF", "#2E9E6B", "#E0A800", "#D64545"
CAT_ING = ["Sueldo", "Emprendimiento", "Ventas", "Bonificaciones", "Otros ingresos"]
CAT_GAS = ["Alimentación", "Transporte", "Educación", "Salud", "Vivienda", "Servicios",
           "Entretenimiento", "Compras personales", "Otros"]
TIPOS = ["Fijo", "Variable", "Ocasional"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
FECHAS = dict(min_value=dt.date(2000, 1, 1), max_value=dt.date(2100, 12, 31))
TODO = "Todo el historial"

st.markdown(f"""<style>
.block-container{{max-width:1150px;padding-top:2rem}}
.tarjeta{{border:1px solid #DDE7E1;border-radius:14px;padding:1rem 1.2rem;background:#fff;
 box-shadow:0 2px 8px rgba(31,95,191,.06);margin-bottom:.8rem}}
.tarjeta .t{{color:#6B7280;font-size:.85rem}}.tarjeta .v{{font-size:1.6rem;font-weight:700}}
.tarjeta .s{{color:#6B7280;font-size:.8rem}}
</style>""", unsafe_allow_html=True)


def soles(x):
    return f"S/ {x:,.2f}"


def etiqueta(m):
    return m if m == TODO else f"{MESES[int(m[5:]) - 1]} {m[:4]}"


def meses_de(df):
    return sorted(set(df["mes"]) | {dt.date.today().strftime("%Y-%m")}, reverse=True)


def tarjeta(titulo, valor, sub="", color=AZUL):
    st.markdown(f'<div class="tarjeta"><div class="t">{titulo}</div><div class="v" style="color:{color}">{valor}</div>'
                f'<div class="s">{sub}&nbsp;</div></div>', unsafe_allow_html=True)


def color_estado(p):
    return ROJO if p > 1 else AMARILLO if p >= 0.8 else VERDE


def barra(p, color=None):
    c = color or color_estado(p)
    return (f"<div style='background:#E5E7EB;border-radius:8px;height:12px;margin:6px 0'>"
            f"<div style='width:{min(p, 1) * 100:.1f}%;background:{c};height:12px;border-radius:8px'></div></div>")


def resumen(df):
    p = df.pivot_table(index="mes", columns="tipo", values="monto", aggfunc="sum", fill_value=0)
    for t in ("Ingreso", "Gasto"):
        if t not in p:
            p[t] = 0.0
    p = p.rename(columns={"Ingreso": "Ingresos", "Gasto": "Gastos"})[["Ingresos", "Gastos"]]
    p["Balance"] = p.Ingresos - p.Gastos
    p["% gastos/ingresos"] = (p.Gastos / p.Ingresos.where(p.Ingresos > 0) * 100).round(1)
    return p.sort_index().reset_index().rename(columns={"mes": "Mes"})


def graficar(fig):
    fig.update_layout(margin=dict(t=40, b=10, l=10, r=10), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)


def g_categorias(d, titulo="Gastos por categoría"):
    g = d[d.tipo == "Gasto"].groupby("categoria", as_index=False).monto.sum()
    if g.empty:
        st.caption("No hay gastos en este período.")
    else:
        graficar(px.pie(g, names="categoria", values="monto", hole=0.5, title=titulo,
                        color_discrete_sequence=px.colors.sequential.Blues_r + [VERDE]))


def g_barras(r):
    m = r.melt("Mes", ["Ingresos", "Gastos"], "Tipo", "Monto (S/)")
    graficar(px.bar(m, x="Mes", y="Monto (S/)", color="Tipo", barmode="group",
                    title="Ingresos y gastos por mes", color_discrete_map={"Ingresos": VERDE, "Gastos": AZUL}))


def g_linea(r, cols, titulo):
    graficar(px.line(r, x="Mes", y=cols, markers=True, title=titulo,
                     color_discrete_map={"Ingresos": VERDE, "Gastos": AZUL}).update_layout(yaxis_title="S/"))


def vacio(df):
    if df.empty:
        st.info("Aún no hay movimientos registrados. Empieza en «Mis ingresos» o «Mis gastos».")
    return df.empty


# ------------------------------------------------------------ Panel
def pagina_panel():
    st.title("Panel principal")
    df = db.movimientos()
    if vacio(df):
        return
    sel = st.selectbox("Período", [TODO] + meses_de(df), format_func=etiqueta)
    d = df if sel == TODO else df[df.mes == sel]
    ing, gas = d[d.tipo == "Ingreso"].monto.sum(), d[d.tipo == "Gasto"].monto.sum()
    saldo = df[df.tipo == "Ingreso"].monto.sum() - df[df.tipo == "Gasto"].monto.sum()
    lim = db.presupuestos().get("TOTAL", 0)
    c = st.columns(5)
    with c[0]: tarjeta("Saldo disponible", soles(saldo), "Acumulado total", VERDE if saldo >= 0 else ROJO)
    with c[1]: tarjeta("Total de ingresos", soles(ing), etiqueta(sel), VERDE)
    with c[2]: tarjeta("Total de gastos", soles(gas), etiqueta(sel))
    with c[3]: tarjeta("Presupuesto mensual", soles(lim) if lim else "Sin definir", "Límite de gasto")
    if lim and sel != TODO:
        with c[4]: tarjeta("Presupuesto usado", f"{gas / lim:.0%}", "del mes seleccionado", color_estado(gas / lim))
    else:
        with c[4]: tarjeta("Presupuesto usado", "—", "Elige un mes y define un límite")
    r = resumen(df)
    a, b = st.columns(2)
    with a: g_categorias(d)
    with b: g_barras(r)
    g_linea(r, ["Gastos"], "Evolución de los gastos")


# ------------------------------------------------------------ Movimientos
def campos(pref, tipo, r=None):
    """Campos comunes del formulario; r es un registro existente (edición)."""
    cats = CAT_ING if tipo == "Ingreso" else CAT_GAS
    if r is not None and r.categoria not in cats:
        cats = cats + [r.categoria]
    c1, c2 = st.columns(2)
    desc = c1.text_input("Descripción", value=r.descripcion if r is not None else "", key=f"{pref}_d")
    monto = c2.number_input("Monto (S/)", min_value=0.0, step=10.0, format="%.2f",
                            value=float(r.monto) if r is not None else 0.0, key=f"{pref}_m")
    cat = c1.selectbox("Categoría", cats, index=cats.index(r.categoria) if r is not None else 0, key=f"{pref}_c")
    fecha = c2.date_input("Fecha", r.fecha.date() if r is not None else dt.date.today(),
                          format="DD/MM/YYYY", key=f"{pref}_f", **FECHAS)
    sub = c1.selectbox(f"Tipo de {tipo.lower()}", TIPOS,
                       index=TIPOS.index(r.subtipo) if r is not None and r.subtipo in TIPOS else 0, key=f"{pref}_s")
    return desc, monto, cat, fecha, sub


def valido(desc, monto):
    if not desc.strip():
        st.error("Escribe una descripción.")
    elif monto <= 0:
        st.error("El monto debe ser mayor que cero.")
    else:
        return True
    return False


def gestionar(df, clave):
    if df.empty:
        st.info("Todavía no hay registros para mostrar.")
        return
    v = df[["fecha", "tipo", "descripcion", "categoria", "subtipo", "monto"]].copy()
    v["fecha"] = v.fecha.dt.strftime("%d/%m/%Y")
    v.columns = ["Fecha", "Movimiento", "Descripción", "Categoría", "Tipo", "Monto"]
    st.dataframe(v, use_container_width=True, hide_index=True,
                 column_config={"Monto": st.column_config.NumberColumn(format="S/ %.2f")})
    st.markdown("**Editar o eliminar un movimiento**")
    filas = {r.id: r for r in df.itertuples()}
    mid = st.selectbox("Selecciona un movimiento", list(filas), key=f"sel_{clave}",
                       format_func=lambda i: f"{filas[i].fecha:%d/%m/%Y} · {filas[i].descripcion} · {soles(filas[i].monto)}")
    r = filas[mid]
    with st.form(f"ed_{clave}_{mid}"):
        desc, monto, cat, fecha, sub = campos(f"e{clave}{mid}", r.tipo, r)
        guardar = st.form_submit_button("Guardar cambios", type="primary")
    if guardar and valido(desc, monto):
        db.editar_mov(mid, desc, monto, cat, fecha, sub)
        S.aviso = "Movimiento actualizado."
        st.rerun()
    with st.popover("Eliminar este movimiento"):
        st.write("Esta acción no se puede deshacer.")
        if st.button("Confirmar eliminación", key=f"del_{clave}_{mid}"):
            db.eliminar_mov(mid)
            S.aviso = "Movimiento eliminado."
            st.rerun()


def pagina_mov(tipo):
    st.title("Mis ingresos" if tipo == "Ingreso" else "Mis gastos")
    n = S.setdefault(f"n_{tipo}", 0)  # contador para limpiar el formulario tras guardar
    with st.form(f"nuevo_{tipo}_{n}"):
        desc, monto, cat, fecha, sub = campos(f"n{tipo}{n}", tipo)
        ok = st.form_submit_button(f"Guardar {tipo.lower()}", type="primary")
    if ok and valido(desc, monto):
        db.agregar_mov(tipo, desc, monto, cat, fecha, sub)
        S[f"n_{tipo}"] += 1
        S.aviso = f"{tipo} guardado correctamente."
        st.rerun()
    st.subheader("Registros")
    df = db.movimientos()
    gestionar(df[df.tipo == tipo], tipo)


def pagina_historial():
    st.title("Historial")
    df = db.movimientos()
    if vacio(df):
        return
    a, b, c = st.columns(3)
    tipo = a.radio("Movimiento", ["Todos", "Ingreso", "Gasto"], horizontal=True)
    mes = b.selectbox("Mes", ["Todos"] + meses_de(df), format_func=lambda m: m if m == "Todos" else etiqueta(m))
    cats = c.multiselect("Categorías", sorted(df.categoria.unique()))
    d = df
    if tipo != "Todos": d = d[d.tipo == tipo]
    if mes != "Todos": d = d[d.mes == mes]
    if cats: d = d[d.categoria.isin(cats)]
    if st.checkbox("Filtrar por rango de fechas"):
        rango = st.date_input("Rango", (df.fecha.min().date(), df.fecha.max().date()), format="DD/MM/YYYY", **FECHAS)
        if len(rango) == 2:
            d = d[(d.fecha.dt.date >= rango[0]) & (d.fecha.dt.date <= rango[1])]
    st.caption(f"{len(d)} movimientos · Ingresos {soles(d[d.tipo == 'Ingreso'].monto.sum())} · "
               f"Gastos {soles(d[d.tipo == 'Gasto'].monto.sum())}")
    gestionar(d, "hist")


# ------------------------------------------------------------ Presupuesto
def bloque(nombre, gastado, limite):
    p = gastado / limite
    est = "Excedido" if p > 1 else "Próximo a agotarse" if p >= 0.8 else "Dentro del presupuesto"
    resto = f"Te quedan {soles(limite - gastado)}" if limite >= gastado else f"Excedido por {soles(gastado - limite)}"
    st.markdown(f"<div class='tarjeta'><b>{nombre}</b> · {soles(gastado)} de {soles(limite)} ({p:.0%}) · "
                f"<span style='color:{color_estado(p)};font-weight:600'>{est}</span>{barra(p)}"
                f"<span class='s'>{resto}</span></div>", unsafe_allow_html=True)


def pagina_presupuesto():
    st.title("Mi presupuesto")
    pres, df = db.presupuestos(), db.movimientos()
    with st.expander("Definir presupuestos", expanded=not pres):
        with st.form("form_pres"):
            tot = st.number_input("Límite de gasto mensual (S/)", min_value=0.0, step=50.0,
                                  value=float(pres.get("TOTAL", 0)))
            st.caption("Estos montos se aplican a cada mes. Deja 0 en una categoría para no asignarle presupuesto.")
            cols = st.columns(3)
            vals = {c: cols[i % 3].number_input(c, min_value=0.0, step=10.0, value=float(pres.get(c, 0)), key=f"p_{c}")
                    for i, c in enumerate(CAT_GAS)}
            if st.form_submit_button("Guardar presupuesto", type="primary"):
                db.fijar_presupuesto("TOTAL", tot)
                for c, v in vals.items():
                    db.fijar_presupuesto(c, v)
                S.aviso = "Presupuesto guardado."
                st.rerun()
    if not pres:
        st.info("Define tu límite mensual y los presupuestos por categoría para ver tu avance.")
        return
    mes = st.selectbox("Mes a consultar", meses_de(df), format_func=etiqueta)
    g = df[(df.tipo == "Gasto") & (df.mes == mes)]
    if "TOTAL" in pres:
        bloque("Presupuesto total del mes", g.monto.sum(), pres["TOTAL"])
    for c in CAT_GAS:
        if c in pres:
            bloque(c, g[g.categoria == c].monto.sum(), pres[c])


# ------------------------------------------------------------ Estadísticas
def pagina_stats():
    st.title("Mis estadísticas")
    df = db.movimientos()
    if vacio(df):
        return
    sel = st.selectbox("Período", [TODO] + meses_de(df), format_func=etiqueta)
    d = df if sel == TODO else df[df.mes == sel]
    ing, gas = d[d.tipo == "Ingreso"].monto.sum(), d[d.tipo == "Gasto"].monto.sum()
    c = st.columns(4)
    with c[0]: tarjeta("Ingresos", soles(ing), etiqueta(sel), VERDE)
    with c[1]: tarjeta("Gastos", soles(gas), etiqueta(sel))
    with c[2]: tarjeta("Balance", soles(ing - gas), "Ingresos − gastos", VERDE if ing >= gas else ROJO)
    with c[3]: tarjeta("Gastos / ingresos", f"{gas / ing:.0%}" if ing else "—", "Porcentaje")
    r = resumen(df)
    a, b = st.columns(2)
    with a:
        top = d[d.tipo == "Gasto"].groupby("categoria", as_index=False).monto.sum().sort_values("monto")
        if top.empty:
            st.caption("No hay gastos en este período.")
        else:
            graficar(px.bar(top, x="monto", y="categoria", orientation="h", title="Categorías con mayores gastos",
                            color_discrete_sequence=[AZUL]).update_layout(xaxis_title="S/", yaxis_title=""))
    with b:
        g_linea(r, ["Ingresos", "Gastos"], "Evolución de ingresos y gastos")
    st.subheader("Resumen mensual")
    st.dataframe(r, use_container_width=True, hide_index=True,
                 column_config={k: st.column_config.NumberColumn(format="S/ %.2f") for k in ("Ingresos", "Gastos", "Balance")})


# ------------------------------------------------------------ Ahorros
def campos_meta(pref, m=None):
    c1, c2 = st.columns(2)
    nombre = c1.text_input("Nombre de la meta", value=m.nombre if m is not None else "", key=f"{pref}_n")
    desc = c2.text_input("Descripción", value=(m.descripcion or "") if m is not None else "", key=f"{pref}_d")
    obj = c1.number_input("Monto objetivo (S/)", min_value=0.0, step=50.0, format="%.2f",
                          value=float(m.objetivo) if m is not None else 0.0, key=f"{pref}_o")
    aho = c2.number_input("Cantidad ahorrada (S/)", min_value=0.0, step=10.0, format="%.2f",
                          value=float(m.ahorrado) if m is not None else 0.0, key=f"{pref}_a")
    lim0 = dt.date.fromisoformat(m.limite) if m is not None and isinstance(m.limite, str) else None
    usar = c1.checkbox("Tiene fecha límite", value=lim0 is not None, key=f"{pref}_u")
    lim = c2.date_input("Fecha límite", lim0 or dt.date.today(), format="DD/MM/YYYY", key=f"{pref}_l", **FECHAS)
    return nombre, desc, obj, aho, (lim if usar else None)


def meta_valida(nombre, obj):
    if not nombre.strip():
        st.error("Escribe el nombre de la meta.")
    elif obj <= 0:
        st.error("El monto objetivo debe ser mayor que cero.")
    else:
        return True
    return False


def pagina_ahorros():
    st.title("Mis ahorros")
    st.caption("Los ahorros se registran aquí de forma independiente: no modifican tu saldo disponible.")
    metas = db.metas()
    n = S.setdefault("n_meta", 0)
    with st.expander("Nueva meta de ahorro", expanded=metas.empty):
        with st.form(f"meta_nueva_{n}"):
            nombre, desc, obj, aho, lim = campos_meta(f"mn{n}")
            ok = st.form_submit_button("Crear meta", type="primary")
        if ok and meta_valida(nombre, obj):
            db.agregar_meta(nombre, desc, obj, aho, lim)
            S.n_meta += 1
            S.aviso = "Meta creada."
            st.rerun()
    if metas.empty:
        st.info("Aún no tienes metas de ahorro.")
    for m in metas.itertuples():
        p = m.ahorrado / m.objetivo
        plazo = f" · Fecha límite: {dt.date.fromisoformat(m.limite):%d/%m/%Y}" if isinstance(m.limite, str) else ""
        falta = max(m.objetivo - m.ahorrado, 0)
        st.markdown(f"<div class='tarjeta'><b>{m.nombre}</b> <span class='s'>{m.descripcion or ''}</span><br>"
                    f"{soles(m.ahorrado)} de {soles(m.objetivo)} · <b>{p:.0%}</b>{barra(p, VERDE)}"
                    f"<span class='s'>{'¡Meta alcanzada!' if falta == 0 else 'Te faltan ' + soles(falta)}{plazo}</span></div>",
                    unsafe_allow_html=True)
        with st.expander("Editar o eliminar"):
            with st.form(f"meta_ed_{m.id}"):
                nombre, desc, obj, aho, lim = campos_meta(f"me{m.id}", m)
                g = st.form_submit_button("Guardar cambios", type="primary")
            if g and meta_valida(nombre, obj):
                db.editar_meta(m.id, nombre, desc, obj, aho, lim)
                S.aviso = "Meta actualizada."
                st.rerun()
            with st.popover("Eliminar meta"):
                st.write("Esta acción no se puede deshacer.")
                if st.button("Confirmar eliminación", key=f"delm_{m.id}"):
                    db.eliminar_meta(m.id)
                    S.aviso = "Meta eliminada."
                    st.rerun()


# ------------------------------------------------------------ Exportar
def pagina_exportar():
    st.title("Exportar y copia de seguridad")
    df = db.movimientos()
    if not df.empty:
        c1, c2 = st.columns(2)
        c1.download_button("Descargar movimientos (CSV)", reportes.a_csv(df), "movimientos.csv", "text/csv",
                           use_container_width=True)
        c2.download_button("Descargar movimientos (Excel)", reportes.a_excel(df, resumen(df)), "movimientos.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        st.subheader("Resumen mensual en PDF")
        mes = st.selectbox("Mes", meses_de(df), format_func=etiqueta)
        d = df[df.mes == mes]
        if d.empty:
            st.info("Ese mes no tiene movimientos.")
        else:
            st.download_button("Descargar resumen (PDF)", reportes.a_pdf(etiqueta(mes), d, db.presupuestos().get("TOTAL", 0)),
                               f"resumen_{mes}.pdf", "application/pdf")
    else:
        vacio(df)
    st.divider()
    st.subheader("Copia de seguridad")
    st.caption("En Streamlit Community Cloud el almacenamiento puede borrarse al reiniciar la app. "
               "Descarga tu copia con regularidad y restáurala cuando haga falta.")
    if db.DB.exists():
        st.download_button("Descargar copia de seguridad (.db)", db.DB.read_bytes(), "mipresupuesto.db",
                           "application/octet-stream")
    arch = st.file_uploader("Restaurar copia (.db)", type="db")
    if arch is not None and st.button("Restaurar (reemplaza los datos actuales)"):
        try:
            db.restaurar(arch.getvalue())
            S.aviso = "Copia restaurada."
            st.rerun()
        except ValueError as e:
            st.error(str(e))


# ------------------------------------------------------------ Navegación
PAGINAS = {"Panel principal": pagina_panel, "Mis ingresos": lambda: pagina_mov("Ingreso"),
           "Mis gastos": lambda: pagina_mov("Gasto"), "Mi presupuesto": pagina_presupuesto,
           "Historial": pagina_historial, "Mis estadísticas": pagina_stats, "Mis ahorros": pagina_ahorros,
           "Exportar y copia": pagina_exportar}
with st.sidebar:
    st.markdown(f"<h2 style='color:{AZUL};margin:0'>Mi<span style='color:{VERDE}'>Presupuesto</span></h2>",
                unsafe_allow_html=True)
    pagina = st.radio("Menú", list(PAGINAS), label_visibility="collapsed")
if S.get("aviso"):
    st.toast(S.pop("aviso"))
PAGINAS[pagina]()
