import psycopg2, os
from dotenv import load_dotenv
import json


def verify_db_connection():
    try:
        conn = psycopg2.connect(database=os.getenv("DATABASE_NAME", "spore_db"),
                                host=os.getenv("host", "localhost"),
                                user=os.getenv("user", "postgres"),
                                password=os.getenv("password", ""),
                                port=os.getenv("port", "5432"))
        conn.close()
        return True
    except psycopg2.Error as e:
        print("Unable to connect to the database")
        return False

def initialize_connection():
    try:
        conn = psycopg2.connect(database=os.getenv("DATABASE_NAME", "spore_db"),
                                host=os.getenv("host", "localhost"),
                                user=os.getenv("user", "postgres"),
                                password=os.getenv("password", ""),
                                port=os.getenv("port", "5432"))
        return conn
    except psycopg2.Error as e:
        print("Unable to connect to the database")
        return False

def last_indexed_nft_control():
    conn = initialize_connection()
    c= conn.cursor()
    #return both values of last block indexed
    query = """SELECT * FROM nft_control WHERE table_name='nft_buys'"""
    c.execute(query)
    result = c.fetchall()
    #handle an empty response
    if len(result) == 0:
        nft_buys_last_indexed = 0
    else:
        nft_buys_last_indexed = result[0][2]
    query = """SELECT * FROM nft_control WHERE table_name='nft_prices'"""
    c.execute(query)
    result = c.fetchall()
    if len(result) == 0:
        nft_prices_last_indexed = 0
    else:
        nft_prices_last_indexed = result[0][2]
    return nft_buys_last_indexed, nft_prices_last_indexed

