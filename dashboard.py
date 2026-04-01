import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="controle de acessos", layout="wide")

st.title("📊 Controle de Acesso")
st.markdown("Sistema compatível com planilhas **Ebskills** e **Outras Plataformas** (Hotmart, CSVs genéricos, etc).")

# --- BARRA LATERAL: ESCOLHA DO MODO ---
st.sidebar.header("⚙️ Configuração")
tipo_planilha = st.sidebar.radio(
    "Qual o modelo da planilha?",
    ("Padrão Ebskills", "Outra Planilha (alpaclass)")
)

# --- UPLOAD ---
arquivo = st.file_uploader("📂 Solte seu arquivo Excel (.xlsx) ou CSV aqui", type=['csv', 'xlsx'])

if arquivo is not None:
    try:
        # --- LEITURA INTELIGENTE DO ARQUIVO ---
        if arquivo.name.endswith('.csv'):
            try:
                df = pd.read_csv(arquivo, sep=None, engine='python')
            except:
                arquivo.seek(0)
                df = pd.read_csv(arquivo, sep=';')
        else:
            df = pd.read_excel(arquivo)

        # Remove espaços extras dos nomes das colunas
        df.columns = df.columns.str.strip()
        
        # --- LIMPEZA AUTOMÁTICA DE EQUIPE (PARA AMBOS OS MODOS) ---
        # Procura se existe alguma coluna de e-mail para aplicar o filtro
        coluna_email_encontrada = None
        for col in df.columns:
            if col.lower() in ['email', 'e-mail', 'mail', 'endereço de email']:
                coluna_email_encontrada = col
                break
        
        if coluna_email_encontrada:
            # Aplica o filtro da EB
            emails_norm = df[coluna_email_encontrada].astype(str).str.lower().str.strip()
            dominios_internos = ('@ebtreinamentos.com', '@ebedu.com.br')
            qtd_antes = len(df)
            df = df[~emails_norm.str.endswith(dominios_internos)]
            qtd_depois = len(df)
            removidos = qtd_antes - qtd_depois
            
            if removidos > 0:
                st.toast(f"🧹 Limpeza realizada: {removidos} emails da equipe EB foram removidos.", icon="🗑️")
        
        # Variáveis de trabalho
        df_final = pd.DataFrame()
        coluna_data_nome = ""

        # ==============================================================================
        # MODO 1: PADRÃO EBSKILLS (Regras Rígidas de Perfil e Status)
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
            
            # Menu de seleção
            perfis_sel = st.sidebar.multiselect("Filtrar Perfis:", perfis_permitidos, default=perfis_permitidos)
            df_final = df[df['Perfil'].isin(perfis_sel)].copy()
            
            coluna_data_nome = 'Último login'

       
        # ==============================================================================
        # MODO 2: GENÉRICO (Flexível)
        # ==============================================================================
        else:
            st.info("Modo ativado: **Outras Planilhas**.")
            
            colunas_disponiveis = df.columns.tolist()
            
            # Tentativa de encontrar a coluna de data automaticamente
            termos_comuns = ['data', 'login', 'acesso', 'last', 'criado', 'date']
            index_sugerido = 0
            for i, col in enumerate(colunas_disponiveis):
                if any(termo in col.lower() for termo in termos_comuns):
                    index_sugerido = i
                    break
            
            coluna_data_nome = st.selectbox(
                "Selecione a coluna que contém a DATA:", 
                colunas_disponiveis, 
                index=index_sugerido
            )
            
            # IMPORTANTE: Definimos o df_final aqui para garantir que ele não comece vazio
            df_final = df.copy()

            # Filtro Opcional Extra
            usar_filtro = st.checkbox("Filtrar por outra coluna (Ex: Curso, Status, Produto)")
            if usar_filtro:
                col_filtro = st.selectbox("Coluna para filtrar:", colunas_disponiveis)
                valores_unicos = df[col_filtro].unique()
                valores_escolhidos = st.multiselect("Manter apenas:", valores_unicos, default=valores_unicos)
                df_final = df[df[col_filtro].isin(valores_escolhidos)].copy()

        # ==============================================================================
        # CÁLCULOS E VISUALIZAÇÃO
        # ==============================================================================
        
        if df_final.empty:
            st.warning("Nenhum dado encontrado após os filtros.")
            st.stop()

        if coluna_data_nome not in df_final.columns:
            st.error(f"Erro: A coluna '{coluna_data_nome}' não existe.")
            st.stop()

        hoje = datetime.datetime.now()
        
        # Converte Data
        df_final['data_processada'] = pd.to_datetime(df_final[coluna_data_nome], dayfirst=True, errors='coerce')
        
        # Flags
        df_final['nunca_acessou'] = df_final['data_processada'].isna()
        df_final['dias_atraso'] = (hoje - df_final['data_processada']).dt.days

        # Buckets
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
        ax.set_title("Status de Acesso")
        
        for bar in barras:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, '%d' % int(height), ha='center', va='bottom')
        st.pyplot(fig)

        # Downloads
        st.subheader("📥 Baixar Relatórios")
        def to_csv(d): return d.to_csv(sep=';', index=False, encoding='utf-8-sig').encode('utf-8-sig')

        col_d1, col_d2, col_d3 = st.columns(3)
        col_d1.download_button("Nunca", data=to_csv(df_final[mask_nunca]), file_name="nunca.csv")
        col_d2.download_button("15-30 Dias", data=to_csv(df_final[mask_15_30]), file_name="15_30.csv")
        col_d3.download_button("+60 Dias", data=to_csv(df_final[mask_60_mais]), file_name="mais_60.csv")
        st.download_button("Mês Vigente", data=to_csv(df_final[mask_mes]), file_name="mes_vigente.csv")

    except Exception as e:

        st.error(f"Erro: {e}")
