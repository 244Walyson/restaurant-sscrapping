import ast
import csv
import json
import os
import re
import time
from itertools import islice

import fake_useragent
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from database import insert_restaurant, insert_error_log, insert_index, fetch_restaurant_data

user_agent = fake_useragent.UserAgent

# Function to set up Chrome options with a fake User-Agent
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    #chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    user_agent = fake_useragent.UserAgent().random
    chrome_options.add_argument(f"user-agent={user_agent}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_window_size(1920, 1080)
    driver.implicitly_wait(10)
    driver.maximize_window()
    driver.delete_all_cookies()
    return driver


def ler_links_do_csv(csv_filename):
    links = []

    with open(csv_filename, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['Link']:
                links.append(row['Link'])

    return links


def clean_html(raw_html):
    clean_text = re.sub('<.*?>', '', raw_html)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text.strip()


def check_feature(feature_text, features):
    return "Sim" if feature_text in features else "Não"


def process_price(average_cost_raw):
    average_cost = clean_html(average_cost_raw)

    if "mais de" in average_cost:
        min_price = float(re.findall(r'\d+', average_cost)[0])  # Extrai o número após "mais de"
        max_price = min_price
    elif "-" in average_cost:
        # Separa pelo intervalo "-"
        price_parts = average_cost.replace("BRL", "").split("-")
        min_price = float(price_parts[0].strip())
        max_price = float(price_parts[1].strip())
    else:
        # Caso o valor seja único
        min_price = float(re.findall(r'\d+', average_cost)[0])
        max_price = min_price

    average_price = (min_price + max_price) / 2

    price_range = f"{min_price:.2f} À {max_price:.2f}" if min_price != max_price else f"{min_price:.2f}"

    return min_price, max_price, average_price, price_range


def get_element_text_or_default(container, selector, default=""):
    try:
        element = container.find_element(By.CSS_SELECTOR, selector)
        return element.text
    except NoSuchElementException:
        return default


def write_csv_file(data, csv_filename):
    file_exists = os.path.isfile(csv_filename)
    with open(csv_filename, mode='a', newline='', encoding='utf-8') as file:  # Mude 'w' para 'a'
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "Nome", "Endereço", "Estado", "Cidade", "País", "CEP",
                "Total de Avaliações", "Média de Avaliações", "Avaliação Google", "Avaliação Foursquare",
                "Avaliação Facebook", "Avaliação Trip",
                "Posição no Ranking da Cidade",
                "Site", "Instagram", "Telefone",
                "Tipos de Cozinha", "Horário",
                "Faixa de Preço por Pessoa", "Preço Médio por Pessoa",
                "Estacionamento", "Lugares Ao Ar Livre", "Wi-Fi", "Reserva", "Entrega", "Para Viagem", "Música", "TV",
                "Acessível a cadeiras de rodas", "Crianças", "Grupos Grandes", "Serviço de Garçom"
            ])

        writer.writerow(data.values())



