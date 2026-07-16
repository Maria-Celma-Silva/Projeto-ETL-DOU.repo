# 🚀 Guia de Melhorias do Pipeline ETL DOU

Este documento contém todas as melhorias propostas para seu projeto, organizadas por prioridade.

## 📋 Resumo das Melhorias

### ✨ Estrutura Modular
- Refatorar `main.py` em módulos separados na pasta `src/`
- Cada módulo responsável por uma etapa do pipeline (E, T, L)

### 🔍 Logging Estruturado
- Logs com timestamps e níveis (DEBUG, INFO, WARNING, ERROR)
- Saída para console E arquivo (`logs/etl_pipeline.log`)
- Facilita debug e rastreamento de problemas

### 🔄 Retry Automático
- Biblioteca `tenacity` para retry com espera exponencial
- Até 3 tentativas antes de falhar
- Útil para conexões instáveis com o servidor do DOU

### 💾 Backup Automático
- Backup do banco antes de cada atualização
- Recuperação rápida em caso de erro
- Histórico completo de versões

### ⚙️ Configuração Centralizada
- Arquivo `.env.example` com todas as variáveis
- Configurações via variáveis de ambiente
- Sem hardcoding de URLs ou credenciais

### ✅ Validação de Dados
- Validação em cada etapa do pipeline
- Remover valores NULL antes de salvar
- Garantir integridade dos dados

### 📦 GitHub Actions Melhorado
- Notificações de falha via Issue automática
- Upload de artefatos (logs e planilhas)
- Status visual do pipeline

---

## 🛠️ Como Implementar

### 1️⃣ Passo 1: Instalar Novas Dependências

```bash
pip install tenacity python-dotenv
```

Atualizar `requirements.txt`:
```
pandas==2.1.3
selenium==4.15.2
webdriver-manager==4.0.1
openpyxl==3.11.0
tenacity==8.2.3
python-dotenv==1.0.0
```

### 2️⃣ Passo 2: Criar Estrutura de Pastas

```bash
mkdir -p src logs backups
touch src/__init__.py
```

### 3️⃣ Passo 3: Criar Arquivos na Pasta `src/`

#### `src/config.py` - Configurações Centralizadas
```python
"""
Configurações centralizadas da aplicação
"""

import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# ==========================================
# CONFIGURAÇÕES GERAIS
# ==========================================
DOU_URL = os.getenv(
    'DOU_URL',
    'https://www.in.gov.br/consulta/-/buscar/dou?q=INSS&s=todos&exactDate=personalizado&sortType=0'
)

DB_PATH = os.getenv('DB_PATH', 'monitoramento_dou.db')
BACKUP_DIR = os.getenv('BACKUP_DIR', 'backups')
LOG_DIR = os.getenv('LOG_DIR', 'logs')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# ==========================================
# REGRAS DE NEGÓCIO
# ==========================================
ORGAOS_ALVO = [
    "casa civil",
    "ministério da previdência social",
    "instituto nacional do seguro social",
    "inss"
]

PALAVRAS_CHAVE = [
    "nomear", "exonerar", "dispensa", "designa",
    "dispensa gsiste", "designa gsiste"
]

# ==========================================
# CONFIGURAÇÕES SELENIUM
# ==========================================
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'
BROWSER_TIMEOUT = int(os.getenv('BROWSER_TIMEOUT', '15'))

# ==========================================
# CONFIGURAÇÕES DE NOTIFICAÇÃO
# ==========================================
ENABLE_NOTIFICATIONS = os.getenv('ENABLE_NOTIFICATIONS', 'true').lower() == 'true'

# Garante que os diretórios existem
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
```

#### `src/logger.py` - Sistema de Logging
```python
"""
Sistema de logging estruturado para o pipeline ETL
"""

import logging
import os
from src.config import LOG_DIR, LOG_LEVEL

def setup_logger(name: str) -> logging.Logger:
    """
    Configura logger estruturado com handlers para arquivo e console
    
    Args:
        name: Nome do logger (geralmente __name__)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Formato do log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo
    log_file = os.path.join(LOG_DIR, 'etl_pipeline.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
```

