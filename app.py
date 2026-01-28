import streamlit as st
import pandas as pd
from datetime import timedelta

st.set_page_config(page_title="Analista Go In Fibra", layout="wide")

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
st.write("Cálculo automático de dias para desconto (Regra: >10min de gap).")

uploaded_file = st.file_uploader("Arraste o relatório XLSX ou CSV", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)

        # Padronização de colunas conforme os arquivos enviados 
        map_cols = {'INICIAL': 'INICIAL', 'Conexão Inicial': 'INICIAL', 'FINAL': 'FINAL', 'Conexão Final': 'FINAL'}
        df = df.rename(columns=map_cols)

        df['INICIAL'] = pd.to_datetime(df['INICIAL'], dayfirst=True, errors='coerce')
        df['FINAL'] = pd.to_datetime(df['FINAL'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['INICIAL', 'FINAL']).sort_values(by='INICIAL')

        gaps = []
        segundos_totais = 0

        for i in range(len(df) - 1):
            fim = df.iloc[i]['FINAL']
            inicio = df.iloc[i+1]['INICIAL']
            diff = (inicio - fim).total_seconds()
            
            if diff > 600: # 10 minutos
                segundos_totais += diff
                gaps.append({
                    "Caiu em": fim,
                    "Voltou em": inicio,
                    "Duração": formatar_tempo(diff),
                    "Segundos": diff
                })

        # --- Dashboard ---
        st.divider()
        c1, c2 = st.columns(2)
        
        with c1:
            st.metric("Tempo Total Offline", formatar_tempo(segundos_totais))
        with c2:
            st.metric("Quedas Identificadas", len(gaps))

        if gaps:
            st.subheader("📋 Relatório Detalhado")
            st.table(pd.DataFrame(gaps).drop(columns=['Segundos']))
            
            # Cálculo de exemplo para o Cleiton Sofiatti 
            st.info("💡 **Dica Sistêmica:** Se o total passar de 3 dias, o script já sugere o abatimento direto em diárias.")
        else:
            st.success("✅ Cliente estável.")

    except Exception as e:
        st.error(f"Erro: {e}")