def get_restaurant_data(url):
    try:

        driver = setup_driver()

        driver.get(url)

        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.content_wide"))
        )

        name = container.find_element(By.CSS_SELECTOR, "h1.notranslate a").text

        try:
            closed_info = (container.find_element(By.CSS_SELECTOR, "div.closed_info_block")
                           .get_attribute("innerHTML"))
        except NoSuchElementException:
            closed_info = ""
        if closed_info.__contains__("Pode ser permanentemente fechado"):
            return "Restaurante fechado permanentemente", name

        try:
            number_of_reviews = container.find_element(By.CSS_SELECTOR, "span.rating-stars__text").text.split()[0]
        except NoSuchElementException:
            return "Sem avaliações"

        position_in_city_rank = container.find_element(By.CSS_SELECTOR, "a.number").text
        address_full = container.find_element(By.CSS_SELECTOR, "div.address").text.replace("\n", " ").replace(
            "Endereço ", "")
        address_parts = address_full.split(", ")
        print(address_parts)

        address = f"{address_parts[0]}, {address_parts[1]}"
        city = address_parts[2]
        state = address_parts[3]
        country = address_parts[4] if len(address_parts) > 4 else "Sem Informação"
        postal_code = address_parts[5] if len(address_parts) > 5 else "Sem Informação"

        site = get_element_text_or_default(container, "div.website a", "Sem Informação")
        instagram = get_element_text_or_default(container, "div.instagram a", "Sem Informação")
        phone_number = get_element_text_or_default(container, "a.call", "Sem Informação")
        features_text = container.find_element(By.CSS_SELECTOR, "div.features_block .overflow").text

        # Extraindo tipos de cozinha
        cuisine_container = container.find_element(By.CSS_SELECTOR, "div.wrapper_main_info")
        cuisine_elements_span = cuisine_container.find_elements(By.CSS_SELECTOR, "div.cuisine_hidden span")

        cuisines = [cuisine.get_attribute("innerHTML") for cuisine in
                    cuisine_elements_span] if cuisine_elements_span else ["Não especificado"]
        cuisines = [clean_html(cuisine) for cuisine in cuisines if cuisine]

        # Preço médio com remoção de HTML
        try:
            average_cost_raw = cuisine_container.find_element(By.CSS_SELECTOR, "span.nowrap").get_attribute(
                "innerHTML")
            min_price, max_price, average_price, price_range = process_price(average_cost_raw)
        except NoSuchElementException:
            min_price, max_price, average_price, price_range = "Sem Informação", "Sem Informação", "Sem Informação", "Sem Informação"

        # Horário de funcionamento
        try:
            schedule_table = driver.find_element(By.CSS_SELECTOR, "table.schedule-table tbody")
        except NoSuchElementException:
            return "Sem Informação de horario"

        schedule_rows = schedule_table.find_elements(By.TAG_NAME, "tr")
        schedule = [
            f"{row.find_element(By.TAG_NAME, 'td').text}: {row.find_elements(By.TAG_NAME, 'td')[1].text}"
            for row in
            schedule_rows]
        schedule = [sch.replace("\n", " ") for sch in schedule if sch]
        print(schedule)

        # Extraindo avaliações de diferentes plataformas
        ratings = {}
        rating_elements = container.find_elements(By.CSS_SELECTOR, "div.wrapper_ratings .row")

        total_rating = 0
        ratings_count = 0

        for rating in rating_elements:
            platform = rating.find_element(By.CSS_SELECTOR, "p").text
            try:
                rating_value = rating.find_element(By.CSS_SELECTOR, "span.agency-count").text
            except NoSuchElementException:
                rating_value = "Sem Avaliação"

            if rating_value != "Sem Avaliação":
                # Verifica a escala de avaliação (ex: 4,5/5 ou 9/10)
                if "/" in rating_value:
                    rating_value = rating_value.replace("(", "").replace(")", "")
                    value, scale = rating_value.split("/")
                    value = float(value.replace(",", "."))
                    scale = float(scale)

                    # Normaliza para a escala de 5
                    normalized_value = (value / scale) * 5
                    normalized_value = round(normalized_value, 1)
                    ratings[platform] = normalized_value
                else:
                    normalized_value = float(rating_value.replace(",", "."))
                    normalized_value = round(normalized_value, 1)
                    ratings[platform] = normalized_value

                total_rating += normalized_value
                ratings_count += 1

        average_rating = 0
        # Calcula a média se houverem avaliações válidas
        if ratings_count > 0:
            average_rating = total_rating / ratings_count
            average_rating = round(average_rating, 1)

        # Extraindo os dados de características
        estacionamento = check_feature("Estacionamento", features_text)
        lugares_ao_ar_livre = check_feature("Lugares ao ar livre", features_text)
        wifi = check_feature("Wi-fi", features_text)
        reserva = check_feature("Reserva", features_text)
        entrega = check_feature("Entrega", features_text)
        para_viagem = check_feature("Leve embora", features_text)
        musica = check_feature("Música", features_text)
        tv = check_feature("TV", features_text)
        acessivel_cadeiras = check_feature("Acessível a cadeiras de rodas", features_text)
        criancas = check_feature("Crianças", features_text)
        grupos_grandes = check_feature("Grupos grandes", features_text)
        servico_garcom = check_feature("Serviço de garçom", features_text)

        return {
            "name": name,
            "address": address,
            "state": state,
            "city": city,
            "country": country,
            "postal_code": postal_code,
            "number_of_reviews": number_of_reviews,
            "average_rating": average_rating,
            "google_rating": ratings.get('Google', 'Sem Avaliação'),
            "foursquare_rating": ratings.get('Foursquare', 'Sem Avaliação'),
            "facebook_rating": ratings.get('Facebook', 'Sem Avaliação'),
            "trip_rating": ratings.get('Trip', 'Sem Avaliação'),
            "position_in_city_rank": position_in_city_rank,
            "site": site,
            "instagram": instagram,
            "phone_number": phone_number,
            "cuisines": ', '.join(cuisines),
            "schedule": '; '.join(schedule),  # Uma string única de horários
            "price_range": price_range,
            "average_price": average_price,
            "estacionamento": estacionamento,
            "lugares_ao_ar_livre": lugares_ao_ar_livre,
            "wifi": wifi,
            "reserva": reserva,
            "entrega": entrega,
            "para_viagem": para_viagem,
            "musica": musica,
            "tv": tv,
            "acessivel_a_cadeiras_rodas": acessivel_cadeiras,
            "children": criancas,
            "grupos_grandes": grupos_grandes,
            "servico_garcom": servico_garcom
        }


    except TimeoutException:
        error = f"Tempo de espera excedido para o restaurante: {url}"
        print(error)
        return error


