import streamlit as st
import pandas as pd
from datetime import timedelta

# Configuração da página
st.set_page_config(page_title="Analista Go In Fibra", layout="wide", page_icon="📡")

def formatar_tempo(segundos):
    dias = segundos // 86400
    horas = (segundos % 86400) // 3600
    
    if dias >= 3:
        return f"{int(dias)} dias (Abatimento sugerido: {int(dias)} diárias)"
    elif dias > 0:
        return f"{int(dias)} dia(s) e {int(horas)}h"
    else:
        return f"{int(horas)}h"

st.title("📡 Analista de Downtime - Go In Fibra")
st.markdown("### Cálculo automático de gaps de conexão (Regra: > 10 min)")

uploaded_file = st.file_uploader("Arraste o relatório XLSX ou CSV aqui", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # Carregamento dos dados
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Padronização de colunas para aceitar os dois formatos do IXC
        map_cols = {
            'INICIAL': 'INICIAL', 'Conexão Inicial': 'INICIAL',
            'FINAL': 'FINAL', 'Conexão Final': 'FINAL'
        }
        df = df.rename(columns=map_cols)

        # Converte INICIAL para datetime (obrigatório)
        df['INICIAL'] = pd.to_datetime(df['INICIAL'], dayfirst=True, errors='coerce')
        
        # Ordena por início de conexão
        df = df.sort_values(by='INICIAL').reset_index(drop=True)

        gaps = []
        segundos_totais = 0

        # Lógica de processamento
        for i in range(len(df) - 1):
            inicio_atual = df.loc[i, 'INICIAL']
            fim_atual = df.loc[i, 'FINAL']
            inicio_prox = df.loc[i+1, 'INICIAL']

            # TRATAMENTO DE CÉLULA VAZIA [Rigor Técnico: Identificado]
            # Se a coluna FINAL estiver vazia mas não for a última linha do arquivo,
            # consideramos que a queda ocorreu no momento do login (ou login sujo).
            if pd.isna(fim_atual) or str(fim_atual).strip() == "":
                momento_queda = inicio_atual
                tipo_evento = "Sessão Sem Log de Fim (Queda)"
            else:
                momento_queda = pd.to_datetime(fim_atual, dayfirst=True, errors='coerce')
                tipo_evento = "Queda de Conexão"

            if pd.notna(momento_queda) and pd.notna(inicio_prox):
                diff = (inicio_prox - momento_queda).total_seconds()
                
                # Regra dos 10 minutos
                if diff > 600:
                    segundos_totais += diff
                    gaps.append({
                        "Evento": tipo_evento,
                        "Caiu em": momento_queda,
                        "Voltou em": inicio_prox,
                        "Duração": formatar_tempo(diff),
                        "Segundos": diff
                    })

        # --- Dashboard de Resultados ---
        st.divider()
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.metric("Tempo Total Offline", formatar_tempo(segundos_totais))
        with c2:
            st.metric("Total de Gaps (>10min)", len(gaps))
        with c3:
            cliente = df['CLIENTE'].iloc[0] if 'CLIENTE' in df.columns else "Não Identificado"
            st.metric("Cliente", str(cliente))

        if gaps:
            st.subheader("📋 Detalhamento das Ocorrências")
            df_display = pd.DataFrame(gaps).drop(columns=['Segundos'])
            st.table(df_display)
            
            # Botão para exportar
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button("Baixar Relatório (CSV)", csv, "relatorio_quedas.csv", "text/csv")
        else:
            st.success("✅ Nenhuma instabilidade superior a 10 minutos detectada.")

    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
        st.info("Verifica se as colunas INICIAL e FINAL estão presentes no ficheiro.")
