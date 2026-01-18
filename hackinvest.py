import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Radar de Dividendos", layout="wide")

st.title("📊 HackInvest")

@st.cache_data(ttl=3600) # Guarda os dados por 1 hora
def calcular_score_estatistico(t, meta):
    try:
        acao = yf.Ticker(t + ".SA")
        h = acao.history(period="1y")
        if h.empty: return 0
        p_at = h['Close'].iloc[-1]
        m200 = h['Close'].rolling(window=200).mean().iloc[-1]
        inf = acao.info
        div = inf.get('dividendRate') or inf.get('trailingAnnualDividendRate') or 0
        lpa = inf.get('trailingEps', 0) or 0
        vpa = inf.get('bookValue', 0) or 0
        
        pts = 0
        # Bazin (40 pts)
        if (div/meta if div > 0 else 0) > p_at: pts += 40 
        # Graham (40 pts)
        if np.sqrt(22.5 * lpa * vpa) > p_at: pts += 40    
        # Média 200 (20 pts)
        if p_at <= m200: pts += 20                       
        return int(pts)
    except: return 0


# Menu lateral
st.sidebar.header("Configurações")
ticker_input = st.sidebar.text_input("Digite o Ticker (ex: BBAS3):", value="BBAS3").upper()
# Agora iniciando em 12% como você pediu
yield_alvo = st.sidebar.slider("Sua meta de Yield (%)", 1.0, 15.0, 12.0, step=0.1) / 100

periodo = st.sidebar.selectbox(
    "Período do Gráfico",
    options=["1d", "5d", "1mo", "6mo", "ytd", "1y", "5y", "max"],
    index=5,
    format_func=lambda x: {
        "1d": "1 Dia", "5d": "1 Semana", "1mo": "1 Mês", 
        "6mo": "6 Meses", "ytd": "Este Ano (YTD)", 
        "1y": "1 Ano", "5y": "5 Anos", "max": "Máximo"
    }[x]
)

ticker = ticker_input + ".SA" if not ticker_input.endswith(".SA") else ticker_input

try:
    acao = yf.Ticker(ticker)
    hist_media = acao.history(period="2y")
    
    if hist_media.empty:
        st.error("Não encontrei dados. Verifique o ticker.")
    else:
        # --- DADOS BASE ---
        preco_atual = float(hist_media['Close'].iloc[-1])
        mme200 = float(hist_media['Close'].rolling(window=200).mean().iloc[-1])
        
        info = acao.info
        lpa = info.get('trailingEps', 0) or 0
        vpa = info.get('bookValue', 0) or 0
        div_ano = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0

        # --- CÁLCULOS ---
        preco_teto_bazin = div_ano / yield_alvo if div_ano > 0 else 0
        valor_justo_graham = np.sqrt(22.5 * lpa * vpa) if (lpa > 0 and vpa > 0) else 0

        # --- LÓGICA DO SCORE HACKINVEST (0-100) ---
        score = 0
        # Pontos Graham (Max 40)
        if valor_justo_graham > preco_atual:
            score += 40
        elif valor_justo_graham > 0:
            margem_g = (valor_justo_graham / preco_atual)
            score += int(max(0, margem_g * 20))

        # Pontos Bazin (Max 40)
        if preco_teto_bazin > preco_atual:
            score += 40
        elif preco_teto_bazin > 0:
            margem_b = (preco_teto_bazin / preco_atual)
            score += int(max(0, margem_b * 20))

        # Pontos Média 200 (Max 20)
        distancia_media = (preco_atual / mme200)
        if distancia_media <= 1.0: 
            score += 20
        elif distancia_media <= 1.10: 
            score += 10
        
        score = min(100, score)

        # --- EXIBIÇÃO DO SCORE ---
        st.divider()
        c_score, c_desc = st.columns([1, 2])
        with c_score:
            st.subheader("Nota HackInvest")
            if score >= 80: st.success(f"🚀 {score}/100 - EXCELENTE")
            elif score >= 50: st.warning(f"⚖️ {score}/100 - NEUTRA")
            else: st.error(f"⚠️ {score}/100 - EVITAR")
        with c_desc:
            st.write(f"Análise baseada em Graham (Valor Justo), Bazin ({yield_alvo*100:.0f}% Yield) e Média de 200 dias.")

        st.divider()

        # --- MÉTRICAS ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Preço Atual", f"R$ {preco_atual:.2f}")
        col2.metric("Média 200 dias", f"R$ {mme200:.2f}", f"{(preco_atual/mme200 - 1)*100:.2f}%")
        col3.metric("Dividendos (12m)", f"R$ {div_ano:.2f}")

        st.divider()

        # --- ESTRATÉGIAS ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("💡 Estratégia Bazin")
            st.code(f"Preço Teto: R$ {preco_teto_bazin:.2f}")
            if preco_atual <= preco_teto_bazin:
                st.success("✅ DENTRO DO PREÇO TETO")
            else:
                st.warning("⚠️ ACIMA DO PREÇO TETO")

        with c2:
            st.subheader("🛡️ Estratégia Graham")
            st.code(f"Valor Justo: R$ {valor_justo_graham:.2f}")
            if preco_atual <= valor_justo_graham:
                st.success("✅ COM MARGEM DE SEGURANÇA")
            else:
                st.error("❌ CARA POR ESTE CRITÉRIO")

        # --- GRÁFICO ARREDONDADO ---
        st.subheader(f"Histórico {ticker_input} - {periodo}")
        hist_grafico = acao.history(period=periodo)
        dados_finais = hist_grafico[['Close']].copy()
        dados_finais['Close'] = dados_finais['Close'].round(2)
        st.line_chart(dados_finais)

except Exception as e:

    st.error(f"Erro técnico: {e}")
