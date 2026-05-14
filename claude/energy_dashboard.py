import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ─── Config ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Production électrique France",
    page_icon="⚡",
    layout="wide",
)

# ─── Style ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    .main { background-color: #0d1117; }
    .stApp { background-color: #0d1117; }

    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 20px 24px;
        margin-bottom: 8px;
    }
    .metric-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #8b949e;
        margin-bottom: 6px;
    }
    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 28px;
        font-weight: 600;
        color: #e6edf3;
    }
    .metric-unit {
        font-size: 14px;
        font-weight: 300;
        color: #8b949e;
        margin-left: 4px;
    }
    .metric-delta {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        margin-top: 4px;
    }
    h1 {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 22px !important;
        font-weight: 600 !important;
        color: #e6edf3 !important;
        letter-spacing: -0.02em;
    }
    h3 {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #8b949e !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .stSelectbox label, .stDateInput label {
        color: #8b949e !important;
        font-size: 12px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    div[data-testid="stSelectbox"] > div > div {
        background-color: #161b22 !important;
        border-color: #30363d !important;
        color: #e6edf3 !important;
    }
    .stAlert { background-color: #161b22; border-color: #30363d; }
</style>
""", unsafe_allow_html=True)

# ─── Constantes ───────────────────────────────────────────────────────────────
API_URL = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-tr/records"

SOURCES = {
    "nucleaire": {"label": "Nucléaire",  "color": "#3fb950", "fill": "rgba(63,185,80,0.08)",  "emoji": "☢️"},
    "eolien":    {"label": "Éolien",     "color": "#58a6ff", "fill": "rgba(88,166,255,0.08)", "emoji": "💨"},
    "solaire":   {"label": "Solaire",    "color": "#f0b429", "fill": "rgba(240,180,41,0.08)", "emoji": "☀️"},
}

# ─── Récupération des données ─────────────────────────────────────────────────
@st.cache_data(ttl=300)  # cache 5 minutes
def fetch_data(date_debut: str, date_fin: str) -> pd.DataFrame:
    params = {
        "where": f"date_heure >= '{date_debut}T00:00:00Z' AND date_heure <= '{date_fin}T23:59:59Z'",
        "select": "date_heure,nucleaire,eolien,solaire",
        "order_by": "date_heure ASC",
        "limit": 100,
    }
    rows = []
    offset = 0

    with st.spinner("Chargement des données..."):
        while True:
            params["offset"] = offset
            r = requests.get(API_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            if not results:
                break
            rows.extend(results)
            if len(rows) >= data.get("total_count", 0):
                break
            offset += 100

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["date_heure"] = pd.to_datetime(df["date_heure"], utc=True).dt.tz_convert("Europe/Paris")
    df = df.sort_values("date_heure").reset_index(drop=True)
    for col in ["nucleaire", "eolien", "solaire"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

# ─── UI ───────────────────────────────────────────────────────────────────────
st.title("⚡ Production électrique — Réseau français")
st.markdown("<p style='color:#8b949e; font-size:13px; margin-top:-12px;'>Source : ODRE / RTE • Données temps réel eco2mix</p>", unsafe_allow_html=True)

st.markdown("---")

col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 2])

with col_ctrl1:
    periode = st.selectbox(
        "Période",
        ["Aujourd'hui", "Hier", "7 derniers jours", "30 derniers jours", "Personnalisé"],
    )

today = datetime.now().date()

if periode == "Aujourd'hui":
    date_debut = date_fin = today
elif periode == "Hier":
    date_debut = date_fin = today - timedelta(days=1)
elif periode == "7 derniers jours":
    date_debut = today - timedelta(days=6)
    date_fin = today
elif periode == "30 derniers jours":
    date_debut = today - timedelta(days=29)
    date_fin = today
else:
    with col_ctrl2:
        date_debut = st.date_input("Du", today - timedelta(days=6))
    with col_ctrl3:
        date_fin = st.date_input("Au", today)

# ─── Chargement ───────────────────────────────────────────────────────────────
df = fetch_data(str(date_debut), str(date_fin))

if df.empty:
    st.warning("Aucune donnée disponible pour cette période.")
    st.stop()

# ─── Métriques ────────────────────────────────────────────────────────────────
st.markdown("### Moyennes sur la période")

col1, col2, col3 = st.columns(3)

for col, (key, meta) in zip([col1, col2, col3], SOURCES.items()):
    moy = df[key].mean()
    maxi = df[key].max()
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{meta['emoji']} {meta['label']}</div>
            <div class="metric-value">{moy:,.0f}<span class="metric-unit">MW</span></div>
            <div class="metric-delta" style="color:{meta['color']}">↑ max {maxi:,.0f} MW</div>
        </div>
        """, unsafe_allow_html=True)

# ─── Graphique principal ───────────────────────────────────────────────────────
st.markdown("### Production au fil du temps")

fig = go.Figure()

for key, meta in SOURCES.items():
    fig.add_trace(go.Scatter(
        x=df["date_heure"],
        y=df[key],
        name=f"{meta['emoji']} {meta['label']}",
        line=dict(color=meta["color"], width=2),
        fill="tozeroy",
        fillcolor=meta["fill"],
        hovertemplate=f"<b>{meta['label']}</b><br>%{{x|%d/%m %H:%M}}<br>%{{y:,.0f}} MW<extra></extra>",
    ))

fig.update_layout(
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    font=dict(family="IBM Plex Mono", color="#8b949e", size=11),
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="left", x=0,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color="#e6edf3"),
    ),
    xaxis=dict(
        gridcolor="#21262d",
        tickformat="%d/%m\n%H:%M",
        tickfont=dict(size=10),
        showline=True, linecolor="#30363d",
    ),
    yaxis=dict(
        title="MW",
        gridcolor="#21262d",
        tickformat=",",
        showline=True, linecolor="#30363d",
    ),
    hovermode="x unified",
    margin=dict(l=0, r=0, t=40, b=0),
    height=420,
)

