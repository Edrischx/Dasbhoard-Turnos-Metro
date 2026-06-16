import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Dashboard Turnos Metro", layout="wide", initial_sidebar_state="expanded")

DATA_FILE = Path(__file__).parent / "base_powerbi_gestion_turnos_metro.xlsx"

METRO_BLUE = "#032B5C"
BLUE = "#1E5BC6"
GREEN = "#39A857"
RED = "#E64B4B"
YELLOW = "#F0B323"
PURPLE = "#6E4DBA"
BG = "#F5F6F8"
TEXT = "#061A3A"

st.markdown(f"""
<style>
    .stApp {{ background-color: {BG}; }}
    [data-testid="stSidebar"] {{ background: linear-gradient(180deg, #021E42 0%, #032B5C 100%); }}
    [data-testid="stSidebar"] * {{ color: white !important; }}
    .main-title {{ font-size: 34px; font-weight: 800; color: {TEXT}; margin-bottom: 0; }}
    .subtitle {{ font-size: 16px; color: {TEXT}; margin-top: 0; margin-bottom: 18px; }}
    .kpi-card {{ background: white; border: 1px solid #DCE3EF; border-radius: 12px; padding: 18px 20px; min-height: 118px; box-shadow: 0 2px 10px rgba(6,26,58,.04); }}
    .kpi-label {{ color: {TEXT}; font-size: 13px; font-weight: 800; text-align:center; text-transform: uppercase; }}
    .kpi-value {{ font-size: 36px; font-weight: 800; text-align:center; margin-top: 8px; }}
    .kpi-note {{ color: {TEXT}; font-size: 13px; text-align:center; margin-top: 5px; }}
    .panel {{ background: white; border: 1px solid #DCE3EF; border-radius: 12px; padding: 16px; box-shadow: 0 2px 10px rgba(6,26,58,.04); }}
    .panel-title {{ color: {TEXT}; font-weight: 800; font-size: 16px; margin-bottom: 8px; text-transform: uppercase; }}
    .risk-card {{ background: white; border: 1px solid #DCE3EF; border-radius: 12px; padding: 18px; min-height: 110px; box-shadow: 0 2px 10px rgba(6,26,58,.04); }}
    .risk-title {{ color: {TEXT}; font-weight: 800; font-size: 13px; text-transform: uppercase; }}
    .risk-value {{ font-size: 25px; font-weight: 800; margin-top: 5px; }}
    div[data-testid="stMetric"] {{ background: white; padding: 12px; border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(uploaded_file=None):
    file = uploaded_file if uploaded_file is not None else DATA_FILE
    fact = pd.read_excel(file, sheet_name="FactServicios")
    dim = pd.read_excel(file, sheet_name="DimConductores")

    # Normaliza nombres de columnas para que funcione aunque el Excel venga con nombres distintos
    alias_map = {
        "Terminal Origen": "Terminal",
        "Estado Cobertura": "Estado",
        "Conductor Titular": "Conductor",
        "Hora Partida": "Hora",
    }
    for original, standard in alias_map.items():
        if standard not in fact.columns and original in fact.columns:
            fact[standard] = fact[original]

    if "Terminal" not in fact.columns:
        fact["Terminal"] = "Sin dato"
    if "Estado" not in fact.columns:
        fact["Estado"] = "Cubierto"
    if "Conductor" not in fact.columns:
        fact["Conductor"] = "Sin dato"

    # Limpieza básica
    for col in ["Terminal", "Estado", "Conductor", "Franja Horaria"]:
        if col in fact.columns:
            fact[col] = fact[col].fillna("Sin dato").astype(str)

    # Si el conductor aparece como Sin Cubrir, también marcamos el estado como Sin Cubrir
    fact.loc[fact["Conductor"].str.lower().str.contains("sin cubrir", na=False), "Estado"] = "Sin Cubrir"

    if "Hora Bucket" in fact.columns:
        fact["Hora Bucket"] = fact["Hora Bucket"].astype(str).str.slice(0,5)
    elif "Hora" in fact.columns:
        fact["Hora Bucket"] = pd.to_datetime(fact["Hora"], errors="coerce").dt.strftime("%H:00").fillna("Sin dato")

    if "Franja Horaria" not in fact.columns:
        fact["Franja Horaria"] = "Sin dato"

    return fact, dim

with st.sidebar:
    st.markdown("""
    <div style='font-size:28px;font-weight:900;line-height:1.05;margin-top:10px;'>◈ METRO<br><span style='font-size:18px;'>DE SANTIAGO</span></div>
    <hr style='border:0;border-top:1px solid rgba(255,255,255,.25);margin:24px 0;'>
    <div style='font-size:18px;font-weight:800;margin-bottom:18px;'>FILTROS</div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("Subir Excel actualizado", type=["xlsx", "xls"])

fact, dim = load_data(uploaded)

with st.sidebar:
    terminales = sorted(fact["Terminal"].dropna().unique()) if "Terminal" in fact else []
    estados = sorted(fact["Estado"].dropna().unique()) if "Estado" in fact else []
    franjas = sorted(fact["Franja Horaria"].dropna().unique()) if "Franja Horaria" in fact else []
    conductores = sorted([x for x in fact["Conductor"].dropna().unique() if x != "Sin Cubrir"]) if "Conductor" in fact else []

    f_terminal = st.multiselect("Terminal", terminales, default=terminales)
    f_estado = st.multiselect("Estado", estados, default=estados)
    f_franja = st.multiselect("Tipo de turno", franjas, default=franjas)
    f_conductor = st.multiselect("Conductor", conductores, default=[])
    st.markdown("<div style='height:260px'></div>", unsafe_allow_html=True)
    st.caption("Última actualización\n20/05/2024 08:30")

filtered = fact.copy()
if f_terminal and "Terminal" in filtered: filtered = filtered[filtered["Terminal"].isin(f_terminal)]
if f_estado and "Estado" in filtered: filtered = filtered[filtered["Estado"].isin(f_estado)]
if f_franja and "Franja Horaria" in filtered: filtered = filtered[filtered["Franja Horaria"].isin(f_franja)]
if f_conductor and "Conductor" in filtered: filtered = filtered[filtered["Conductor"].isin(f_conductor)]

total_turnos = len(filtered)
sin_cubrir = int((filtered["Estado"].str.lower() == "sin cubrir").sum()) if "Estado" in filtered else 0
cubiertos = total_turnos - sin_cubrir
cobertura = cubiertos / total_turnos if total_turnos else 0
conductores_activos = filtered.loc[~filtered["Conductor"].isin(["Sin Cubrir", "Sin dato", ""]), "Conductor"].nunique() if "Conductor" in filtered else 0
sobrecargados = filtered.loc[~filtered["Conductor"].isin(["Sin Cubrir", "Sin dato", ""]), "Conductor"].value_counts()
sobrecargados_count = int((sobrecargados >= 7).sum())

st.markdown("<div class='main-title'>DASHBOARD PLANIFICACIÓN DE TURNOS</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Resumen Operacional - Metro de Santiago</div>", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Conductores Activos</div><div class='kpi-value' style='color:{BLUE}'>{conductores_activos}</div><div class='kpi-note'>Dotación filtrada</div></div>", unsafe_allow_html=True)
with k2:
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Turnos Programados</div><div class='kpi-value' style='color:{GREEN}'>{total_turnos}</div><div class='kpi-note'>Servicios cargados</div></div>", unsafe_allow_html=True)
with k3:
    pct_sc = (sin_cubrir/total_turnos*100) if total_turnos else 0
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Turnos Sin Cubrir</div><div class='kpi-value' style='color:{RED}'>{sin_cubrir}</div><div class='kpi-note'>{pct_sc:.1f}% del total</div></div>", unsafe_allow_html=True)
with k4:
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Cobertura General</div><div class='kpi-value' style='color:{PURPLE}'>{cobertura:.1%}</div><div class='kpi-note'>Turnos cubiertos {cubiertos}</div></div>", unsafe_allow_html=True)

st.write("")

c1, c2 = st.columns([1.25, 1])
with c1:
    st.markdown("<div class='panel-title'>Turnos programados por hora</div>", unsafe_allow_html=True)
    if {"Hora Bucket", "Terminal"}.issubset(filtered.columns):
        hour_df = filtered.groupby(["Hora Bucket", "Terminal"]).size().reset_index(name="Turnos")
        fig = px.bar(hour_df, x="Hora Bucket", y="Turnos", color="Terminal", barmode="stack", color_discrete_sequence=[BLUE, GREEN, YELLOW])
        fig.update_layout(height=360, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white", legend_title_text="", xaxis_title="Hora de inicio", yaxis_title="N° de turnos")
        st.plotly_chart(fig, use_container_width=True)
with c2:
    st.markdown("<div class='panel-title'>Servicios sin cubrir por terminal</div>", unsafe_allow_html=True)
    if {"Terminal", "Estado"}.issubset(filtered.columns):
        sc = filtered[filtered["Estado"].str.lower() == "sin cubrir"].groupby("Terminal").size().reset_index(name="Cantidad")
        if sc.empty:
            sc = pd.DataFrame({"Terminal":["Sin pendientes"],"Cantidad":[0]})
        fig = px.pie(sc, names="Terminal", values="Cantidad", hole=.55, color_discrete_sequence=[RED, YELLOW, BLUE])
        fig.update_traces(textposition='outside', textinfo='percent+label')
        fig.update_layout(height=360, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", annotations=[dict(text=str(sin_cubrir), x=0.5, y=0.54, font_size=30, showarrow=False), dict(text="Total", x=0.5, y=0.43, font_size=14, showarrow=False)])
        st.plotly_chart(fig, use_container_width=True)

c3, c4, c5 = st.columns([.9, .95, 1.1])
with c3:
    st.markdown("<div class='panel-title'>Distribución de turnos por franja horaria</div>", unsafe_allow_html=True)
    if "Franja Horaria" in filtered.columns:
        fr = filtered.groupby("Franja Horaria").size().reset_index(name="Turnos")
        fig = px.pie(fr, names="Franja Horaria", values="Turnos", hole=.55, color_discrete_sequence=[BLUE, GREEN, PURPLE])
        fig.update_layout(height=310, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
with c4:
    st.markdown("<div class='panel-title'>Carga de turnos por día de la semana</div>", unsafe_allow_html=True)
    days = pd.DataFrame({"Día":["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"],"Turnos":[868,872,865,870,867,432,301]})
    fig = px.bar(days, x="Día", y="Turnos", text="Turnos", color_discrete_sequence=[BLUE])
    fig.update_layout(height=310, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white", xaxis_title="", yaxis_title="N° de turnos")
    st.plotly_chart(fig, use_container_width=True)
with c5:
    st.markdown("<div class='panel-title'>Top 10 conductores con mayor carga</div>", unsafe_allow_html=True)
    top = filtered.loc[~filtered["Conductor"].isin(["Sin Cubrir", "Sin dato", ""]), "Conductor"].value_counts().head(10).reset_index()
    top.columns = ["Conductor", "Turnos"]
    fig = px.bar(top.sort_values("Turnos"), x="Turnos", y="Conductor", orientation="h", text="Turnos", color_discrete_sequence=[BLUE])
    fig.update_layout(height=310, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="white", plot_bgcolor="white", xaxis_title="N° turnos", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("<div class='panel-title'>Resumen de riesgos operacionales</div>", unsafe_allow_html=True)
r1, r2, r3, r4 = st.columns(4)
with r1:
    st.markdown(f"<div class='risk-card'><div class='risk-title'>⚠️ Turnos sin cubrir</div><div class='risk-value' style='color:{RED}'>{sin_cubrir}</div><div>{pct_sc:.1f}% del total programado</div></div>", unsafe_allow_html=True)
with r2:
    st.markdown(f"<div class='risk-card'><div class='risk-title'>👥 Sobrecarga de conductores</div><div class='risk-value' style='color:#F08A00'>{sobrecargados_count}</div><div>Conductores con 7+ turnos</div></div>", unsafe_allow_html=True)
with r3:
    st.markdown(f"<div class='risk-card'><div class='risk-title'>🕘 Concentración AM / hora punta</div><div class='risk-value' style='color:#F0A000'>06:00 - 09:00</div><div>Mayor demanda de conductores</div></div>", unsafe_allow_html=True)
with r4:
    st.markdown(f"<div class='risk-card'><div class='risk-title'>✅ Cobertura general</div><div class='risk-value' style='color:{GREEN}'>{cobertura:.1%}</div><div>Nivel de cobertura actual</div></div>", unsafe_allow_html=True)
