from datetime import datetime
import time
import pytz
import requests
from bs4 import BeautifulSoup
import json
import os
import re
from curl_cffi import requests as curl_requests


def buscar_dados_acao_investidor10(ticker):
    """
    Método melhorado para extrair dados do Investidor10
    """
    url = f"https://investidor10.com.br/acoes/{ticker.lower()}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        dados = {
            "ticker": ticker,
            "cotacao": "N/A",
            "pl": "N/A",
            "pvp": "N/A", 
            "dy": "N/A",
            "psr": "N/A",
            "payout": "N/A",
            "margem_liquida": "N/A",
            "margem_bruta": "N/A",
            "ev_ebitda": "N/A",
            "ev_ebit": "N/A",
            "vpa": "N/A",
            "roe": "N/A",
            "divida_liquida_patrimonio": "N/A",
            "divida_liquida_ebitda": "N/A",
            "liquidez_corrente": "N/A",
            "cagr_receitas_5anos": "N/A",
            "cagr_lucros_5anos": "N/A",
            "variacao_12m": "N/A"
        }

        # Extrai cotação
        cotacao_div = soup.find("div", class_="_card cotacao")
        if cotacao_div:
            value_span = cotacao_div.find("span", class_="value")
            if value_span:
                dados["cotacao"] = value_span.get_text(strip=True)

        # Extrai variação 12 meses - está em um card específico
        # Busca pelo card que contém "VARIAÇÃO (12M)" no header
        variacao_cards = soup.find_all("div", class_="_card")
        for card in variacao_cards:
            header = card.find("div", class_="_card-header")
            if header:
                header_text = header.get_text(strip=True).upper()
                if "VARIAÇÃO" in header_text and "12M" in header_text:
                    # Encontrou o card da variação 12M, agora busca o valor no body
                    card_body = card.find("div", class_="_card-body")
                    if card_body:
                        span = card_body.find("span")
                        if span:
                            dados["variacao_12m"] = span.get_text(strip=True)
                            break

        # Extrai indicadores da seção de indicadores fundamentalistas
        indicators_section = soup.find("div", id="indicators")
        if indicators_section:
            cells = indicators_section.find_all("div", class_="cell")
            
            for cell in cells:
                # Procura pelo texto do indicador
                cell_text = cell.get_text().upper()
                
                # Extrai o valor (primeiro span dentro da div com classe "value")
                value_div = cell.find("div", class_="value")
                if value_div:
                    value_span = value_div.find("span")
                    if value_span:
                        valor = value_span.get_text(strip=True)
                        
                        # Mapeia os indicadores baseado no texto da célula
                        if "P/L" in cell_text and "P/LP" not in cell_text:
                            dados["pl"] = valor
                        elif "P/VP" in cell_text:
                            dados["pvp"] = valor
                        elif "DIVIDEND YIELD" in cell_text:
                            dados["dy"] = valor
                        elif "P/RECEITA" in cell_text:
                            dados["psr"] = valor
                        elif "PAYOUT" in cell_text:
                            dados["payout"] = valor
                        elif "MARGEM LÍQUIDA" in cell_text:
                            dados["margem_liquida"] = valor
                        elif "MARGEM BRUTA" in cell_text:
                            dados["margem_bruta"] = valor
                        elif "EV/EBITDA" in cell_text:
                            dados["ev_ebitda"] = valor
                        elif "EV/EBIT" in cell_text:
                            dados["ev_ebit"] = valor
                        elif "VPA" in cell_text:
                            dados["vpa"] = valor
                        elif "ROE" in cell_text:
                            dados["roe"] = valor
                        # Melhorada a detecção para dívida líquida / patrimônio
                        elif "DÍVIDA LÍQUIDA / PATRIMÔNIO" in cell_text or "DIVIDA LIQUIDA / PATRIMONIO" in cell_text:
                            dados["divida_liquida_patrimonio"] = valor
                        # Melhorada a detecção para dívida líquida / EBITDA
                        elif "DÍVIDA LÍQUIDA / EBITDA" in cell_text or "DIVIDA LIQUIDA / EBITDA" in cell_text or "DL/EBITDA" in cell_text:
                            dados["divida_liquida_ebitda"] = valor
                        elif "LIQUIDEZ CORRENTE" in cell_text:
                            dados["liquidez_corrente"] = valor
                        elif "CAGR RECEITAS 5 ANOS" in cell_text or "CAGR RECEITA" in cell_text:
                            dados["cagr_receitas_5anos"] = valor
                        elif "CAGR LUCROS 5 ANOS" in cell_text or "CAGR LUCRO" in cell_text:
                            dados["cagr_lucros_5anos"] = valor

        return dados

    except Exception as e:
        return {"ticker": ticker, "erro": str(e)}

