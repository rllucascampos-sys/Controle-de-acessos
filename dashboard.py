import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Data Insights AP", layout="wide", page_icon="📈")

# --- ESTILO CSS PROFISSIONAL ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
    }
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1f77b4; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Gestão Estratégica de Acessos")
st.markdown("Análise avançada de retenção e engajamento.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configurações")
    tipo_planilha = st.radio(
        "Modelo de Dados",
        ("Padrão Ebskills", "Outra Planilha (Regra 11 Meses)")
    )
    st.divider()
    arquivo = st.file_uploader("📂 Carregar base de dados", type=['csv', 'xlsx'])

if arquivo:
    try:
        # 1. LEITURA (Detectando separador do teu CSV)
        if arquivo.name.endswith('.csv'):
            try:
                df = pd.read_csv(arquivo, sep=';', engine='python')
            except:
                arquivo.seek(0)
                df = pd.read_csv(arquivo, sep=',', engine='python')
        else:
            df = pd.read_excel(arquivo)

        df.columns = df.columns.str.strip()
        
        # 2. LIMPEZA DE EQUIPE (EB)
        col_email = next((c for c in df.columns if 'email' in c.lower()), None)
        if col_email:
            df = df[~df[col_email].astype(str).str.contains('ebtreinamentos|ebedu', case=False)]

        df_final = pd.DataFrame()
        coluna_data_acesso = ""

        # ==============================================================================
        # MODO 1: EBSKILLS (REGRA ORIGINAL)
        # ==============================================================================
        if tipo_planilha == "Padrão Ebskills":
            st.info("💡 Modo Ebskills: Análise de base ativa total.")
            col_status = 'Staus' if 'Staus' in df.columns else 'Status'
            if col_status in df.columns:
                df = df[df[col_status].astype(str).str.strip().str.capitalize() == 'Ativo']
            
            perfis = ['AlunoComunidade', 'AlunoCursos', 'AlunoCompleto', 'AlunoBasico']
            if 'Perfil' in df.columns:
                selecao = st.multiselect("Filtrar Perfis:", perfis, default=perfis)
                df_final = df[df['Perfil'].isin(selecao)].copy()
            else:
                df_final = df.copy()
            
            coluna_data_acesso = 'Último login'

        # ==============================================================================
        # MODO 2: OUTRAS PLANILHAS (JANELA 11 MESES - USANDO DATA DE ACESSO)
        # ==============================================================================
        else:
            st.info("🎯 Modo Outras Planilhas: Regra de 11 meses (ignora mês atual).")
            
            # Prioriza "último acesso" em vez de "criação"
            colunas = df.columns.tolist()
            termos_acesso = ['acesso', 'login', 'last', 'último']
            idx_sugerido = next((i for i, c in enumerate(colunas) if any(t in c.lower() for t in termos_acesso) and 'cria' not in c.lower()), 0)
            
            coluna_data_acesso = st.selectbox("Selecione a coluna de ÚLTIMO ACESSO:", colunas, index=idx_sugerido)

            # Cálculo da Janela Móvel
            hoje = datetime.datetime.now()
            data_fim = hoje.replace(day=1) - datetime.timedelta(days=1)
            mes_inicio = hoje.month + 1
            ano_inicio = hoje.year - 1
            if mes_inicio > 12: 
                mes_inicio = 1
                ano_inicio = hoje.year
            data_inicio = datetime.datetime(ano_inicio, mes_inicio, 1)

            st.success(f"📅 Analisando Acessos entre: **{data_inicio.strftime('%d/%m/%Y')}** e **{data_fim.strftime('%d/%m/%Y')}**")

            # Converte e aplica o filtro
            df['dt_temp'] = pd.to_datetime(df[coluna_data_acesso], errors='coerce')
            df_final = df[(df['dt_temp'] >= data_inicio) & (df['dt_temp'] <= data_fim)].copy()

            # Filtro por Tags (Muito útil para as tuas planilhas)
            if 'Tags' in df_final.columns:
                tags_unicas = df_final['Tags'].dropna().unique()
                tags_sel = st.multiselect("Segmentar por Tags:", tags_unicas)
                if tags_sel:
                    df_final = df_final[df_final['Tags'].isin(tags_sel)]

        # ==============================================================================
        # DASHBOARD E GRÁFICOS INTERATIVOS
        # ==============================================================================
        if df_final.empty:
            st.warning("Nenhum dado encontrado para os filtros aplicados.")
        else:
            # Cálculos de Recência
            df_final['dt_proc'] = pd.to_datetime(df_final[coluna_data_acesso], errors='coerce')
            hoje_ref = datetime.datetime.now()
            df_final['dias'] = (hoje_ref - df_final['dt_proc']).dt.days

            m_nunca = df_final['dt_proc'].isna()
            m_15_30 = (df_final['dias'] >= 15) & (df_final['dias'] <= 30)
            m_30_60 = (df_final['dias'] > 30) & (df_final['dias'] <= 60)
            m_60_mais = (df_final['dias'] > 60)
            m_ativos = (df_final['dias'] < 15)

            # --- CARDS KPI ---
            st.markdown("### 🚀 Indicadores de Retenção")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Nunca Acessou", m_nunca.sum())
            c2.metric("Alerta (15-30d)", m_15_30.sum())
            c3.metric("Risco (30-60d)", m_30_60.sum())
            c4.metric("Inativos (+60d)", m_60_mais.sum())
            c5.metric("Ativos (<15d)", m_ativos.sum())

            # --- GRÁFICO PLOTLY ---
            st.markdown("---")
            dados_fig = pd.DataFrame({
                'Status': ['Nunca', '15-30d', '30-60d', '+60d', 'Ativos'],
                'Qtd': [m_nunca.sum(), m_15_30.sum(), m_30_60.sum(), m_60_mais.sum(), m_ativos.sum()]
            })
            
            fig = px.bar(dados_fig, x='Status', y='Qtd', color='Status', text_auto=True,
                         title="Distribuição de Alunos por Último Acesso",
                         color_discrete_map={'Nunca':'#EF5350','15-30d':'#ffa726','30-60d':'#ffeb3b','+60d':'#90a4ae','Ativos':'#66bb6a'})
            
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            # --- EXPORTAÇÃO ---
            st.markdown("### 📥 Centra de Exportação")
            def to_csv(d): return d.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            
            d1, d2, d3 = st.columns(3)
            d1.download_button("🔴 Lista Desengajados", to_csv(df_final[m_60_mais]), "desengajados.csv")
            d2.download_button("🟡 Lista em Risco", to_csv(df_final[m_15_30 | m_30_60]), "risco.csv")
            d3.download_button("🟢 Base Filtrada", to_csv(df_final), "base_completa.csv")

    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")
