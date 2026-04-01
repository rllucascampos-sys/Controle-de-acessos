import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard de Acessos", layout="wide", page_icon="📊")

# --- ESTILIZAÇÃO CSS PERSONALIZADA ---
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .sidebar .sidebar-content {
        background-color: #ffffff;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Dashboard de Controle de Acesso")
st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Configurações")
    tipo_planilha = st.radio(
        "Modelo da Planilha:",
        ("Padrão Ebskills", "Outra Planilha (Alpaclass/CSV)"),
        help="Selecione o formato para aplicar as regras de filtro corretas."
    )
    st.divider()
    arquivo = st.file_uploader("📂 Carregar Arquivo", type=['csv', 'xlsx'])

if arquivo is not None:
    try:
        # 1. LEITURA DO ARQUIVO
        if arquivo.name.endswith('.csv'):
            try:
                df = pd.read_csv(arquivo, sep=';', engine='python')
            except:
                arquivo.seek(0)
                df = pd.read_csv(arquivo, sep=',', engine='python')
        else:
            df = pd.read_excel(arquivo)

        df.columns = df.columns.str.strip()
        
        # 2. LIMPEZA DE EQUIPE
        col_email = next((col for col in df.columns if col.lower() in ['email', 'e-mail', 'mail']), None)
        if col_email:
            dominios = ('@ebtreinamentos.com', '@ebedu.com.br')
            df = df[~df[col_email].astype(str).str.lower().str.strip().str.endswith(dominios)]

        df_final = pd.DataFrame()
        coluna_data_nome = ""

        # ==============================================================================
        # MODO 1: EBSKILLS
        # ==============================================================================
        if tipo_planilha == "Padrão Ebskills":
            st.subheader("📋 Filtros Ebskills")
            
            col_status = 'Staus' if 'Staus' in df.columns else 'Status'
            if col_status in df.columns:
                df = df[df[col_status].astype(str).str.strip().str.capitalize() == 'Ativo']
            
            perfis_permitidos = ['AlunoComunidade', 'AlunoCursos', 'AlunoCompleto', 'AlunoBasico']
            if 'Perfil' in df.columns:
                perfis_existentes = [p for p in perfis_permitidos if p in df['Perfil'].unique()]
                perfis_sel = st.multiselect("Filtrar por Perfil:", perfis_existentes, default=perfis_existentes)
                df_final = df[df['Perfil'].isin(perfis_sel)].copy()
            else:
                df_final = df.copy()
            
            coluna_data_nome = 'Último login'

        # ==============================================================================
        # MODO 2: OUTRAS PLANILHAS (REGRA 11 MESES)
        # ==============================================================================
        else:
            st.subheader("🔍 Filtros Outras Planilhas")
            
            colunas = df.columns.tolist()
            termos_data = ['data', 'login', 'acesso', 'last', 'criado', 'date']
            index_sugestao = next((i for i, col in enumerate(colunas) if any(t in col.lower() for t in termos_data)), 0)
            
            coluna_data_nome = st.selectbox("Selecione a coluna de DATA:", colunas, index=index_sugestao)

            hoje = datetime.datetime.now()
            data_fim = hoje.replace(day=1) - datetime.timedelta(days=1)
            mes_inicio = hoje.month + 1
            ano_inicio = hoje.year - 1
            if mes_inicio > 12: 
                mes_inicio = 1
                ano_inicio = hoje.year
            data_inicio = datetime.datetime(ano_inicio, mes_inicio, 1)

            st.info(f"📅 **Análise Temporal:** {data_inicio.strftime('%b/%y')} a {data_fim.strftime('%b/%y')}")

            df['data_temp'] = pd.to_datetime(df[coluna_data_nome], errors='coerce')
            df_final = df[(df['data_temp'] >= data_inicio) & (df['data_temp'] <= data_fim)].copy()

        # ==============================================================================
        # DASHBOARD VISUAL
        # ==============================================================================
        if df_final.empty:
            st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
        else:
            df_final['data_processada'] = pd.to_datetime(df_final[coluna_data_nome], errors='coerce')
            hoje_ref = datetime.datetime.now()
            df_final['dias_atraso'] = (hoje_ref - df_final['data_processada']).dt.days

            # Mascaras
            m_nunca = df_final['data_processada'].isna()
            m_15_30 = (df_final['dias_atraso'] >= 15) & (df_final['dias_atraso'] <= 30)
            m_30_60 = (df_final['dias_atraso'] > 30) & (df_final['dias_atraso'] <= 60)
            m_60_mais = (df_final['dias_atraso'] > 60)
            m_mes = (df_final['data_processada'].dt.month == hoje_ref.month) & (df_final['data_processada'].dt.year == hoje_ref.year)

            # --- LINHA 1: MÉTRICAS (CARDS) ---
            st.markdown("### 📈 Indicadores Chave")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Sem Acesso", m_nunca.sum(), delta="Total", delta_color="off")
            c2.metric("15-30 Dias", m_15_30.sum(), delta="Crítico", delta_color="inverse")
            c3.metric("30-60 Dias", m_30_60.sum(), delta="Atenção", delta_color="normal")
            c4.metric("+60 Dias", m_60_mais.sum(), delta="Inativo", delta_color="inverse")
            c5.metric("Mês Atual", m_mes.sum(), delta="Novos", delta_color="normal")

            # --- LINHA 2: GRÁFICO ---
            st.markdown("---")
            col_graph, col_info = st.columns([2, 1])

            with col_graph:
                st.markdown("#### Visualização de Engajamento")
                fig, ax = plt.subplots(figsize=(10, 5))
                fig.patch.set_facecolor('#f5f7f9')
                cats = ['Nunca', '15-30d', '30-60d', '+60d', 'Mês Atual']
                vals = [m_nunca.sum(), m_15_30.sum(), m_30_60.sum(), m_60_mais.sum(), m_mes.sum()]
                cores = ['#EF5350', '#FB8C00', '#FDD835', '#90A4AE', '#4CAF50']
                
                bars = ax.bar(cats, vals, color=cores, edgecolor='white', linewidth=0.7)
                ax.set_facecolor('#f5f7f9')
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                
                for bar in bars:
                    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5, 
                            int(bar.get_height()), ha='center', fontweight='bold', color='#444444')
                st.pyplot(fig)

            with col_info:
                st.markdown("#### ℹ️ Resumo")
                st.info(f"Total de alunos processados: **{len(df_final)}**")
                taxa_engajamento = ((m_mes.sum() + (len(df_final) - m_60_mais.sum() - m_nunca.sum())) / len(df_final)) * 100
                st.write(f"Taxa estimada de engajamento: **{taxa_engajamento:.1f}%**")

            # --- LINHA 3: DOWNLOADS ---
            st.markdown("---")
            st.markdown("#### 📥 Exportar Listas")
            def to_csv(d): return d.to_csv(sep=';', index=False, encoding='utf-8-sig').encode('utf-8-sig')
            
            d1, d2, d3, d4 = st.columns(4)
            d1.download_button("📂 Nunca Acessaram", to_csv(df_final[m_nunca]), "nunca.csv")
            d2.download_button("📂 Atraso 15-30d", to_csv(df_final[m_15_30]), "atraso_15_30.csv")
            d3.download_button("📂 Atraso +60d", to_csv(df_final[m_60_mais]), "atraso_60.csv")
            d4.download_button("📂 Mês Vigente", to_csv(df_final[m_mes]), "mes_atual.csv")

    except Exception as e:
        st.error(f"❌ Erro crítico: {e}")