def extract_and_load_data(urls):
    for index, url in enumerate(urls):
        print(index)
        time.sleep(2)

        data = get_restaurant_data(url)
        if data.__contains__("Restaurante fechado permanentemente"):
            print(f"Restaurante fechado permanentemente: {url}")
            _, name = data
            insert_error_log(name, "Restaurante fechado permanentemente", index)
            insert_index(index)
            continue
        elif data.__contains__("Tempo de espera excedido"):
            print(f"Tempo de espera excedido: {url}")
            retries = 0
            while retries < 5:
                print("retrying")
                data = get_restaurant_data(url)
                print(data)
                if data.__contains__("Tempo de espera excedido"):
                    retries += 1
                    time.sleep(60)
                else:
                    print(f"Max retries exceeded for {url}. wainting some minutes.")
                    time.sleep(60 * 5)
                    retries = 0
                    continue


        elif data.__contains__("Sem Informação de horario"):
            print(f"Sem Informação de horario: {url}")
            insert_error_log(url, "Sem Informação de horario", index)
            insert_index(index)
            continue
        elif data.__contains__("Sem avaliações"):
            print(f"Sem avaliações: {url}")
            insert_error_log(url, "Sem avaliações", index)
            insert_index(index)
            continue
        else:
            insert_restaurant(data)
            insert_index(index)
            continue


def parse_restaurant_data(data_string):
    # Remove as aspas extras e transforma em uma lista
    data_list = ast.literal_eval(data_string)  # Converte a string para uma lista

    # Converte cada string de dicionário para um dicionário
    parsed_data = [ast.literal_eval(item) for item in data_list]

    return parsed_data


def copy_db_to_csv():
    data = fetch_restaurant_data()
    for row in data:
        row.pop("id")
        print(row)
        write_csv_file(row, csv_filename)




def fetch_and_save_as_json():
    data = fetch_restaurant_data()  # Supondo que isso retorna uma lista de dicionários
    with open("etc/restaurants.json", mode='a', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)  # Grava os dados no formato JSON

    print("Dados salvos como JSON com sucesso.")


# Chame a função
#fetch_and_save_as_json()

def load_and_insert_restaurants():
    with open("etc/restaurants.json", mode='r', encoding='utf-8') as file:
        restaurants = json.load(file)

    for restaurant in restaurants:
        restaurant.pop("id", None)
        insert_restaurant(restaurant)

# Chame a função
#load_and_insert_restaurants()


csv_filename_reader = "etc/restaurantes(1).csv"
links_restaurantes = ler_links_do_csv(csv_filename_reader)

start_index = int(os.getenv("START_INDEX", 421))
end_index = int(os.getenv("END_INDEX", 1000))

print(f"Start index: {start_index} - End index: {end_index}")

restaurant_urls = links_restaurantes[start_index:end_index]
#print(restaurant_urls)

csv_filename = "etc/restaurant_detailed_data(1).csv"

#extract_and_load_data(restaurant_urls)
copy_db_to_csv()