#### `src/extracao.py` - Etapa de Extração com Retry
```python
"""
Módulo de Extração (E) do Pipeline ETL
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import DOU_URL, HEADLESS_MODE, BROWSER_TIMEOUT
from src.logger import setup_logger

logger = setup_logger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def extrair_dados_selenium() -> list:
    """
    Extrai dados do DOU usando Selenium com retry automático
    """
    logger.info("🌐 Iniciando extração de dados do DOU...")
    
    try:
        chrome_options = Options()
        
        if HEADLESS_MODE:
            chrome_options.add_argument("--headless")
            logger.debug("Modo headless ativado")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        logger.info(f"🔍 Acessando: {DOU_URL}")
        driver.get(DOU_URL)
        
        logger.debug(f"Aguardando até {BROWSER_TIMEOUT}s para carregamento...")
        WebDriverWait(driver, BROWSER_TIMEOUT).until(
            EC.presence_of_element_located((By.CLASS_NAME, "resultado-busca-item"))
        )
        
        resultados = driver.find_elements(By.CLASS_NAME, "resultado-busca-item")
        textos_extraidos = [item.text for item in resultados]
        
        logger.info(f"✅ Sucesso! {len(textos_extraidos)} publicações extraídas")
        return textos_extraidos
        
    except Exception as e:
        logger.error(f"❌ Erro durante extração: {str(e)}", exc_info=True)
        raise
    finally:
        try:
            driver.quit()
            logger.debug("Browser encerrado")
        except:
            pass


def validar_texto_extraido(texto: str) -> bool:
    """Valida se o texto extraído é válido"""
    if not texto or not isinstance(texto, str):
        return False
    
    if len(texto.strip()) < 10:
        return False
    
    return True
```

#### `src/transformacao.py` - Etapa de Transformação
```python
"""
Módulo de Transformação (T) do Pipeline ETL
"""

import pandas as pd
from datetime import datetime

from src.config import ORGAOS_ALVO, PALAVRAS_CHAVE
from src.logger import setup_logger

logger = setup_logger(__name__)


def sanitizar_texto(texto: str, max_length: int = 5000) -> str:
    """Sanitiza texto removendo caracteres perigosos"""
    if not isinstance(texto, str):
        return ""
    
    texto_limpo = texto.strip()[:max_length]
    return texto_limpo


def aplicar_filtros_estrategicos(dados_brutos: list) -> pd.DataFrame:
    """Aplica regras de negócio para filtrar dados relevantes"""
    logger.info("🔍 Aplicando filtros de negócio...")
    dados_processados = []
    textos_rejeitados = 0
    
    try:
        for texto in dados_brutos:
            texto_lower = texto.lower()
            
            pertence_ao_orgao = any(orgao in texto_lower for orgao in ORGAOS_ALVO)
            contem_acao = any(acao in texto_lower for acao in PALAVRAS_CHAVE)
            
            if pertence_ao_orgao and contem_acao:
                acao_encontrada = next(
                    (acao for acao in PALAVRAS_CHAVE if acao in texto_lower),
                    "Ação Desconhecida"
                )
                
                texto_sanitizado = sanitizar_texto(texto)
                
                dados_processados.append({
                    "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                    "orgao_provavel": "Previdência/INSS/Casa Civil",
                    "tipo_acao": acao_encontrada.title(),
                    "texto_completo": texto_sanitizado
                })
            else:
                textos_rejeitados += 1
        
        df_resultado = pd.DataFrame(dados_processados)
        
        logger.info(f"✅ Filtros aplicados: {len(dados_processados)} registros mantidos, "
                   f"{textos_rejeitados} rejeitados")
        
        return df_resultado
        
    except Exception as e:
        logger.error(f"❌ Erro durante transformação: {str(e)}", exc_info=True)
        raise


def validar_dataframe(df: pd.DataFrame) -> bool:
    """Valida integridade do DataFrame"""
    if df.empty:
        logger.warning("⚠️ DataFrame vazio após filtragem")
        return False
    
    required_cols = ['data_coleta', 'orgao_provavel', 'tipo_acao', 'texto_completo']
    
    if not all(col in df.columns for col in required_cols):
        missing = set(required_cols) - set(df.columns)
        logger.error(f"❌ Colunas faltantes: {missing}")
        return False
    
    if df.isnull().any().any():
        logger.warning("⚠️ DataFrame contém valores NULL")
        df_cleaned = df.dropna()
        logger.info(f"   Linhas removidas: {len(df) - len(df_cleaned)}")
        return len(df_cleaned) > 0
    
    logger.debug(f"✅ DataFrame validado: {len(df)} linhas, {len(df.columns)} colunas")
    return True
```

