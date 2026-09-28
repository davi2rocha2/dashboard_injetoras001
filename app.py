import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import base64
from pathlib import Path

# =========================================================
# CONFIGURAÇÃO DA PÁGINA E IDENTIDADE VISUAL (Davi Rocha — Soluções em Dados)
# =========================================================
st.set_page_config(
    page_title="Davi Rocha | OEE Injetoras",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

AZUL = "#12305F"
AZUL_CLARO = "#4C82C4"
AMARELO = "#FFD23F"
CINZA_TEXTO = "#333A44"
FUNDO = "#F5F7FA"

ASSETS = Path(__file__).parent / "assets"
DATA = Path(__file__).parent / "data"


def img_base64(caminho):
    return base64.b64encode(Path(caminho).read_bytes()).decode()


LOGO_COLORIDO = img_base64(ASSETS / "logo-horizontal-colorido.png")
LOGO_BRANCO = img_base64(ASSETS / "logo-horizontal-branco.png")

st.markdown(
    f"""
    <style>
        .stApp {{ background-color: {FUNDO}; }}
        #MainMenu, footer, header {{ visibility: hidden; }}

        .db-header {{
            background: linear-gradient(135deg, {AZUL} 0%, #1B4F8C 100%);
            padding: 22px 32px; border-radius: 10px; margin-bottom: 22px;
            display: flex; align-items: center; justify-content: space-between;
        }}
        .db-header img {{ height: 42px; }}
        .db-header .titulo {{ color: #fff; text-align: right; }}
        .db-header .titulo .t1 {{ font-size: 18px; font-weight: 700; }}
        .db-header .titulo .t2 {{ font-size: 12px; color: #CFE0F5; }}

        .kpi-card {{
            background: #fff; border: 1px solid #E1E6EE; border-radius: 10px;
            padding: 16px 18px; text-align: left;
        }}
        .kpi-card .lbl {{ font-size: 11.5px; color: #5B6472; text-transform: uppercase; letter-spacing: 0.3px; }}
        .kpi-card .val {{ font-size: 28px; font-weight: 700; color: {AZUL}; margin-top: 2px; }}
        .kpi-card .sub {{ font-size: 11px; color: #8A93A3; margin-top: 3px; }}
        .kpi-accent {{ height: 4px; width: 34px; background: {AMARELO}; border-radius: 2px; margin-bottom: 8px; }}

        h1, h2, h3 {{ color: {AZUL}; }}
        section[data-testid="stSidebar"] {{ background-color: #fff; border-right: 1px solid #E1E6EE; }}

        .db-footer {{
            margin-top: 34px; padding: 20px 26px; background: {AZUL}; border-radius: 10px;
            color: #fff;
        }}
        .db-footer .ferramentas {{ display: flex; align-items: center; gap: 18px; margin-top: 6px; }}
        .db-footer .ferramentas img {{ height: 22px; filter: grayscale(0%); }}
        .db-footer .linha1 {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }}
        .db-footer .contatos {{ font-size: 11px; color: #D7E4F5; text-align: right; line-height: 1.7; }}
        .db-footer .tag {{ font-size: 10.5px; color: #B9CFEA; margin-top: 2px; }}
        .db-footer .disclaimer {{ font-size: 9.5px; color: #93A9C4; margin-top: 14px; border-top: 1px solid rgba(255,255,255,0.14); padding-top: 10px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# CARGA E PREPARO DOS DADOS
# =========================================================
@st.cache_data
def carregar_dados():
    df_apon_prod = pd.read_csv(DATA / "apontamento_producao_limpo.csv")
    df_apon_parada = pd.read_csv(DATA / "apontamento_paradas_limpo.csv")
    df_ord_prod = pd.read_csv(DATA / "ordens_producao_limpo.csv")
    df_produtos = pd.read_csv(DATA / "produtos.csv")

    # data/hora completa do apontamento (turno C atravessa a meia-noite)
    df_apon_prod["data"] = pd.to_datetime(df_apon_prod["data"])
    df_apon_prod["inicio_dt"] = pd.to_datetime(df_apon_prod["data"].astype(str) + " " + df_apon_prod["hora_inicio"])
    df_apon_prod["fim_dt"] = pd.to_datetime(df_apon_prod["data"].astype(str) + " " + df_apon_prod["hora_fim"])
    overnight = df_apon_prod["fim_dt"] < df_apon_prod["inicio_dt"]
    df_apon_prod.loc[overnight, "fim_dt"] += pd.Timedelta(days=1)
    df_apon_prod["tempo_produzindo_min"] = (df_apon_prod["fim_dt"] - df_apon_prod["inicio_dt"]).dt.total_seconds() / 60
    df_apon_prod["semana"] = df_apon_prod["data"].dt.to_period("W").astype(str)

    df_apon_parada["inicio"] = pd.to_datetime(df_apon_parada["inicio"])
    df_apon_parada["fim"] = pd.to_datetime(df_apon_parada["fim"])
    df_apon_parada["semana"] = df_apon_parada["inicio"].dt.to_period("W").astype(str)

    # produto e tempo padrão
    df_apon_prod = df_apon_prod.merge(df_ord_prod[["ordem_producao", "cod_produto"]], on="ordem_producao", how="left")
    df_apon_prod = df_apon_prod.merge(df_produtos[["cod_produto", "ciclo_padrao_seg", "cavidades"]], on="cod_produto", how="left")
    df_apon_prod["pecas_totais"] = df_apon_prod["qtd_boa"] + df_apon_prod["qtd_refugo"]
    df_apon_prod["tempo_teorico_min"] = df_apon_prod["pecas_totais"] * (df_apon_prod["ciclo_padrao_seg"] / df_apon_prod["cavidades"]) / 60

    # KPI por máquina e semana
    produzido = df_apon_prod.groupby(["maquina", "semana"]).agg(
        tempo_produzindo_min=("tempo_produzindo_min", "sum"),
        tempo_teorico_min=("tempo_teorico_min", "sum"),
        qtd_boa=("qtd_boa", "sum"),
        qtd_refugo=("qtd_refugo", "sum"),
    ).reset_index()
    parado = df_apon_parada.groupby(["maquina", "semana"])["duracao_min"].sum().reset_index()
    parado = parado.rename(columns={"duracao_min": "tempo_parado_min"})

    kpi = produzido.merge(parado, on=["maquina", "semana"], how="left")
    kpi["tempo_parado_min"] = kpi["tempo_parado_min"].fillna(0)
    kpi["tempo_planejado_min"] = kpi["tempo_produzindo_min"] + kpi["tempo_parado_min"]
    kpi["disponibilidade"] = kpi["tempo_produzindo_min"] / kpi["tempo_planejado_min"]
    kpi["performance"] = kpi["tempo_teorico_min"] / kpi["tempo_produzindo_min"]
    kpi["qualidade"] = kpi["qtd_boa"] / (kpi["qtd_boa"] + kpi["qtd_refugo"])
    kpi["oee"] = kpi["disponibilidade"] * kpi["performance"] * kpi["qualidade"]

    return df_apon_prod, df_apon_parada, kpi


df_apon_prod, df_apon_parada, kpi = carregar_dados()

# =========================================================
# CABEÇALHO
# =========================================================
st.markdown(
    f"""
    <div class="db-header">
        <img src="data:image/png;base64,{LOGO_BRANCO}">
        <div class="titulo">
            <div class="t1">Painel de OEE — Produção com Injetoras</div>
            <div class="t2">Disponibilidade · Performance · Qualidade · Pareto de paradas</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# FILTROS (SIDEBAR)
# =========================================================
st.sidebar.image(f"data:image/png;base64,{LOGO_COLORIDO}", width='stretch')
st.sidebar.markdown("### Filtros")

maquinas_disp = sorted(kpi["maquina"].unique())
semanas_disp = sorted(kpi["semana"].unique())

maquinas_sel = st.sidebar.multiselect("Máquinas", maquinas_disp, default=maquinas_disp)
semanas_sel = st.sidebar.multiselect("Semanas", semanas_disp, default=semanas_disp)

kpi_f = kpi[kpi["maquina"].isin(maquinas_sel) & kpi["semana"].isin(semanas_sel)]
parada_f = df_apon_parada[df_apon_parada["maquina"].isin(maquinas_sel) & df_apon_parada["semana"].isin(semanas_sel)]

if kpi_f.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

# =========================================================
# VISÃO GERAL — CARDS
# =========================================================
st.markdown("## Visão geral")

tempo_prod_total = kpi_f["tempo_produzindo_min"].sum()
tempo_planejado_total = kpi_f["tempo_planejado_min"].sum()
oee_medio = (kpi_f["oee"] * kpi_f["tempo_planejado_min"]).sum() / tempo_planejado_total
disp_media = tempo_prod_total / tempo_planejado_total
perf_media = kpi_f["tempo_teorico_min"].sum() / tempo_prod_total
qual_media = kpi_f["qtd_boa"].sum() / (kpi_f["qtd_boa"].sum() + kpi_f["qtd_refugo"].sum())

col1, col2, col3, col4 = st.columns(4)
cards = [
    (col1, "OEE médio", f"{oee_medio:.1%}", "ponderado pelo tempo planejado"),
    (col2, "Disponibilidade", f"{disp_media:.1%}", "tempo produzindo / tempo planejado"),
    (col3, "Performance", f"{perf_media:.1%}", "ritmo real vs. padrão"),
    (col4, "Qualidade", f"{qual_media:.1%}", "peças boas / total produzido"),
]
for col, lbl, val, sub in cards:
    with col:
        st.markdown(
            f"""<div class="kpi-card"><div class="kpi-accent"></div>
            <div class="lbl">{lbl}</div><div class="val">{val}</div><div class="sub">{sub}</div></div>""",
            unsafe_allow_html=True,
        )

st.markdown("")

# =========================================================
# RANKING DE OEE POR MÁQUINA
# =========================================================
col_a, col_b = st.columns([1, 1])

with col_a:
    st.markdown("### OEE por máquina")
    rank = kpi_f.groupby("maquina").apply(
        lambda d: (d["oee"] * d["tempo_planejado_min"]).sum() / d["tempo_planejado_min"].sum()
    ).reset_index(name="oee")
    rank = rank.sort_values("oee")

    fig = go.Figure(go.Bar(
        x=rank["oee"], y=rank["maquina"], orientation="h",
        marker_color=AZUL_CLARO, text=[f"{v:.1%}" for v in rank["oee"]], textposition="outside",
    ))
    fig.update_layout(
        xaxis_tickformat=".0%", height=380, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    st.plotly_chart(fig, width='stretch')

with col_b:
    st.markdown("### Evolução semanal do OEE")
    evol = kpi_f.groupby(["semana", "maquina"]).apply(
        lambda d: (d["oee"] * d["tempo_planejado_min"]).sum() / d["tempo_planejado_min"].sum()
    ).reset_index(name="oee")

    fig2 = px.line(evol, x="semana", y="oee", color="maquina", markers=True)
    fig2.update_layout(
        yaxis_tickformat=".0%", height=380, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="white", legend_title_text="",
    )
    st.plotly_chart(fig2, width='stretch')

# =========================================================
# PARETO DE PARADAS
# =========================================================
st.markdown("### Pareto de paradas por motivo")

pareto = parada_f.groupby("motivo")["duracao_min"].sum().sort_values(ascending=False).reset_index()
pareto["pct_acumulado"] = pareto["duracao_min"].cumsum() / pareto["duracao_min"].sum() * 100

fig3 = go.Figure()
fig3.add_bar(x=pareto["motivo"], y=pareto["duracao_min"], name="Minutos parados", marker_color=AZUL)
fig3.add_trace(go.Scatter(
    x=pareto["motivo"], y=pareto["pct_acumulado"], name="% acumulado",
    yaxis="y2", mode="lines+markers", line=dict(color=AMARELO, width=3),
))
fig3.update_layout(
    yaxis=dict(title="Minutos parados"),
    yaxis2=dict(title="% acumulado", overlaying="y", side="right", range=[0, 105], ticksuffix="%"),
    height=420, margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="white", paper_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig3, width='stretch')

# =========================================================
# DETALHE POR MÁQUINA
# =========================================================
st.markdown("### Detalhe por máquina")
maquina_foco = st.selectbox("Selecione uma máquina", maquinas_disp)

col_c, col_d = st.columns([1, 1])

with col_c:
    st.markdown(f"**Disponibilidade, performance e qualidade — {maquina_foco}**")
    trend = kpi[kpi["maquina"] == maquina_foco].sort_values("semana")
    fig4 = go.Figure()
    for col_nome, cor in [("disponibilidade", AZUL), ("performance", AZUL_CLARO), ("qualidade", AMARELO)]:
        fig4.add_trace(go.Scatter(x=trend["semana"], y=trend[col_nome], name=col_nome.capitalize(), mode="lines+markers", line=dict(color=cor)))
    fig4.update_layout(
        yaxis_tickformat=".0%", height=340, margin=dict(l=10, r=10, t=36, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig4, width='stretch')

with col_d:
    st.markdown(f"**Minutos parados por motivo — {maquina_foco}**")
    paradas_maq = df_apon_parada[df_apon_parada["maquina"] == maquina_foco]
    paradas_maq = paradas_maq.groupby("motivo")["duracao_min"].sum().sort_values(ascending=True).reset_index()
    fig5 = go.Figure(go.Bar(x=paradas_maq["duracao_min"], y=paradas_maq["motivo"], orientation="h", marker_color=AZUL_CLARO))
    fig5.update_layout(
        height=340, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    st.plotly_chart(fig5, width='stretch')

# =========================================================
# RODAPÉ
# =========================================================
FERRAMENTAS = [
    ("Python", "python", "3776AB"),
    ("Pandas", "pandas", "150458"),
    ("NumPy", "numpy", "013243"),
    ("Google Colab", "googlecolab", "F9AB00"),
    ("Google Sheets", "googlesheets", "34A853"),
    ("Streamlit", "streamlit", "FF4B4B"),
]
icones_html = "".join(
    f'<img src="https://cdn.simpleicons.org/{slug}/{cor}" title="{nome}">'
    for nome, slug, cor in FERRAMENTAS
)

st.markdown(
    f"""
    <div class="db-footer">
        <div class="linha1">
            <div>
                <div style="font-weight:700; font-size:14px;">Davi Rocha — Soluções em Dados</div>
                <div class="tag">Transformando dados em informações úteis para o seu negócio</div>
                <div class="ferramentas">{icones_html}</div>
            </div>
            <div class="contatos">
                <b>WhatsApp</b> (11) 93054-4694<br>
                <b>Instagram</b> @davirocha.dados<br>
                <b>Site</b> davi2rocha2.github.io/Site<br>
                <b>E-mail</b> digitalstar444@gmail.com
            </div>
        </div>
        <div class="disclaimer">Projeto de demonstração — dados simulados, criados para ilustrar a metodologia de análise de indicadores de produção aplicada a clientes reais.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