def buscar_dados_acao_fundamentus(ticker):
    """
    Versão com TLS spoof via curl_cffi para evitar bloqueio (403) pelo site Fundamentus
    """
    url = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker.upper()}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Referer": "https://www.fundamentus.com.br/",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    }

    max_tentativas = 3
    tentativa = 0

    while tentativa < max_tentativas:
        try:
            # Delay progressivo entre tentativas
            time.sleep(2 * (tentativa + 1))

            response = curl_requests.get(
                url,
                headers=headers,
                impersonate="chrome120",
                timeout=20
            )

            if "captcha" in response.text.lower():
                raise Exception("Bloqueado por CAPTCHA")

            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            ano_atual = datetime.now().year

            dados = {
                "ticker": ticker,
                "oscilacao_ano_atual": "N/A",
                "oscilacao_ano_menos_1": "N/A",
                "oscilacao_ano_menos_2": "N/A", 
                "oscilacao_ano_menos_3": "N/A",
                "oscilacao_ano_menos_4": "N/A",
                "oscilacao_ano_menos_5": "N/A"
            }

            # Exemplo genérico — você pode adaptar de acordo com a lógica original
            # Aqui ele procura oscilações por ano
            tabela = soup.find("table", class_="resultado")
            if tabela:
                linhas = tabela.find_all("tr")
                for linha in linhas:
                    colunas = linha.find_all("td")
                    if len(colunas) >= 2:
                        ano = colunas[0].get_text(strip=True)
                        valor = colunas[1].get_text(strip=True)
                        if ano.isdigit():
                            ano = int(ano)
                            if ano == ano_atual:
                                dados["oscilacao_ano_atual"] = valor
                            elif ano == ano_atual - 1:
                                dados["oscilacao_ano_menos_1"] = valor
                            elif ano == ano_atual - 2:
                                dados["oscilacao_ano_menos_2"] = valor
                            elif ano == ano_atual - 3:
                                dados["oscilacao_ano_menos_3"] = valor
                            elif ano == ano_atual - 4:
                                dados["oscilacao_ano_menos_4"] = valor
                            elif ano == ano_atual - 5:
                                dados["oscilacao_ano_menos_5"] = valor

            return dados

        except Exception as e:
            tentativa += 1
            ultimo_erro = str(e)
            if tentativa == max_tentativas:
                return {
                    "ticker": ticker,
                    "erro": f"Falha após {max_tentativas} tentativas: {ultimo_erro}"
                }