#### `src/carregamento.py` - Etapa de Carregamento
```python
"""
Módulo de Carregamento (L) do Pipeline ETL
"""

import sqlite3
import pandas as pd
import shutil
from datetime import datetime

from src.config import DB_PATH, BACKUP_DIR
from src.logger import setup_logger

logger = setup_logger(__name__)


def fazer_backup() -> None:
    """Cria backup do banco de dados antes de atualizar"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{BACKUP_DIR}/dou_backup_{timestamp}.db"
        
        shutil.copy(DB_PATH, backup_path)
        logger.info(f"💾 Backup criado: {backup_path}")
        
    except FileNotFoundError:
        logger.debug(f"Banco {DB_PATH} não existe ainda (primeira execução)")
    except Exception as e:
        logger.error(f"❌ Erro ao criar backup: {str(e)}", exc_info=True)


def inicializar_banco() -> None:
    """Inicializa o banco de dados SQLite"""
    try:
        logger.info("🗄️  Inicializando banco de dados...")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_coleta TEXT NOT NULL,
                orgao_provavel TEXT NOT NULL,
                tipo_acao TEXT NOT NULL,
                texto_completo TEXT NOT NULL,
                data_insercao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Banco inicializado com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco: {str(e)}", exc_info=True)
        raise


def salvar_no_banco(df_processado: pd.DataFrame) -> bool:
    """Salva dados processados no banco SQLite"""
    if df_processado.empty:
        logger.warning("⚠️ Nenhum registro para salvar (DataFrame vazio)")
        return False
    
    try:
        logger.info(f"💾 Salvando {len(df_processado)} registros no banco...")
        
        fazer_backup()
        
        conn = sqlite3.connect(DB_PATH)
        df_processado.to_sql('movimentacoes', conn, if_exists='append', index=False)
        conn.close()
        
        logger.info(f"✅ {len(df_processado)} registros salvos com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar no banco: {str(e)}", exc_info=True)
        raise


def exportar_para_excel() -> str:
    """Exporta todos os dados do banco para uma planilha Excel"""
    try:
        logger.info("📊 Exportando dados para Excel...")
        
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM movimentacoes", conn)
        conn.close()
        
        if df.empty:
            logger.warning("⚠️ Nenhum dado para exportar")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_excel = f"relatorio_dou_{timestamp}.xlsx"
        
        with pd.ExcelWriter(arquivo_excel, engine='openpyxl') as writer:
            df.to_excel(
                writer,
                index=False,
                sheet_name='Movimentações'
            )
            
            worksheet = writer.sheets['Movimentações']
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        
        logger.info(f"✅ Planilha criada: {arquivo_excel}")
        logger.info(f"   Total de registros: {len(df)}")
        
        return arquivo_excel
        
    except Exception as e:
        logger.error(f"❌ Erro ao exportar para Excel: {str(e)}", exc_info=True)
        raise


def get_estatisticas_banco() -> dict:
    """Retorna estatísticas do banco de dados"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM movimentacoes")
        total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT tipo_acao, COUNT(*) as quantidade
            FROM movimentacoes
            GROUP BY tipo_acao
            ORDER BY quantidade DESC
        """)
        por_acao = dict(cursor.fetchall())
        
        cursor.execute("SELECT MAX(data_coleta) FROM movimentacoes")
        ultima_atualizacao = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_registros": total,
            "por_tipo_acao": por_acao,
            "ultima_atualizacao": ultima_atualizacao
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas: {str(e)}", exc_info=True)
        return {}
```

