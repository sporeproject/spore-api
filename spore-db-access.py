import psycopg2
from os.path import exists
from time import sleep
from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
from web3._utils.filters import construct_event_filter_params
from web3._utils.events import get_event_data
from eth_abi.codec import ABICodec
import os
from dotenv import load_dotenv
load_dotenv()

with open('abi/spore_abi.json') as abi:
    spore_abi = json.load(abi)


avax_url= os.getenv("RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
bsc_url="https://bsc-dataseed1.defibit.io/"

spore_address_avalanche="0x6e7f5C0b9f4432716bDd0a77a3601291b9D9e985"
spore_address_bsc="0x33A3d962955A3862C8093D1273344719f03cA17C"


def verify_db_connection():
    try:
        conn = psycopg2.connect(database=os.getenv("DATABASE_NAME", "spore_db"),
                                host=os.getenv("DATABASE_HOST", "localhost"),
                                user=os.getenv("DATABASE_USER", "postgres"),
                                password=os.getenv("DATABASE_PASSWORD", ""),
                                port=os.getenv("DATABASE_PORT", "5432"))
        conn.close()
        return True
    except psycopg2.Error as e:
        print("Unable to connect to the database")
        print(e.pgerror)
        print(e.diag.message_detail)
        return False

def create_table(table_name):
    conn = psycopg2.connect(database=os.getenv("DATABASE_NAME", "spore_db"),
                            host=os.getenv("DATABASE_HOST", "localhost"),
                            user=os.getenv("DATABASE_USER", "postgres"),
                            password=os.getenv("DATABASE_PASSWORD", ""),
                            port=os.getenv("DATABASE_PORT", "5432"))
    c= conn.cursor()
    c.execute("""CREATE TABLE %s (
                _id SERIAL PRIMARY KEY,
                txHash VARCHAR(68) NOT NULL,
                txfrom VARCHAR(42) NOT NULL,
                txto VARCHAR(42) NOT NULL,
                txvalue double precision not null,
                blockNumber integer not null
                )"""%table_name)
    conn.commit()
    conn.close()

def drop_table(table_name):
    conn = psycopg2.connect(database=os.getenv("DATABASE_NAME", "spore_db"),
                            host=os.getenv("DATABASE_HOST", "localhost"),
                            user=os.getenv("DATABASE_USER", "postgres"),
                            password=os.getenv("DATABASE_PASSWORD", ""),
                            port=os.getenv("DATABASE_PORT", "5432"))
    c= conn.cursor()
    c.execute("""DROP TABLE %s"""%table_name)
    conn.commit()
    conn.close()


# db_name="tx_bsc"
# drop_table(db_name)
# create_table(db_name)
# db_name="tx_avax"
# drop_table(db_name)
# create_table(db_name)
# exit()

def connect_and_get_event(chain):
    if chain == "avax":
        chain_url= avax_url
        contract_address= spore_address_avalanche
    elif chain == "bsc":
        chain_url= bsc_url
        contract_address= spore_address_bsc

    web3 = Web3(Web3.HTTPProvider(chain_url))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    print("clientVersion: ",web3.client_version)
    print("isConnected: ",web3.is_connected())
    contract = web3.eth.contract(address=contract_address, abi=spore_abi)
    event=contract.events.Transfer
    return web3, event

def event_filter(fromBlock,toBlock, web3, event, chain):
    abi = event._get_event_abi()
    codec: ABICodec = web3.codec

    if chain == "avax":
        spore_address= spore_address_avalanche
    elif chain == "bsc":
        spore_address= spore_address_bsc
    data_filter_set, event_filter_params = construct_event_filter_params(
            abi,
            codec,
            contract_address=spore_address,
            fromBlock=fromBlock,
            toBlock=toBlock,
            address=None,
            topics=None,
    )
    # Call node over JSON-RPC API
    logs = web3.eth.get_logs(event_filter_params)
    for log in logs:
        # Convert raw JSON-RPC log result to human readable event by using ABI data
        # More information how processLog works here
        # https://github.com/ethereum/web3.py/blob/fbaf1ad11b0c7fac09ba34baff2c256cffe0a148/web3/_utils/events.py#L200
        evt = get_event_data(codec, abi, log)
        handle_event(evt, chain)

def handle_event(element,chain):
        txhash=element['transactionHash'].hex()
        txfrom=str(element['args']['from'])
        txto=str(element['args']['to'])
        txvalue=str(element['args']['value'])
        blockNumber=str(element['blockNumber'])
        row_data= (txhash,txfrom,txto,txvalue,blockNumber)
        write_data(row_data, chain)

def write_data(row_data, chain):
    if chain == "avax":
        db_name= "tx_avax"
    elif chain == "bsc":
        db_name= "tx_bsc"              
    conn = psycopg2.connect(database=os.getenv("DATABASE_NAME", "spore_db"),
                            host=os.getenv("DATABASE_HOST", "localhost"),
                            user=os.getenv("DATABASE_USER", "postgres"),
                            password=os.getenv("DATABASE_PASSWORD", ""),
                            port=os.getenv("DATABASE_PORT", "5432"))
    c= conn.cursor()
    sql = f'''INSERT INTO %s '''%db_name
    sql = sql+ f'''VALUES (DEFAULT,%s,%s,%s,%s,%s)'''
    print(row_data)
    c.execute(sql,row_data)
    conn.commit()
    conn.close()

def initialize_process(chain):
        if chain == "avax":
            initial_block= 642754
            table_name="tx_avax"
        elif chain == "bsc":
            initial_block= 6321472
            table_name="tx_bsc"
        
        conn = psycopg2.connect(database=os.getenv("DATABASE_NAME", "spore_db"),
                            host=os.getenv("DATABASE_HOST", "localhost"),
                            user=os.getenv("DATABASE_USER", "postgres"),
                            password=os.getenv("DATABASE_PASSWORD", ""),
                            port=os.getenv("DATABASE_PORT", "5432"))

        query = "SELECT * FROM %s ORDER BY blockNumber DESC LIMIT 1"%table_name
        c= conn.cursor()
        c.execute(query)
        result = c.fetchone()
        if result==None:
            current_block= initial_block
        else:
            current_block=result[5]
        # Close the connection
        conn.close()
        print("currentblock inside the loop {}".format(current_block))

        return initial_block,current_block

def main(chain):
    verify_db_connection()
    exit()
    web3, event=connect_and_get_event(chain)
    latest_block= web3.eth.get_block('latest')['number']
    initial_block,current_block= initialize_process(chain)
    print("initial block {}, current block {}, latest block {}".format(initial_block, current_block, latest_block))
    i=0
    while current_block<latest_block:
        if current_block>initial_block:
            from_block=current_block+1
        else:
            from_block=current_block
        if current_block+2048>latest_block:
            to_block=latest_block
        else:
            to_block=current_block+2048
        event_filter(from_block,to_block, web3, event, chain)
        current_block=to_block
        
        print("indexing from {} to {}".format(from_block, to_block))
    
        if chain == "bsc":
            sleep(1)

        # i+=1
        # if i ==2:
        #     print(i)
        #     exit()
        # for event in block_filter.get_all_entries():
        #     handle_event(event)


main("avax")







# print("""CREATE TABLE %s (
#             _id SERIAL PRIMARY KEY,
#             txHash VARCHAR(64) NOT NULL,
#             txfrom VARCHAR(40) NOT NULL,
#             txto VARCHAR(40) NOT NULL,
#             blockNumber integer not null
#             )"""%db_name)
# exit()
# c.execute("""CREATE TABLE %s (
#             _id SERIAL PRIMARY KEY,
#             txHash VARCHAR(64) NOT NULL,
#             txfrom VARCHAR(40) NOT NULL,
#             txto VARCHAR(40) NOT NULL,
#             blockNumber integer not null
#             )"""%db_name)
# conn.commit()

    














