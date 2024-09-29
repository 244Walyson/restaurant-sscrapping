import csv
import time
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

chrome_options = Options()
service = Service("/usr/local/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get("https://restaurantguru.com.br/Belo-Horizonte#restaurant-list")

def scroll_to_load_more(max_scrolls=3):
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Aguarde o carregamento
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:  # Checa se chegou ao final da página
            break
        last_height = new_height
        scroll_count += 1

csv_filename = "etc/restaurantes(1).csv"

try:
    # Realiza o scroll para carregar mais restaurantes
    scroll_to_load_more(max_scrolls=50)

    # Espera pelo primeiro restaurante para garantir que a página está carregada
    WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.restaurant_container"))
    )

    # Abre o arquivo CSV
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Escreve o cabeçalho (nomes das colunas)
        writer.writerow(["Name", "Link", "Price_range"])

        # Captura todos os elementos de restaurantes na página após o scroll
        all_restaurants = driver.find_elements(By.CSS_SELECTOR, "div.restaurant_row")

        print(f"Total de restaurantes carregados: {len(all_restaurants)}")

        for restaurant in all_restaurants:
            try:
                name = restaurant.find_element(By.CSS_SELECTOR, "h3.item__title").text
            except NoSuchElementException:
                name = ""

            try:
                link = restaurant.find_element(By.CSS_SELECTOR, "a.title_url").get_attribute("href")
            except NoSuchElementException:
                link = ""

            try:
                price_range = restaurant.find_element(By.CSS_SELECTOR, "span.cost").get_attribute("title")
            except NoSuchElementException:
                price_range = ""

            # Escreve os dados no CSV
            writer.writerow([name, link, price_range])

except TimeoutException:
    print("O tempo de espera pelo elemento expirou.")
except NoSuchElementException as e:
    print(f"Um ou mais elementos não foram encontrados: {e}")

# Encerra o driver
driver.quit()