### 4️⃣ Passo 4: Atualizar `main.py`

```python
"""
Pipeline ETL Principal: Monitoramento do Diário Oficial da União
"""

import sys
from src.logger import setup_logger
from src.extracao import extrair_dados_selenium, validar_texto_extraido
from src.transformacao import aplicar_filtros_estrategicos, validar_dataframe
from src.carregamento import (
    inicializar_banco,
    salvar_no_banco,
    exportar_para_excel,
    get_estatisticas_banco
)

logger = setup_logger(__name__)


def executar_pipeline() -> bool:
    """
    Executa o pipeline ETL completo
    
    Fluxo:
    1. Extração (E): Coleta dados do DOU via Selenium
    2. Transformação (T): Aplica filtros e estrutura dados
    3. Carregamento (L): Salva em banco e exporta Excel
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO PIPELINE ETL - MONITORAMENTO DOU")
        logger.info("=" * 60)
        
        # EXTRAÇÃO
        logger.info("\n📥 ETAPA 1: EXTRAÇÃO")
        logger.info("-" * 60)
        
        textos_reais = extrair_dados_selenium()
        
        if not textos_reais:
            logger.warning("⚠️ Nenhum dado extraído do DOU")
            return False
        
        textos_validos = [t for t in textos_reais if validar_texto_extraido(t)]
        logger.info(f"Textos válidos: {len(textos_validos)}/{len(textos_reais)}")
        
        if not textos_validos:
            logger.warning("⚠️ Nenhum texto válido após validação")
            return False
        
        # TRANSFORMAÇÃO
        logger.info("\n🔄 ETAPA 2: TRANSFORMAÇÃO")
        logger.info("-" * 60)
        
        dados_filtrados = aplicar_filtros_estrategicos(textos_validos)
        
        if not validar_dataframe(dados_filtrados):
            logger.warning("⚠️ DataFrame não passou na validação")
            return False
        
        # CARREGAMENTO
        logger.info("\n📤 ETAPA 3: CARREGAMENTO")
        logger.info("-" * 60)
        
        inicializar_banco()
        salvar_no_banco(dados_filtrados)
        arquivo_excel = exportar_para_excel()
        
        # ESTATÍSTICAS
        logger.info("\n📊 ESTATÍSTICAS DO BANCO")
        logger.info("-" * 60)
        
        stats = get_estatisticas_banco()
        
        if stats:
            logger.info(f"Total de registros: {stats.get('total_registros', 0)}")
            
            if stats.get('por_tipo_acao'):
                logger.info("Distribuição por tipo:")
                for acao, qtd in stats['por_tipo_acao'].items():
                    logger.info(f"  - {acao}: {qtd}")
            
            logger.info(f"Última atualização: {stats.get('ultima_atualizacao', 'N/A')}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ PIPELINE EXECUTADO COM SUCESSO!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error(f"❌ ERRO FATAL NO PIPELINE: {str(e)}")
        logger.error("=" * 60, exc_info=True)
        return False


if __name__ == "__main__":
    try:
        sucesso = executar_pipeline()
        sys.exit(0 if sucesso else 1)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Pipeline interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Erro não capturado: {str(e)}", exc_info=True)
        sys.exit(1)
```

