import os
import io
from datetime import timedelta

import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="Analista Go In Fibra",
    layout="wide",
    page_icon="📡"
)

def formatar_tempo(segundos):
    segundos = int(segundos)
    dias = segundos // 86400
    horas = (segundos % 86400) // 3600

    if dias >= 3:
        return f"{dias} dias (Abatimento sugerido: {dias} diárias)"
    elif dias > 0:
        return f"{dias} dia(s) e {horas}h"
    else:
        return f"{horas}h"

st.title("📡 Analista de Downtime - Go In Fibra")
st.markdown("### Cálculo automático de gaps de conexão (Regra: > 10 min)")

uploaded_file = st.file_uploader(
    "Arraste o relatório gerado no IXC aqui (CSV/XLS/XLSX)",
    type=['csv', 'xls', 'xlsx']
)

if uploaded_file:
    try:
        # --- Leitura robusta (IXC manda CSV com extensão .xls) ---
        content = uploaded_file.read()
        uploaded_file.seek(0)

        df = None
        erro_csv = None

        # 1) Tenta ler como CSV (mesmo se for .xls)
        try:
            df = pd.read_csv(
                io.BytesIO(content),
                sep=';',           # se no seu IXC for vírgula, troca aqui
                engine='python'
            )
        except Exception as e:
            erro_csv = e

        # 2) Se falhar como CSV, tenta como Excel real
        if df is None:
            try:
                df = pd.read_excel(uploaded_file)
            except Exception as e:
                st.error("Não foi possível ler o arquivo nem como CSV nem como Excel.")
                st.text(f"Erro CSV: {erro_csv}")
                st.text(f"Erro Excel: {e}")
                st.stop()

        # --- Padronização de colunas para aceitar os dois formatos do IXC ---
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

        # --- Lógica de processamento ---
        for i in range(len(df) - 1):
            inicio_atual = df.loc[i, 'INICIAL']
            fim_atual = df.loc[i, 'FINAL'] if 'FINAL' in df.columns else None
            inicio_prox = df.loc[i + 1, 'INICIAL']

            # TRATAMENTO DE CÉLULA VAZIA
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
            cliente = df['CLIENTE'].iloc[0] if 'CLIENTE' in df.columns else "Não identificado"
            st.metric("Cliente", str(cliente))

        # Métrica opcional de abatimento total
        dias_total = segundos_totais // 86400
        st.metric("Abatimento sugerido (diárias)", int(dias_total))

        if gaps:
            st.subheader("📋 Detalhamento das ocorrências")
            df_display = pd.DataFrame(gaps).drop(columns=['Segundos'])
            st.dataframe(df_display, use_container_width=True)

            # Botão para exportar
            csv_out = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Baixar relatório (CSV)",
                csv_out,
                "relatorio_quedas.csv",
                "text/csv"
            )
        else:
            st.success("✅ Nenhuma instabilidade superior a 10 minutos detectada.")

    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
        st.info("Verifica se o relatório exportado do IXC contém as colunas INICIAL e FINAL.")