# Lista de ações para consulta
acoes = ["AALR3", "ABCB4", "ABEV3", "AERI3", "AFLT3", "AGRO3", "AGXY3", 
        #  "ALLD3", "ALOS3", "ALPA3", "ALPA4", "ALPK3", "ALUP11", "AMAR3", 
        #  "AMBP3", "AMER3", "AMOB3", "ANIM3", "ARML3", "ASAI3", "ATMP3", "AURE3", 
        #  "AVLL3", "AZUL4", "AZZA3", "B3SA3", "BALM4", "BAZA3", "BBAS3", "BBDC3", 
        #  "BBDC4", "BBSE3", "BEEF3", "BEES3", "BEES4", "BGIP3", "BGIP4", "BHIA3", 
        #  "BIED3", "BLAU3", "BMEB3", "BMEB4", "BMGB4", "BMKS3", "BMOB3", "BOBR4", 
        #  "BPAC11", "BPAC3", "BPAC5", "BPAN4", "BRAP3", "BRAP4", "BRAV3", "BRFS3", 
        #  "BRKM3", "BRKM5", "BRSR3", "BRSR6", "BRST3", "CAMB3", "CAML3", "CASH3", 
        #  "CBAV3", "CCTY3", "CEAB3", "CEBR3", "CEBR6", "CEDO4", "CGAS5", "CGRA3", 
        #  "CGRA4", "CLSC3", "CLSC4", "CMIG3", "CMIG4", "CMIN3", "COCE3", "COCE5", 
        #  "COGN3", "CPFE3", "CPLE3", "CPLE6", "CRPG5", "CSAN3", "CSED3", 
        #  "CSMG3", "CSNA3", "CSUD3", "CURY3", "CVCB3", "CXSE3", "CYRE3", "DASA3", 
        #  "DESK3", "DEXP3", "DEXP4", "DIRR3", "DMVF3", "DOTZ3", "DXCO3", "EALT3", 
        #  "EALT4", "ECOR3", "EGIE3", "ELET3", "ELET5", "ELET6", "EMAE4", "EMBR3", 
        #  "ENEV3", "ENGI11", "ENGI3", "ENGI4", "ENJU3", "EQPA3", "EQTL3", "ESPA3", 
        #  "ETER3", "EUCA3", "EUCA4", "EVEN3", "EZTC3", "FESA3", "FESA4", "FHER3", 
        #  "FIQE3", "FLRY3", "FRAS3", "GFSA3", "GGBR3", "GGBR4", "GGPS3", "GMAT3", 
        #  "GOAU3", "GOAU4", "GRND3", "GUAR3", "HAPV3", "HBOR3", "HBSA3", "HYPE3", 
        #  "IFCM3", "IGTI11", "INTB3", "IRBR3", "ISAE3", "ISAE4", "ITSA3", "ITSA4", 
        #  "ITUB3", "ITUB4", "JALL3", "JHSF3", "JSLG3", "KEPL3", "KLBN11", "KLBN3", 
        #  "KLBN4", "LAND3", "LAVV3", "LEVE3", "LIGT3", "LJQQ3", "LOGG3", "LOGN3", 
        #  "LPSB3", "LREN3", "LVTC3", "LWSA3", "MATD3", "MDIA3", "MDNE3", "MEAL3", 
        #  "MELK3", "MGLU3", "MILS3", "MLAS3", "MNDL3", "MOAR3", "MOTV3", "MOVI3", 
        #  "MRVE3", "MTRE3", "MTSA4", "MULT3", "MYPK3", "NATU3", "NEOE3", "NEXP3",  
        #  "NGRD3", "ODPV3", "OFSA3", "OIBR3", "OIBR4", "ONCO3", "OPCT3", "ORVR3", 
        #  "PCAR3", "PDTC3", "PETR3", "PETR4", "PETZ3", "PFRM3", "PGMN3", "PLAS3", 
        #  "PLPL3", "PMAM3", "PNVL3", "POMO3", "POMO4", "PORT3", "POSI3", "PRIO3", 
        #  "PRNR3", "PSSA3", "PTBL3", "PTNT3", "PTNT4", "QUAL3", "RADL3", "RAIL3", 
        #  "RAIZ4", "RANI3", "RAPT3", "RAPT4", "RDNI3", "RDOR3", "REAG3", "RECV3", 
        #  "RENT3", "ROMI3", "SANB11", "SAPR11", "SAPR3", "SAPR4", "SBFG3", "SBSP3", 
        #  "SCAR3", "SEER3", "SEQL3", "SGPS3", "SHUL4", "SIMH3", "SLCE3", "SMFT3", 
        #  "SMTO3", "SOJA3", "SRNA3", "STBP3", "SUZB3", "SYNE3", "TAEE11", "TAEE3", 
        #  "TAEE4", "TASA3", "TASA4", "TCSA3", "TECN3", "TEND3", "TFCO4", "TGMA3", 
        #  "TIMS3", "TOKY3", "TOTS3", "TRAD3", "TRIS3", "TTEN3", "TUPY3", "TXRX3", 
        #  "UCAS3", "UGPA3", "UNIP3", "UNIP6", "USIM3", "USIM5", "USIM6", "VALE3", 
        #  "VAMO3", "VBBR3", "VITT3", "VIVA3", "VIVT3", "VLID3", "VSTE3", "VTRU3", 
         "VULC3", "VVEO3", "WEGE3", "WEST3", "WHRL3", "WHRL4", "WIZC3", "WLMM4", "YDUQ3"]