### 5️⃣ Passo 5: Criar Arquivo `.env.example`

```bash
# 🔐 Configurações de Ambiente
# Copie este arquivo para .env e adicione seus valores reais

# URLs
DOU_URL=https://www.in.gov.br/consulta/-/buscar/dou?q=INSS&s=todos&exactDate=personalizado&sortType=0

# Banco de Dados
DB_PATH=monitoramento_dou.db
BACKUP_DIR=backups

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# Selenium
HEADLESS_MODE=true
BROWSER_TIMEOUT=15

# GitHub Actions (opcional)
ENABLE_NOTIFICATIONS=true
```

### 6️⃣ Passo 6: Atualizar `.gitignore`

```bash
# Ambiente Python
.env
.venv/
env/
__pycache__/
*.py[cod]
*$py.class
*.so

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs e Backups
logs/
backups/
*.log

# Banco de Dados
*.db

# Excel exportado
relatorio_dou_*.xlsx

# OS
.DS_Store
Thumbs.db
```

### 7️⃣ Passo 7: Atualizar GitHub Actions Workflow

Substitua o conteúdo de `.github/workflows/robo_dou.yml` com:

```yaml
name: Robô Diário Oficial (ETL)

on:
  schedule:
    - cron: '0 10 * * 1-5'  # Todos os dias úteis às 10h
  workflow_dispatch:

jobs:
  executar_etl:
    runs-on: ubuntu-latest
    
    steps:
      - name: 📥 Checkout do repositório
        uses: actions/checkout@v4

      - name: 🐍 Configurar Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'

      - name: 📦 Instalar dependências
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: 🚀 Executar Pipeline ETL
        id: etl_execution
        run: |
          python main.py
          echo "ETL_STATUS=success" >> $GITHUB_OUTPUT
        continue-on-error: true

      - name: 📊 Fazer upload de relatórios e logs
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: etl-reports-${{ github.run_id }}
          path: |
            logs/
            relatorio_dou_*.xlsx
          retention-days: 30

      - name: 💾 Salvar atualizações no repositório
        if: steps.etl_execution.outputs.ETL_STATUS == 'success'
        uses: EndBug/add-and-commit@v9
        with:
          author_name: 'Robô DOU 🤖'
          author_email: 'action@github.com'
          message: 'chore: Atualização automática - Novos registros do DOU'
          add: |
            *.db
            *.xlsx
            logs/
          push: true

      - name: ✅ Pipeline executado com sucesso
        if: steps.etl_execution.outputs.ETL_STATUS == 'success'
        run: echo "🎉 Pipeline ETL concluído com sucesso!"

      - name: ❌ Notificar falha
        if: steps.etl_execution.outputs.ETL_STATUS != 'success'
        run: |
          echo "❌ Pipeline ETL falhou!"
          exit 1
```

---

## 🧪 Testar Localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Copiar arquivo de configuração
cp .env.example .env

# Executar pipeline
python main.py

# Ver logs
tail -f logs/etl_pipeline.log
```

---

## 📊 Benefícios

| Melhoria | Benefício |
|----------|-----------|
| **Modularização** | Código mais organizado e testável |
| **Logging** | Rastreamento completo de erros |
| **Retry Automático** | Maior resiliência a falhas temporárias |
| **Backup Automático** | Proteção contra perda de dados |
| **Validação de Dados** | Garante integridade dos registros |
| **Configuração Centralizada** | Fácil manutenção e ajustes |
| **Notificações** | Alertas imediatos de problemas |

---

## 📝 Próximos Passos

1. ✅ Implementar as mudanças acima
2. ✅ Testar localmente
3. ✅ Fazer commit na branch `feature/refactor-etl-architecture`
4. ✅ Criar Pull Request
5. ✅ Revisar e fazer merge para `main`

---

**Criado em:** 2026-07-16
**Status:** ✅ Pronto para implementação
