import psycopg2, os
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3._utils.filters import construct_event_filter_params
from web3._utils.events import get_event_data
from eth_abi.codec import ABICodec
import json

load_dotenv()

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
        print(e.pgerror)
        print(e.diag.message_detail)
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
        print(e.pgerror)
        print(e.diag.message_detail)
        return False

#in the case of the NFTs there are two tables to be created plus one for the control; the first one is the table filtered for all buy events with tx hash and block, to calculate the total volume of the token. The second one tells the price of each of the 72 NFTs; the third one is the control, which tells you the last block indexed

def create_nft_tables():
    conn = initialize_connection()
    c= conn.cursor()
    query = """CREATE TABLE IF NOT EXISTS nft_buys (
        id SERIAL PRIMARY KEY,
        blockNumber INTEGER,
        transactionHash TEXT,
        tokenId INTEGER,
        value TEXT
    )"""
    c.execute(query)
    conn.commit()
    query = """CREATE TABLE IF NOT EXISTS nft_prices (
        id SERIAL PRIMARY KEY,
        tokenId INTEGER,
        price TEXT
    )"""
    c.execute(query)
    conn.commit()
    query = """
        CREATE TABLE IF NOT EXISTS nft_control (
            id SERIAL PRIMARY KEY,
            table_name TEXT,
            lastBlock INTEGER
        );
        INSERT INTO nft_control (table_name, lastBlock) 
        SELECT 'nft_buys', 1747108 WHERE NOT EXISTS (SELECT 1 FROM nft_control WHERE table_name = 'nft_buys');
        INSERT INTO nft_control (table_name, lastBlock) 
        SELECT 'nft_prices', 1747108 WHERE NOT EXISTS (SELECT 1 FROM nft_control WHERE table_name = 'nft_prices');
    """
    c.execute(query)
    conn.commit()
    conn.close()


def connect_and_get_Bought_event():
    chain_url=  "https://api.avax.network/ext/bc/C/rpc"
    #spore nftv1 address avalanche
    contract_address= "0xc2457F6Eb241C891EF74E02CCd50E5459c2E28Ea"
    with open('abi/nftv1_abi.json') as abi:
        nftv1_abi = json.load(abi)
    web3 = Web3(Web3.HTTPProvider(chain_url))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    # print("clientVersion: ",web3.client_version)
    # print("isConnected: ",web3.is_connected())
    contract = web3.eth.contract(address=contract_address, abi=nftv1_abi)
    #attributes = vars(contract.events)
    event=contract.events.Bought
    return web3, event

def get_last_block(table_name):
    conn = initialize_connection()
    c= conn.cursor()
    query = "SELECT lastBlock FROM nft_control WHERE table_name = %s"
    c.execute(query, (table_name,))
    result = c.fetchone()
    last_block = result[0] if result else None
    conn.close()
    return last_block

def get_ava_latest_block():
    try:
        chain_url=  "https://api.avax.network/ext/bc/C/rpc"
        web3 = Web3(Web3.HTTPProvider(chain_url))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        latest_block= web3.eth.get_block('latest')['number']
        return latest_block
    except Exception as e:
        print(e)
        return False

def bought_event_filter(fromBlock,toBlock, web3, event):
    abi = event._get_event_abi()
    codec: ABICodec = web3.codec
    nftv1_address= "0xc2457F6Eb241C891EF74E02CCd50E5459c2E28Ea"
    data_filter_set, event_filter_params = construct_event_filter_params(
            abi,
            codec,
            contract_address=nftv1_address,
            fromBlock=fromBlock,
            toBlock=toBlock,
            address=None,
            topics=None,
    )
    # Call node over JSON-RPC API
    try:
        logs = web3.eth.get_logs(event_filter_params)
    except Exception as e:
        return
    for log in logs:
        # Convert raw JSON-RPC log result to human readable event by using ABI data
        # More information how processLog works here
        # https://github.com/ethereum/web3.py/blob/fbaf1ad11b0c7fac09ba34baff2c256cffe0a148/web3/_utils/events.py#L200
        evt = get_event_data(codec, abi, log)
        print(evt)
        exit()
        # handle_bought_event(evt)


