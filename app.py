from __future__ import annotations

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


st.set_page_config(
    page_title="Controle de Exigências",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def aplicar_estilo() -> None:
    st.markdown(
        """
        <style>
        :root {
          --ink: #14231f;
          --muted: #65736e;
          --green: #0b5745;
          --green-2: #11735a;
          --paper: #f4f7f5;
          --line: #dce5e1;
        }
        .stApp { background: var(--paper); color: var(--ink); }
        [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--line); }
        [data-testid="stHeader"] { background: rgba(244,247,245,.9); }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
        .hero {
          background: linear-gradient(118deg, #083e33 0%, #0b5745 58%, #128068 100%);
          border-radius: 22px; padding: 28px 32px; color: white; margin-bottom: 18px;
          box-shadow: 0 16px 42px rgba(8,62,51,.16);
        }
        .hero-kicker { font-size: .75rem; letter-spacing: .14em; text-transform: uppercase; opacity: .75; }
        .hero h1 { margin: 6px 0 7px; font-size: clamp(1.8rem, 4vw, 2.7rem); line-height: 1.05; }
        .hero p { margin: 0; opacity: .84; max-width: 760px; }
        div[data-testid="stMetric"] {
          background: white; border: 1px solid var(--line); padding: 15px 17px;
          border-radius: 16px; box-shadow: 0 5px 18px rgba(18,45,37,.045);
        }
        div[data-testid="stMetricLabel"] { color: var(--muted); }
        div[data-testid="stMetricValue"] { color: var(--ink); }
        div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
        h2, h3 { color: var(--ink); letter-spacing: -.02em; }
        .section-note { color: var(--muted); font-size: .9rem; margin-top: -12px; margin-bottom: 12px; }
        .signal {
          background: white; border: 1px solid var(--line); border-left: 5px solid #d89b25;
          border-radius: 13px; padding: 13px 16px; margin: 6px 0 18px;
        }
        .stDownloadButton button { border-radius: 10px; border-color: var(--green); color: var(--green); }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("## Filtros")
    status_opcoes = sorted(df["status"].dropna().astype(str).unique())
    status = st.sidebar.multiselect("Status", status_opcoes, default=status_opcoes)

    segurados = sorted(df["segurado"].dropna().astype(str).unique())
    segurado = st.sidebar.multiselect("Segurado", segurados)

    inspetores = sorted(v for v in df["inspetor"].dropna().astype(str).unique() if v.strip())
    inspetor = st.sidebar.multiselect("Inspetor", inspetores)

    busca = st.sidebar.text_input("Buscar", placeholder="Título, endereço ou descrição")
    intervalo = st.sidebar.date_input("Prazo final", value=(), format="DD/MM/YYYY")

    filtrado = df[df["status"].isin(status)].copy()
    if segurado:
        filtrado = filtrado[filtrado["segurado"].isin(segurado)]
    if inspetor:
        filtrado = filtrado[filtrado["inspetor"].isin(inspetor)]
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
    if isinstance(intervalo, (tuple, list)) and len(intervalo) == 2:
        inicio, fim = pd.Timestamp(intervalo[0]), pd.Timestamp(intervalo[1])
        filtrado = filtrado[filtrado["prazo_final"].between(inicio, fim)]

    st.sidebar.caption(f"{len(filtrado):,} de {len(df):,} exigências exibidas".replace(",", "."))
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

    colunas = st.columns(5)
    colunas[0].metric("Total", total)
    colunas[1].metric("Em andamento", andamento, f"{percentual(andamento, total):.0f}%")
    colunas[2].metric("Atrasadas", atrasado, f"{percentual(atrasado, total):.0f}%", delta_color="inverse")
    colunas[3].metric("Finalizadas", finalizado, f"{percentual(finalizado, total):.0f}%")
    colunas[4].metric("Atraso médio", f"{atraso_medio} dias")


def renderizar_graficos(df: pd.DataFrame) -> None:
    esquerda, direita = st.columns([1, 1], gap="large")
    with esquerda:
        st.subheader("Situação das exigências")
        contagem = df["status"].value_counts().rename_axis("Status").to_frame("Exigências")
        st.bar_chart(contagem, color="#0b5745", horizontal=True, height=285)
    with direita:
        st.subheader("Segurados com mais pendências")
        pendentes = df[df["status"] != "Finalizado"]
        ranking = (
            pendentes.groupby("segurado").size().sort_values(ascending=False).head(8)
            .rename_axis("Segurado").to_frame("Pendências")
        )
        st.bar_chart(ranking, color="#d89b25", horizontal=True, height=285)


def renderizar_alertas(df: pd.DataFrame) -> None:
    hoje = pd.Timestamp(date.today())
    limite = hoje + pd.to_timedelta(15, unit="D")
    proximos = df[
        (df["status"] == "Em andamento")
        & df["prazo_final"].notna()
        & df["prazo_final"].between(hoje, limite)
    ].sort_values("prazo_final")
    if proximos.empty:
        return
    st.markdown(
        f'<div class="signal"><strong>{len(proximos)} exigência(s)</strong> vencem nos próximos 15 dias. '
        "Use o filtro de prazo para analisar esse grupo.</div>",
        unsafe_allow_html=True,
    )


def renderizar_tabela(df: pd.DataFrame) -> None:
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

    st.markdown(
        """
        <div class="hero">
          <div class="hero-kicker">Inspeção de riscos</div>
          <h1>Controle de Exigências</h1>
          <p>Acompanhamento de prazos, pendências e conclusões das cartas de recomendação.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("# 🛡️ Controle")
    st.sidebar.caption(f"Fonte: {fonte}")
    st.sidebar.caption("Atualização automática: a cada 30 segundos")
    if st.sidebar.button("🔄 Atualizar agora", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    if fonte == "Dados de demonstração":
        st.sidebar.info("O painel está em demonstração. Configure os segredos para conectar sua planilha.")

    filtrado = aplicar_filtros(dados)
    renderizar_metricas(filtrado)
    renderizar_alertas(filtrado)
    renderizar_graficos(filtrado)
    renderizar_tabela(filtrado)
    st.caption(
        f"Dados consultados em {datetime.now():%d/%m/%Y às %H:%M:%S} "
        "• atualização automática a cada 30 segundos"
    )


if __name__ == "__main__":
    st_autorefresh(interval=30_000, key="atualizacao_automatica")
    renderizar_dashboard()
