import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Controle de Acessos", layout="wide")

st.title("📊 Controle de Acesso")
st.markdown("Sistema compatível com planilhas **Ebskills** e **Outras Plataformas**.")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuração")
tipo_planilha = st.sidebar.radio(
    "Qual o modelo da planilha?",
    ("Padrão Ebskills", "Outra Planilha (alpaclass)")
)

arquivo = st.file_uploader("📂 Solte seu arquivo Excel (.xlsx) ou CSV aqui", type=['csv', 'xlsx'])

if arquivo is not None:
    try:
        # --- LEITURA DO ARQUIVO ---
        if arquivo.name.endswith('.csv'):
            try:
                df = pd.read_csv(arquivo, sep=None, engine='python')
            except:
                arquivo.seek(0)
                df = pd.read_csv(arquivo, sep=';')
        else:
            df = pd.read_excel(arquivo)

        df.columns = df.columns.str.strip()
        
        # --- LIMPEZA DE EQUIPE EB (PARA AMBOS) ---
        col_email = next((col for col in df.columns if col.lower() in ['email', 'e-mail', 'mail', 'endereço de email']), None)
        if col_email:
            dominios_internos = ('@ebtreinamentos.com', '@ebedu.com.br')
            df = df[~df[col_email].astype(str).str.lower().str.strip().str.endswith(dominios_internos)]

        df_final = pd.DataFrame()
        coluna_data_nome = ""

        # ==============================================================================
        # MODO 1: PADRÃO EBSKILLS (VOLTOU AO ORIGINAL)
        # ==============================================================================
        if tipo_planilha == "Padrão Ebskills":
            st.info("Modo ativado: **Ebskills**. Filtros de Status e Perfil aplicados.")
            
            # Filtro de Status
            col_status = 'Staus' if 'Staus' in df.columns else 'Status'
            if col_status in df.columns:
                df = df[df[col_status].astype(str).str.strip().str.capitalize() == 'Ativo']
            
            # Filtro de Perfil
            perfis_permitidos = ['AlunoComunidade', 'AlunoCursos', 'AlunoCompleto', 'AlunoBasico']
            if 'Perfil' in df.columns:
                df = df[df['Perfil'].isin(perfis_permitidos)]
            
            # Seleção na Sidebar
            perfis_sel = st.sidebar.multiselect("Filtrar Perfis:", perfis_permitidos, default=perfis_permitidos)
            df_final = df[df['Perfil'].isin(perfis_sel)].copy()
            
            coluna_data_nome = 'Último login'

     # ==============================================================================
        # MODO 2: OUTRAS PLANILHAS (Filtro por Criação / Status por Acesso)
        # ==============================================================================
        else:
            st.info("Modo ativado: **Outras Planilhas**. Filtro baseado na Data de Criação.")
            
            colunas_disp = df.columns.tolist()
            
            # Identificação automática sugerida das colunas
            idx_criacao = next((i for i, c in enumerate(colunas_disp) if 'cria' in c.lower()), 0)
            idx_acesso = next((i for i, c in enumerate(colunas_disp) if ('acesso' in c.lower() or 'login' in c.lower()) and 'cria' not in c.lower()), 0)
            
            # Seleção de colunas (Já vem pré-selecionado o que o sistema identificou)
            col_criacao_nome = st.selectbox("Selecione a coluna de DATA DE CRIAÇÃO:", colunas_disp, index=idx_criacao)
            coluna_data_nome = st.selectbox("Selecione a coluna de ÚLTIMO ACESSO:", colunas_disp, index=idx_acesso)
            
            # --- CÁLCULO DA JANELA (11 MESES) ---
            hoje_ref = datetime.datetime.now()
            data_fim = hoje_ref.replace(day=1) - datetime.timedelta(days=1) # Fim do mês passado
            
            mes_inicio = hoje_ref.month + 1
            ano_inicio = hoje_ref.year - 1
            if mes_inicio > 12: 
                mes_inicio = 1
                ano_inicio = hoje_ref.year
            data_inicio = datetime.datetime(ano_inicio, mes_inicio, 1) # Mês seguinte do ano passado

            st.success(f"📅 Analisando alunos CRIADOS entre: {data_inicio.strftime('%d/%m/%Y')} e {data_fim.strftime('%d/%m/%Y')}")

            # Converte a Data de Criação para aplicar o filtro de entrada
            df['dt_criacao_filtro'] = pd.to_datetime(df[col_criacao_nome], errors='coerce')
            
            # FILTRO: Só entram alunos criados dentro da janela (Isso fará bater com seus 12 alunos)
            df_final = df[(df['dt_criacao_filtro'] >= data_inicio) & (df['dt_criacao_filtro'] <= data_fim)].copy()

            if st.checkbox("Quero filtrar uma coluna extra"):
                col_filtro = st.selectbox("Escolha a coluna:", colunas_disp)
                valores = st.multiselect("Manter apenas:", df_final[col_filtro].unique(), default=df_final[col_filtro].unique())
                df_final = df_final[df_final[col_filtro].isin(valores)]

        # ==============================================================================
        # CÁLCULOS E VISUALIZAÇÃO (UNIFICADO)
        # ==============================================================================
        if df_final.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
            st.stop()

        hoje = datetime.datetime.now()
        
        # Converte a data de ACESSO para calcular os dias de atraso e o gráfico
        # dayfirst=True garante compatibilidade com o formato brasileiro (DD/MM/AAAA)
        df_final['data_processada'] = pd.to_datetime(df_final[coluna_data_nome], dayfirst=True, errors='coerce')
        
        df_final['nunca_acessou'] = df_final['data_processada'].isna()
        df_final['dias_atraso'] = (hoje - df_final['data_processada']).dt.days

        # Buckets de Engajamento baseados no ÚLTIMO ACESSO
        mask_nunca = df_final['nunca_acessou']
        mask_15_30 = (df_final['dias_atraso'] >= 15) & (df_final['dias_atraso'] <= 30)
        mask_30_60 = (df_final['dias_atraso'] > 30) & (df_final['dias_atraso'] <= 60)
        mask_60_mais = (df_final['dias_atraso'] > 60)
        mask_mes = (df_final['data_processada'].dt.month == hoje.month) & (df_final['data_processada'].dt.year == hoje.year)
        # Dashboard
        st.divider()
        st.subheader(f"Resultados ({len(df_final)} alunos)")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Nunca Acessou", mask_nunca.sum())
        c2.metric("15-30 Dias", mask_15_30.sum())
        c3.metric("30-60 Dias", mask_30_60.sum())
        c4.metric("+60 Dias", mask_60_mais.sum())
        c5.metric("Mês Atual", mask_mes.sum())

        # Gráfico
        fig, ax = plt.subplots(figsize=(10, 4))
        cats = ['Nunca', '15-30', '30-60', '+60', 'Mês Atual']
        vals = [mask_nunca.sum(), mask_15_30.sum(), mask_30_60.sum(), mask_60_mais.sum(), mask_mes.sum()]
        colors = ['#c0392b', '#e67e22', '#f1c40f', '#7f8c8d', '#27ae60']
        
        barras = ax.bar(cats, vals, color=colors)
        for bar in barras:
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), int(bar.get_height()), ha='center', va='bottom')
        st.pyplot(fig)

        # Exportação
        st.subheader("📥 Baixar Relatórios")
        def to_csv(d): return d.to_csv(sep=';', index=False, encoding='utf-8-sig').encode('utf-8-sig')
        
        col_d = st.columns(4)
        col_d[0].download_button("Lista: Nunca", to_csv(df_final[mask_nunca]), "nunca.csv")
        col_d[1].download_button("Lista: 15-30d", to_csv(df_final[mask_15_30]), "atraso_15_30.csv")
        col_d[2].download_button("Lista: +60d", to_csv(df_final[mask_60_mais]), "atraso_60.csv")
        col_d[3].download_button("Mês Vigente", to_csv(df_final[mask_mes]), "mes_vigente.csv")

    except Exception as e:
        st.error(f"Erro: {e}")