st.plotly_chart(fig, use_container_width=True)

# ─── Répartition (camembert) ──────────────────────────────────────────────────
st.markdown("### Répartition moyenne")

col_pie, col_bar = st.columns(2)

totaux = {key: df[key].mean() for key in SOURCES}

with col_pie:
    fig_pie = go.Figure(go.Pie(
        labels=[SOURCES[k]["label"] for k in totaux],
        values=list(totaux.values()),
        marker=dict(colors=[SOURCES[k]["color"] for k in totaux]),
        hole=0.6,
        textinfo="label+percent",
        textfont=dict(family="IBM Plex Mono", size=11, color="#e6edf3"),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} MW<br>%{percent}<extra></extra>",
    ))
    fig_pie.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        showlegend=False,
        margin=dict(l=0, r=0, t=20, b=0),
        height=280,
        annotations=[dict(
            text=f"<b>{sum(totaux.values()):,.0f}</b><br>MW moy.",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family="IBM Plex Mono", size=13, color="#e6edf3"),
        )],
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_bar:
    # Barres horaires empilées (moyennées par heure)
    df["heure"] = df["date_heure"].dt.hour
    df_h = df.groupby("heure")[["nucleaire", "eolien", "solaire"]].mean().reset_index()

    fig_bar = go.Figure()
    for key, meta in SOURCES.items():
        fig_bar.add_trace(go.Bar(
            x=df_h["heure"],
            y=df_h[key],
            name=meta["label"],
            marker_color=meta["color"],
            hovertemplate=f"<b>{meta['label']}</b><br>%{{x}}h → %{{y:,.0f}} MW<extra></extra>",
        ))
    fig_bar.update_layout(
        barmode="stack",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(family="IBM Plex Mono", color="#8b949e", size=10),
        xaxis=dict(title="Heure", gridcolor="#21262d", ticksuffix="h"),
        yaxis=dict(title="MW", gridcolor="#21262d"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#e6edf3")),
        margin=dict(l=0, r=0, t=20, b=0),
        height=280,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<p style='color:#484f58; font-size:11px; font-family: IBM Plex Mono;'>"
    f"Données : {len(df)} points • "
    f"Période : {date_debut} → {date_fin} • "
    f"Mis à jour toutes les 5 min</p>",
    unsafe_allow_html=True,
)
