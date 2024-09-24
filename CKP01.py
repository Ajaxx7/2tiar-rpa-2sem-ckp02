from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import requests
import pandas as pd

# Função para obter todos os estados do Brasil
def get_estados():
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/"
    response = requests.get(url)
    estados = response.json()
    return estados

# Função para obter os municípios de um estado específico
def get_municipios(uf):
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
    response = requests.get(url)
    municipios = response.json()
    return municipios

def scrape_ibge(municipio_nome, uf, driver):
    # Acessando a página principal do IBGE
    url = "https://cidades.ibge.gov.br/"
    driver.get(url)
    
    # Espera explícita para garantir que o menu esteja presente e clicável
    try:
        menu_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "abaMenuLateral"))
        )
        menu_button.click()
    except Exception as e:
        print(f"Erro ao clicar no menu: {e}")
        return
    
    # Espera explícita para garantir que o submenu "Municípios" esteja presente e clicável
    try:
        submenu_municipios = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "menu__municipio"))
        )
        submenu_municipios.click()
    except Exception as e:
        print(f"Erro ao clicar no submenu 'Municípios': {e}")
        return
    
    # Espera explícita para garantir que o campo de busca esteja interativo
    try:
        search_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "busca"))
        )
    except Exception as e:
        print(f"Erro ao localizar o campo de busca: {e}")
        return
    
    # Inserindo o nome do município no campo de busca
    search_input.clear()
    search_input.send_keys(municipio_nome)

    # Clicando no elemento usando JavaScript
    try:
        municipio_link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//li/a[contains(text(), '{municipio_nome}')]"))
        )
        driver.execute_script("arguments[0].click();", municipio_link)  # Simula o clique com JavaScript

        # Troca o foco para a nova guia
        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))  # Espera até que haja 2 guias abertas
        driver.switch_to.window(driver.window_handles[1])  # Muda para a nova guia
    except Exception as e:
        print(f"Dados do município {municipio_nome} foram coletados com sucesso")

def coletar_informacoes_municipio(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Coletando as informações desejadas
    informacoes = {
        "populacao_ultimo_censo": None,
        "populacao_estimada": None,
        "densidade_demografica": None,
    }

    # População no último censo
    populacao_element = soup.find('tr', class_='lista__indicador', tabindex='1')
    if populacao_element:
        valor_element = populacao_element.find('span', class_='unidade').find_previous('span')
        informacoes["populacao_ultimo_censo"] = valor_element.get_text(strip=True) if valor_element else "Informação não disponível"

    # População estimada
    populacao_estimada_element = soup.find('tr', class_='lista__indicador', tabindex='2')
    if populacao_estimada_element:
        valor_element = populacao_estimada_element.find('span', class_='unidade').find_previous('span')
        informacoes["populacao_estimada"] = valor_element.get_text(strip=True) if valor_element else "Informação não disponível"

    # Densidade demográfica
    densidade_element = soup.find('tr', class_='lista__indicador', tabindex='3')
    if densidade_element:
        valor_element = densidade_element.find('span', class_='unidade').find_previous('span')
        informacoes["densidade_demografica"] = valor_element.get_text(strip=True) if valor_element else "Informação não disponível"

    return informacoes

def main():
    # Configurando o WebDriver
    service = Service(executable_path='C:/Users/Gustavo/Documents/FIAP/2TIAR/FRONT_END/CKP1/chromedriver.exe')
    driver = webdriver.Chrome(service=service)

    # DataFrame para armazenar as informações dos municípios
    df_municipios = pd.DataFrame(columns=["municipio", "populacao_ultimo_censo", "populacao_estimada", "densidade_demografica"])

    try:
        # Obtendo os estados
        estados = get_estados()
        print("Escolha um estado pelo ID:")

        # Exibindo os estados disponíveis
        for estado in estados:
            print(f"ID: {estado['id']} - Nome: {estado['nome']}")

        estado_id = input("Digite o ID do estado escolhido: ")

        # Validação da escolha do estado
        if not estado_id.isdigit() or int(estado_id) not in [estado['id'] for estado in estados]:
            print("ID inválido. Por favor, escolha um ID de estado válido.")
            return
        
        # Filtrando o UF do estado escolhido
        estado_escolhido = next(estado for estado in estados if estado['id'] == int(estado_id))
        uf = estado_escolhido['sigla']

        # Obtendo os municípios do estado escolhido
        municipios = get_municipios(uf)

        # Loop por todos os municípios
        for municipio in municipios:
            municipio_nome = municipio['nome']
            print(f"Coletando informações do município: {municipio_nome}...")

            # Realizando o scraping para cada município
            scrape_ibge(municipio_nome, uf, driver)

            # Coletando as informações do município
            informacoes_municipio = coletar_informacoes_municipio(driver)

            # Criar um DataFrame temporário com as informações coletadas
            df_temp = pd.DataFrame([{"municipio": municipio_nome, **informacoes_municipio}])

            # Concatenar o DataFrame temporário ao DataFrame principal
            df_municipios = pd.concat([df_municipios, df_temp], ignore_index=True)

            # Fechando a guia do município e voltando para a guia anterior
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])  # Volta para a guia principal
            else:
                print("--------------------------------")

    finally:
        driver.quit()

    # Exportando o DataFrame para um arquivo CSV
    df_municipios.to_csv("informacoes_municipios.csv", index=False, encoding='utf-8')
    print("Informações dos municípios exportadas para 'informacoes_municipios.csv'.")

    # Exibindo o DataFrame resultante
    print(df_municipios)

if __name__ == "__main__":
    main()
