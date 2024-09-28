import os

import psycopg2

db_host = os.getenv("DB_HOST") or "localhost"
db_port = os.getenv("DB_PORT") or "5433"
db_name = os.getenv("DB_NAME") or "postgres"

def connect_db():
    """Estabelece uma conexão com o banco de dados PostgreSQL."""
    return psycopg2.connect(
        dbname=db_name,
        user="postgres",
        password="123456",
        host=db_host,
        port=db_port
    )

def create_tables():
    """Cria as tabelas necessárias no banco de dados."""
    create_restaurant_table_query = """
        CREATE TABLE IF NOT EXISTS restaurantes (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(255) NOT NULL UNIQUE,
        endereco VARCHAR(255) NOT NULL,
        estado VARCHAR(100) NOT NULL,
        cidade VARCHAR(100) NOT NULL,
        pais VARCHAR(100) NOT NULL,
        cep VARCHAR(20),
        total_avaliacoes VARCHAR(20),
        media_avaliacoes VARCHAR(20),
        avaliacao_google VARCHAR(20),
        avaliacao_foursquare VARCHAR(20),
        avaliacao_facebook VARCHAR(20),
        avaliacao_trip VARCHAR(20),
        posicao_ranking VARCHAR(255),
        site VARCHAR(255),
        instagram VARCHAR(255),
        telefone VARCHAR(20),
        tipos_cozinha VARCHAR(255),
        horario TEXT,
        faixa_preco_pessoa VARCHAR(50),
        preco_medio_pessoa VARCHAR(50),
        estacionamento VARCHAR(3),
        lugares_ao_ar_livre VARCHAR(3),
        wifi VARCHAR(3),
        reserva VARCHAR(3),
        entrega VARCHAR(3),
        para_viagem VARCHAR(3),
        musica VARCHAR(3),
        tv VARCHAR(3),
        acessivel_a_cadeiras_rodas VARCHAR(3),
        criancas VARCHAR(3),
        grupos_grandes VARCHAR(3),
        servico_garcom VARCHAR(3)
    );
    """

    create_control_table_query = """
        CREATE TABLE IF NOT EXISTS control_table (
            id SERIAL PRIMARY KEY,
            current_index INT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """

    create_error_log_table = """
        CREATE TABLE IF NOT EXISTS error_log (
            id SERIAL PRIMARY KEY,
            restaurant_name VARCHAR(255),
            error_message TEXT,
            index INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """

    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(create_restaurant_table_query)
            cursor.execute(create_control_table_query)
            cursor.execute(create_error_log_table)
            conn.commit()

    print("Tabelas criadas com sucesso!")


def insert_restaurant(data):
    """Insere os dados de um restaurante na tabela correspondente."""
    insert_query = """
    INSERT INTO restaurantes (
        nome, endereco, estado, cidade, pais, cep,
        total_avaliacoes, media_avaliacoes, avaliacao_google, avaliacao_foursquare,
        avaliacao_facebook, avaliacao_trip, posicao_ranking,
        site, instagram, telefone, tipos_cozinha, horario,
        faixa_preco_pessoa, preco_medio_pessoa, estacionamento, lugares_ao_ar_livre,
        wifi, reserva, entrega, para_viagem, musica, tv,
        acessivel_a_cadeiras_rodas, criancas, grupos_grandes, servico_garcom
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                values = list(data.values())

                # Verifique o número de valores
                print(f"Dados a serem inseridos: {values}")
                print(f"Número de valores: {len(values)}")

                cursor.execute(insert_query, values)
                conn.commit()
                print("Restaurante inserido com sucesso:", data['name'])

    except Exception as e:
        print("Erro ao inserir restaurante:", e)


def insert_error_log(restaurant_name, error_message, index):
    """Insere um log de erro na tabela de logs."""
    insert_query = """
    INSERT INTO error_log (restaurant_name, error_message, index)
    VALUES (%s, %s, %s)
    """

    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(insert_query, (restaurant_name, error_message, index))
                conn.commit()
                print("Log de erro inserido com sucesso para:", restaurant_name)  # Nome do restaurante

    except Exception as e:
        print("Erro ao inserir log de erro:", e)

def insert_index(index):
    """Insere o índice atual na tabela de controle."""
    update_query = """
    UPDATE control_table
    SET current_index = %s, timestamp = CURRENT_TIMESTAMP
    """

    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(update_query, (index,))
                conn.commit()
                print("Índice inserido com sucesso!")

    except Exception as e:
        print("Erro ao inserir índice:", e)


def fetch_restaurant_data():

    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM restaurantes;")
                data = cursor.fetchall()
                return data

    except Exception as e:
        print(f"Ocorreu um erro: {e}")



create_tables()