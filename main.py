import sqlite3
import pandas as pd
from datetime import datetime
import time

# Bibliotecas do Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# REGRAS DE NEGÓCIO (Seus Filtros)
# ==========================================
ORGAOS_ALVO = [
    "casa civil", 
    "Ministério da Previdência Social", 
    "Instituto Nacional do Seguro Social", 
    "INSS"
]

PALAVRAS_CHAVE = [
    "nomear", "exonerar", "dispensa", "designa", 
    "dispensa gsiste", "designa gsiste"
]

# ==========================================
# INICIALIZAÇÃO DO BANCO
# ==========================================
def inicializar_banco():
    conn = sqlite3.connect("monitoramento_dou.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            data_coleta TEXT,
            orgao_provavel TEXT,
            tipo_acao TEXT,
            texto_completo TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ==========================================
# 1. EXTRAÇÃO AVANÇADA (SELENIUM)
# ==========================================
def extrair_dados_selenium():
    print("Iniciando o Navegador Fantasma (Selenium)...")
    
    # Configurações para o navegador rodar em segundo plano (invisível)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Instala e inicia o ChromeDriver automaticamente
    servico = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servico, options=chrome_options)
    
    textos_extraidos = []
    
    try:
        url = "https://www.in.gov.br/consulta/-/buscar/dou?q=INSS&s=todos&exactDate=personalizado&sortType=0"
        print("Acessando o portal do Diário Oficial da União...")
        driver.get(url)
        
        # O robô espera até 15 segundos para o JavaScript do site carregar os resultados
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "resultado-busca-item"))
        )
        
        # Coleta todas as caixas de texto carregadas
        resultados = driver.find_elements(By.CLASS_NAME, "resultado-busca-item")
        
        for item in resultados:
            textos_extraidos.append(item.text)
            
        print(f"Sucesso! {len(textos_extraidos)} publicações reais encontradas na página de busca.")
        
    except Exception as e:
        print(f"Ocorreu um erro ou a página demorou muito para carregar: {e}")
    finally:
        driver.quit() # Fecha o navegador fantasma
        
    return textos_extraidos

# ==========================================
# 2. TRANSFORMAÇÃO
# ==========================================
def aplicar_filtros_estrategicos(dados_brutos):
    print("Aplicando regras de filtragem...")
    dados_processados = []
    
    for texto in dados_brutos:
        texto_lower = texto.lower()
        pertence_ao_orgao = any(orgao in texto_lower for orgao in ORGAOS_ALVO)
        contem_acao = any(acao in texto_lower for acao in PALAVRAS_CHAVE)
        
        if pertence_ao_orgao and contem_acao:
            acao_encontrada = next(acao for acao in PALAVRAS_CHAVE if acao in texto_lower)
            dados_processados.append({
                "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                "orgao_provavel": "Previdencia/INSS/Casa Civil",
                "tipo_acao": acao_encontrada.title(),
                "texto_completo": texto
            })
            
    return pd.DataFrame(dados_processados)

# ==========================================
# 3. CARREGAMENTO
# ==========================================
def salvar_no_banco(df_processado):
    if df_processado.empty:
        print("Nenhuma movimentação relevante com os filtros informados encontrada hoje.")
        return

    conn = sqlite3.connect("monitoramento_dou.db")
    df_processado.to_sql('movimentacoes', conn, if_exists='append', index=False)
    conn.close()
    print(f"Banco atualizado! {len(df_processado)} registros oficiais gravados.")

# ==========================================
# ORQUESTRAÇÃO
# ==========================================
if __name__ == "__main__":
    inicializar_banco()
    textos_reais = extrair_dados_selenium()
    
    if textos_reais:
        dados_filtrados = aplicar_filtros_estrategicos(textos_reais)
        salvar_no_banco(dados_filtrados)
