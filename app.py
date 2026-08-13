from __future__ import annotations

import base64
import io
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh


APP_DIR = Path(__file__).resolve().parent
SAMPLE_PATH = APP_DIR / "data" / "exemplo.csv"
LOGO_PATH = APP_DIR / "avla-moodys.jpg"

COLUNAS = {
    "segurado": "Segurado",
    "email": "email",
    "endereco": "Endereço",
    "atividade": "Atividade",
    "data_inspecao": "Data da Inspeção",
    "inspetor": "Inspetor",
    "titulo": "Recomendação/ Exigências",
    "descricao": "Descrição",
    "prazo_dias": "Prazo (dias)",
    "meia_data": "Meia Data",
    "prazo_final": "Prazo Final",
    "finalizado": "Finalizado",
    "data_conclusao": "Data de Conclusão",
    "dias_atraso": "Dias em Atraso",
    "status": "Status",
    "arquivo": "Arquivo de Origem",
}

MESES_PT_BR = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)


st.set_page_config(
    page_title="Painel de Exigências | Avla",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def aplicar_estilo() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#16324f; --muted:#7c91a6; --blue:#1768bd; --blue2:#0d7fe8; --paper:#f3f6fb; --line:#d8e0ea; }
        .stApp { background: var(--paper); color: var(--ink); }
        [data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--line); }
        [data-testid="stHeader"] { background:rgba(243,246,251,.92); }
        .block-container { padding-top:1.2rem; padding-bottom:3rem; max-width:1900px; }
        .topbar {
          display:flex; align-items:center; justify-content:space-between; gap:24px;
          background:linear-gradient(105deg,#1768bd 0%,#0f72ca 100%); color:#fff;
          margin:0 0 24px; padding:18px 26px; border-radius:3px;
          box-shadow:0 8px 24px rgba(23,104,189,.13);
        }
        .brand { display:flex; align-items:center; gap:20px; min-width:0; }
        .brand img { width:138px; height:58px; object-fit:contain; background:#fff; border-radius:8px; padding:5px 10px; }
        .brand-line { width:1px; height:38px; background:rgba(255,255,255,.35); }
        .brand-title { font-size:1.45rem; font-weight:750; letter-spacing:-.015em; white-space:nowrap; }
        .top-meta { text-align:right; font-size:.88rem; opacity:.93; white-space:nowrap; }
        .filter-title { font-size:.76rem; letter-spacing:.09em; text-transform:uppercase; color:#344d65; margin:0 0 3px; }
        div[data-testid="stMetric"] {
          background:#fff; border:1px solid var(--line); padding:15px 19px; min-height:126px;
          border-radius:10px; box-shadow:none;
        }
        div[data-testid="stMetricLabel"] { color:#263f58; text-transform:uppercase; letter-spacing:.04em; font-weight:700; }
        div[data-testid="stMetricValue"] { color:var(--blue); font-weight:700; font-size:1.75rem; }
        div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:9px; overflow:hidden; }
        div[data-baseweb="select"] > div, .stTextInput input { background:#fff; border-color:transparent !important; min-height:47px; }
        div[data-testid="stDateInput"] input { background:#fff; }
        div[data-testid="stTabs"] button { color:#243b53; padding-left:.75rem; padding-right:.75rem; }
        div[data-testid="stTabs"] button[aria-selected="true"] { color:var(--blue); }
        h2, h3 { color:var(--ink); letter-spacing:.01em; text-transform:uppercase; font-size:.92rem !important; }
        .section-note { color: var(--muted); font-size: .9rem; margin-top: -12px; margin-bottom: 12px; }
        .signal {
          background:#fff; border:1px solid var(--line); border-radius:9px;
          padding:12px 16px; margin:8px 0; color:#344d65;
        }
        .signal.warning { border-left:4px solid #f0a120; }
        .signal.danger { border-left:4px solid #d43c36; }
        .chart-card { background:#fff; border:1px solid var(--line); border-radius:10px; padding:18px 20px; }
        .stDownloadButton button, .stButton button { border-radius:7px; border-color:var(--blue); color:var(--blue); }
        @media (max-width: 760px) {
          .topbar { align-items:flex-start; padding:16px; }
          .brand-line, .top-meta { display:none; }
          .brand-title { white-space:normal; font-size:1.05rem; }
          .brand img { width:100px; height:48px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def logo_data_uri() -> str:
    if not LOGO_PATH.exists():
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


def canonico(valor: Any) -> str:
    texto = unicodedata.normalize("NFD", str(valor or ""))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-zA-Z0-9]", "", texto).lower()


def segredo(caminho: str, padrao: Any = None) -> Any:
    atual: Any = st.secrets
    try:
        for parte in caminho.split("."):
            atual = atual[parte]
        return atual
    except (KeyError, TypeError, FileNotFoundError):
        return padrao


@st.cache_data(ttl=20, show_spinner=False)
def carregar_csv_publico(url: str) -> pd.DataFrame:
    return pd.read_csv(url)


@st.cache_data(ttl=20, show_spinner=False)
def carregar_google_sheets(
    spreadsheet_id: str, worksheet_name: str, credenciais: dict[str, Any]
) -> pd.DataFrame:
    import gspread
    from google.oauth2.service_account import Credentials

    escopos = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    credentials = Credentials.from_service_account_info(credenciais, scopes=escopos)
    client = gspread.authorize(credentials)
    worksheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    return pd.DataFrame(worksheet.get_all_records(default_blank=""))


@st.cache_data(ttl=20, show_spinner=False)
def carregar_exemplo() -> pd.DataFrame:
    return pd.read_csv(SAMPLE_PATH)


def carregar_dados() -> tuple[pd.DataFrame, str]:
    spreadsheet_id = segredo("gsheets.spreadsheet_id", "")
    worksheet_name = segredo("gsheets.worksheet", "Base")
    csv_url = segredo("gsheets.public_csv_url", "")
    credenciais = segredo("gcp_service_account", None)

    if spreadsheet_id and credenciais:
        return (
            carregar_google_sheets(spreadsheet_id, worksheet_name, dict(credenciais)),
            "Google Sheets",
        )
    if csv_url:
        return carregar_csv_publico(csv_url), "Google Sheets público"
    return carregar_exemplo(), "Dados de demonstração"


def localizar_coluna(df: pd.DataFrame, nome: str) -> str | None:
    alvo = canonico(nome)
    return next((coluna for coluna in df.columns if canonico(coluna) == alvo), None)


def preparar_dados(bruto: pd.DataFrame) -> pd.DataFrame:
    df = bruto.copy()
    renomear: dict[str, str] = {}
    for chave, nome in COLUNAS.items():
        encontrada = localizar_coluna(df, nome)
        if encontrada:
            renomear[encontrada] = chave
    df = df.rename(columns=renomear)

    essenciais = ["segurado", "endereco", "titulo"]
    ausentes = [COLUNAS[c] for c in essenciais if c not in df.columns]
    if ausentes:
        raise ValueError("Colunas obrigatórias ausentes: " + ", ".join(ausentes))

    for coluna in COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""

    for coluna in ["data_inspecao", "meia_data", "prazo_final", "data_conclusao"]:
        df[coluna] = pd.to_datetime(df[coluna], dayfirst=True, errors="coerce")

    df["prazo_dias"] = pd.to_numeric(df["prazo_dias"], errors="coerce").fillna(0).astype(int)
    df["dias_atraso"] = pd.to_numeric(df["dias_atraso"], errors="coerce").fillna(0).astype(int)
    df["finalizado"] = (
        df["finalizado"].astype(str).str.strip().str.lower().isin({"true", "verdadeiro", "sim", "1"})
    )

    hoje = pd.Timestamp(date.today())
    status_calculado = pd.Series("Em andamento", index=df.index)
    status_calculado.loc[df["prazo_final"].notna() & (df["prazo_final"] < hoje)] = "Atrasado"
    status_calculado.loc[df["finalizado"]] = "Finalizado"
    status_informado = df["status"].astype(str).str.strip()
    df["status"] = status_informado.where(status_informado.ne(""), status_calculado)
    df["status"] = df["status"].replace(
        {"Em Andamento": "Em andamento", "FINALIZADO": "Finalizado", "ATRASADO": "Atrasado"}
    )

    atraso_calculado = (hoje - df["prazo_final"]).dt.days.clip(lower=0).fillna(0).astype(int)
    df.loc[~df["finalizado"], "dias_atraso"] = atraso_calculado.loc[~df["finalizado"]]
    df.loc[df["finalizado"], "dias_atraso"] = 0
    df = df[df["segurado"].astype(str).str.strip().ne("")].reset_index(drop=True)
    return df


def rotulo_competencia(periodo: pd.Period) -> str:
    """Exibe uma competência mensal no formato Julho/2026."""
    return f"{MESES_PT_BR[periodo.month - 1]}/{periodo.year}"


def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    segurados = sorted(df["segurado"].dropna().astype(str).unique())
    inspetores = sorted(v for v in df["inspetor"].dropna().astype(str).unique() if v.strip())
    status_opcoes = sorted(df["status"].dropna().astype(str).unique())
    meses_validos = (
        df["data_inspecao"].dropna().dt.to_period("M").sort_values(ascending=False).unique()
    )
    competencias = {rotulo_competencia(periodo): periodo for periodo in meses_validos}

    c1, c2, c3, c4 = st.columns([1.05, 1.35, 1.15, 1.05], gap="medium")
    with c1:
        st.markdown('<div class="filter-title">Mês da inspeção</div>', unsafe_allow_html=True)
        competencia = st.selectbox(
            "Mês da inspeção",
            ["Todas"] + list(competencias),
            label_visibility="collapsed",
        )
    with c2:
        st.markdown('<div class="filter-title">Segurado</div>', unsafe_allow_html=True)
        segurado = st.selectbox("Segurado", ["Todos"] + segurados, label_visibility="collapsed")
    with c3:
        st.markdown('<div class="filter-title">Inspetor</div>', unsafe_allow_html=True)
        inspetor = st.selectbox("Inspetor", ["Todos"] + inspetores, label_visibility="collapsed")
    with c4:
        st.markdown('<div class="filter-title">Situação</div>', unsafe_allow_html=True)
        status = st.selectbox("Situação", ["Todas"] + status_opcoes, label_visibility="collapsed")

    busca = st.text_input(
        "Buscar nos registros",
        placeholder="Buscar por título, endereço ou descrição...",
        label_visibility="collapsed",
    )

    filtrado = df.copy()
    if competencia != "Todas":
        periodo_selecionado = competencias[competencia]
        filtrado = filtrado[
            filtrado["data_inspecao"].dt.to_period("M") == periodo_selecionado
        ]
    if segurado != "Todos":
        filtrado = filtrado[filtrado["segurado"] == segurado]
    if inspetor != "Todos":
        filtrado = filtrado[filtrado["inspetor"] == inspetor]
    if status != "Todas":
        filtrado = filtrado[filtrado["status"] == status]
    if busca:
        alvo = busca.casefold()
        mascara = (
            filtrado[["segurado", "endereco", "titulo", "descricao"]]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .str.casefold()
            .str.contains(re.escape(alvo), regex=True)
        )
        filtrado = filtrado[mascara]
    st.caption(f"{len(filtrado):,} de {len(df):,} exigências exibidas".replace(",", "."))
    return filtrado


def percentual(parte: int, total: int) -> float:
    return (parte / total * 100) if total else 0.0


def renderizar_metricas(df: pd.DataFrame) -> None:
    total = len(df)
    andamento = int((df["status"] == "Em andamento").sum())
    atrasado = int((df["status"] == "Atrasado").sum())
    finalizado = int((df["status"] == "Finalizado").sum())
    media = df.loc[df["dias_atraso"] > 0, "dias_atraso"].mean()
    atraso_medio = round(media) if pd.notna(media) else 0

    hoje = pd.Timestamp(date.today())
    vence_15 = int(
        ((df["status"] == "Em andamento") & df["prazo_final"].between(hoje, hoje + pd.Timedelta(days=15))).sum()
    )
    taxa = percentual(finalizado, total)

    colunas = st.columns(6)
    colunas[0].metric("Total", total)
    colunas[1].metric("Em andamento", andamento, f"{percentual(andamento, total):.0f}% do total")
    colunas[2].metric("Atrasadas", atrasado, f"{percentual(atrasado, total):.0f}% do total", delta_color="inverse")
    colunas[3].metric("Finalizadas", finalizado, f"{taxa:.0f}% do total")
    colunas[4].metric("Vencem em 15 dias", vence_15)
    colunas[5].metric("Atraso médio", f"{atraso_medio} dias")


def renderizar_graficos(df: pd.DataFrame) -> None:
    total = len(df)
    finalizadas = int((df["status"] == "Finalizado").sum())
    taxa = finalizadas / total if total else 0
    st.subheader("Progresso de atendimento")
    st.progress(taxa, text=f"{taxa:.1%} das exigências concluídas ({finalizadas} de {total})")

    esquerda, direita = st.columns([1, 1], gap="large")
    with esquerda:
        st.subheader("Distribuição por situação")
        contagem = df["status"].value_counts().rename_axis("Status").to_frame("Exigências")
        st.bar_chart(contagem, color="#1768bd", horizontal=True, height=285)
    with direita:
        st.subheader("Maiores pendências por segurado")
        pendentes = df[df["status"] != "Finalizado"]
        ranking = (
            pendentes.groupby("segurado").size().sort_values(ascending=False).head(8)
            .rename_axis("Segurado").to_frame("Pendências")
        )
        st.bar_chart(ranking, color="#e28a14", horizontal=True, height=285)


def renderizar_alertas(df: pd.DataFrame) -> None:
    hoje = pd.Timestamp(date.today())
    limite = hoje + pd.to_timedelta(15, unit="D")
    proximos = df[
        (df["status"] == "Em andamento")
        & df["prazo_final"].notna()
        & df["prazo_final"].between(hoje, limite)
    ].sort_values("prazo_final")
    atrasadas = int((df["status"] == "Atrasado").sum())
    if not proximos.empty:
        st.markdown(
            f'<div class="signal warning">› &nbsp;⚠️ <strong>{len(proximos)} exigência(s)</strong> '
            "vencem nos próximos 15 dias — acompanhe as providências.</div>",
            unsafe_allow_html=True,
        )
    if atrasadas:
        st.markdown(
            f'<div class="signal danger">› &nbsp;🔴 <strong>{atrasadas} exigência(s) atrasada(s)</strong> '
            "— priorize a regularização e o envio das evidências.</div>",
            unsafe_allow_html=True,
        )


def renderizar_tabela(df: pd.DataFrame, chave: str) -> None:
    st.subheader("Controle detalhado")
    st.markdown('<div class="section-note">Selecione uma linha para consultar a descrição completa na tabela.</div>', unsafe_allow_html=True)
    tabela = df[
        [
            "status", "segurado", "titulo", "descricao", "prazo_final",
            "dias_atraso", "inspetor", "endereco", "arquivo",
        ]
    ].copy()
    tabela.columns = [
        "Status", "Segurado", "Exigência", "Descrição", "Prazo final",
        "Dias em atraso", "Inspetor", "Endereço", "Documento",
    ]
    tabela = tabela.sort_values(["Dias em atraso", "Prazo final"], ascending=[False, True])
    st.dataframe(
        tabela,
        key=f"tabela_{chave}",
        width="stretch",
        hide_index=True,
        height=475,
        column_config={
            "Prazo final": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Dias em atraso": st.column_config.NumberColumn(format="%d"),
            "Documento": st.column_config.LinkColumn(display_text="Abrir arquivo"),
            "Descrição": st.column_config.TextColumn(width="large"),
        },
    )
    csv = tabela.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Baixar dados filtrados (.csv)",
        data=csv,
        file_name=f"exigencias_filtradas_{date.today():%Y-%m-%d}.csv",
        mime="text/csv",
        key=f"download_{chave}",
    )


def renderizar_dashboard() -> None:
    aplicar_estilo()
    try:
        bruto, fonte = carregar_dados()
        dados = preparar_dados(bruto)
    except Exception as exc:
        st.error("Não foi possível carregar os dados do dashboard.")
        st.exception(exc)
        st.stop()

    logo = logo_data_uri()
    imagem = f'<img src="{logo}" alt="Avla">' if logo else '<strong style="font-size:2rem">Avla</strong>'
    st.markdown(
        f"""
        <div class="topbar">
          <div class="brand">
            {imagem}
            <div class="brand-line"></div>
            <div class="brand-title">Painel de Exigências e Recomendações</div>
          </div>
          <div class="top-meta">Inspeção de Riscos &nbsp;|&nbsp; Atualizado em {datetime.now():%d/%m/%Y}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("# Controle")
    st.sidebar.caption(f"Fonte: {fonte}")
    st.sidebar.caption("Atualização automática: a cada 30 segundos")
    if st.sidebar.button("🔄 Atualizar agora", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    if fonte == "Dados de demonstração":
        st.sidebar.info("O painel está em demonstração. Configure os segredos para conectar sua planilha.")

    filtrado = aplicar_filtros(dados)
    geral, andamento, finalizados, atrasados = st.tabs(
        ["Visão geral", "Em andamento", "Finalizados", "Atrasados"]
    )
    with geral:
        renderizar_metricas(filtrado)
        renderizar_alertas(filtrado)
        renderizar_graficos(filtrado)
        renderizar_tabela(filtrado, "visao_geral")
    with andamento:
        renderizar_tabela(filtrado[filtrado["status"] == "Em andamento"], "em_andamento")
    with finalizados:
        renderizar_tabela(filtrado[filtrado["status"] == "Finalizado"], "finalizados")
    with atrasados:
        renderizar_tabela(filtrado[filtrado["status"] == "Atrasado"], "atrasados")
    st.caption(
        f"Dados consultados em {datetime.now():%d/%m/%Y às %H:%M:%S} "
        "• atualização automática a cada 30 segundos"
    )


if __name__ == "__main__":
    st_autorefresh(interval=30_000, key="atualizacao_automatica")
    renderizar_dashboard()