print("Iniciando extração de dados...")

# Busca os dados de todas as ações usando ambos os métodos
dados_acoes = []
for acao in acoes:
    print(f"Extraindo dados de {acao}...")
    
    # Dados do Investidor10
    dados_inv10 = buscar_dados_acao_investidor10(acao)
    
    # Dados do Fundamentus
    dados_fund = buscar_dados_acao_fundamentus(acao)
    
    # Combina os dados
    dados_combinados = {**dados_inv10, **dados_fund}
    # Remove duplicata do ticker
    if "ticker" in dados_fund and "ticker" in dados_inv10:
        dados_combinados["ticker"] = dados_inv10["ticker"]
    
    # Força o uso da timezone de São Paulo (que representa o horário de Brasília)
    brasilia_tz = pytz.timezone('America/Sao_Paulo')
    dados_combinados["atualizado_em"] = datetime.now(brasilia_tz).strftime("%Y-%m-%d %H:%M:%S")
    
    dados_acoes.append(dados_combinados)

"""
# Salva na área de trabalho
desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
json_path = os.path.join(desktop_path, 'investbr.json')
"""

json_path = 'dados_acoes.json'

with open(json_path, 'w', encoding='utf-8') as json_file:
    json.dump(dados_acoes, json_file, indent=4, ensure_ascii=False)

print(f"Arquivo salvo em: {json_path}")

# Exibe um resumo dos dados extraídos
print("\n=== RESUMO DOS DADOS EXTRAÍDOS ===")
for dado in dados_acoes:
    if "erro" not in dado:
        print(f"\n{dado['ticker']}:")
        print(f"  Cotação: {dado['cotacao']}")
        print(f"  P/L: {dado['pl']}")
        print(f"  P/VP: {dado['pvp']}")
        print(f"  DY: {dado['dy']}")
        print(f"  PSR: {dado['psr']}")
        print(f"  EV/EBIT: {dado['ev_ebit']}")
        print(f"  VPA: {dado['vpa']}")
        print(f"  ROE: {dado['roe']}")
        print(f"  Dívida Líq./Patrimônio: {dado['divida_liquida_patrimonio']}")
        print(f"  Dívida Líq./EBITDA: {dado['divida_liquida_ebitda']}")
        print(f"  Liquidez Corrente: {dado['liquidez_corrente']}")
        print(f"  CAGR Receitas 5a: {dado['cagr_receitas_5anos']}")
        print(f"  CAGR Lucros 5a: {dado['cagr_lucros_5anos']}")
        print(f"  Variação 12m: {dado['variacao_12m']}")
        print(f"  Oscilação {datetime.now().year}: {dado.get('oscilacao_ano_atual', 'N/A')}")
        print(f"  Oscilação {datetime.now().year-1}: {dado.get('oscilacao_ano_menos_1', 'N/A')}")
        print(f"  Oscilação {datetime.now().year-2}: {dado.get('oscilacao_ano_menos_2', 'N/A')}")
        print(f"  Oscilação {datetime.now().year-3}: {dado.get('oscilacao_ano_menos_3', 'N/A')}")
        print(f"  Oscilação {datetime.now().year-4}: {dado.get('oscilacao_ano_menos_4', 'N/A')}")
        print(f"  Oscilação {datetime.now().year-5}: {dado.get('oscilacao_ano_menos_5', 'N/A')}")
    else:
        print(f"\n{dado['ticker']}: ERRO - {dado['erro']}")