def process_nft_buy_events(web3, event, from_block, to_block):
    conn = initialize_connection()
    c= conn.cursor()
    logs = event.get_logs(fromBlock=from_block, toBlock=to_block)
    for log in logs:
        print(log)
        blockNumber = log['blockNumber']
        transactionHash = log['transactionHash'].hex()
        tokenId = log['args']['tokenId']
        value = log['args']['value']
        query = "INSERT INTO nft_buys (blockNumber, transactionHash, tokenId, value) VALUES (%s, %s, %s, %s)"
        c.execute(query, (blockNumber, transactionHash, tokenId, value))
    conn.commit()
    query = "UPDATE nft_control SET lastBlock = %s WHERE table_name = 'nft_buys'"
    c.execute(query, (to_block,))
    conn.commit()
    conn.close()


def index_nft_bought_data():
    connected = verify_db_connection()
    if not connected:
        print("Unable to connect to the database")
        return False
    create_nft_tables()
    web3, event = connect_and_get_Bought_event()
    current_block = get_last_block("nft_buys")
    latest_block= web3.eth.get_block('latest')['number']
    print(f"Last block indexed: {latest_block}, Current block: {current_block}")
    initial_block = 41756273
    while current_block<latest_block:
        if current_block==latest_block:
            print("All blocks indexed")
            break
        if current_block>initial_block:
            from_block=current_block+1
        else:
            from_block=current_block
        if current_block+2047>latest_block:
            to_block=latest_block
        else:
            to_block=current_block+2047

        print("indexing from {} to {}".format(from_block, to_block))
        process_nft_buy_events(web3, event, from_block, to_block)
        current_block=to_block
    
def add_first_data_to_nft_prices():
    conn = initialize_connection()
    c= conn.cursor()
    query = "SELECT * FROM nft_prices"
    c.execute(query)
    result = c.fetchone()
    if result==None:
        query = "INSERT INTO nft_prices (tokenId, price) VALUES (%s, %s)"
        for i in range(1, 73):
            c.execute(query, (i, "0"))
        conn.commit()
    conn.close()


def get_token_price(tokenId):
    chain_url=  "https://api.avax.network/ext/bc/C/rpc"
    #spore nftv1 address avalanche
    contract_address= "0xc2457F6Eb241C891EF74E02CCd50E5459c2E28Ea"
    with open('abi/nftv1_abi.json') as abi:
        nftv1_abi = json.load(abi)
    web3 = Web3(Web3.HTTPProvider(chain_url))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    contract = web3.eth.contract(address=contract_address, abi=nftv1_abi)

    bazzar_mapping = contract.functions.Bazaar(tokenId).call()
    price = bazzar_mapping[1]
    return price

def index_nft_price_data():
    conn = initialize_connection()
    if not conn:
        print("Unable to connect to the database")
        return False
    c= conn.cursor()
    current_block = get_last_block("nft_prices")
    chain_url=  "https://api.avax.network/ext/bc/C/rpc"
    web3 = Web3(Web3.HTTPProvider(chain_url))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    latest_block= web3.eth.get_block('latest')['number']
    if current_block<latest_block:
        #populate nft_prices table if there are no entries
        add_first_data_to_nft_prices()

        #query all the tokens and update the price
        query = "SELECT * FROM nft_prices"
        c.execute(query)
        result = c.fetchall()
        for row in result:
            tokenId = row[1]
            price = get_token_price(tokenId)
            query = "UPDATE nft_prices SET price = %s WHERE tokenId = %s"
            c.execute(query, (price, tokenId))
        conn.commit()
        query = "UPDATE nft_control SET lastBlock = %s WHERE table_name = 'nft_prices'"
        c.execute(query, (latest_block,))
        conn.commit()
        conn.close()
    else:
        print("All blocks indexed")


def nft_get_total_volume():
    conn = initialize_connection()
    c= conn.cursor()
    query = "SELECT SUM(CAST(value AS DECIMAL)) FROM nft_buys"
    c.execute(query)
    result = c.fetchone()
    total_volume = result[0]
    conn.close()
    return int(total_volume)/10**18

def nft_get_floor_price():
    conn = initialize_connection()
    c= conn.cursor()
    #select min price that is not 0
    query = "SELECT MIN(CAST(price AS DECIMAL)) FROM nft_prices WHERE CAST(price AS DECIMAL) != 0"
    c.execute(query)
    result = c.fetchone()
    floor_price = result[0]
    conn.close()
    return int(floor_price)/10**18

def nft_get_last_sale():
    conn = initialize_connection()
    c= conn.cursor()
    query = "SELECT value FROM nft_buys ORDER BY id DESC LIMIT 1"
    c.execute(query)
    result = c.fetchone()
    last_sale = result[0]
    conn.close()
    return int(last_sale)/10**18

def update_nft_db():
    verify_db_connection()
    index_nft_price_data()
    index_nft_bought_data()