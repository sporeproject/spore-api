from time import sleep
import json
import spore_db_utils as db_utils


with open('abi/spore_abi.json') as abi:
    spore_abi = json.load(abi)
with open('abi/nftv1_abi.json') as abi:
    nftv1_abi = json.load(abi)


# avax_url= os.getenv("RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
bsc_url="https://bsc-dataseed1.defibit.io/"

spore_address_avalanche="0x6e7f5C0b9f4432716bDd0a77a3601291b9D9e985"
spore_address_bsc="0x33A3d962955A3862C8093D1273344719f03cA17C"


# def drop_table(table_name):
#     conn = psycopg2.connect(database=os.getenv("DATABASE_NAME", "spore_db"),
#                             host=os.getenv("DATABASE_HOST", "localhost"),
#                             user=os.getenv("DATABASE_USER", "postgres"),
#                             password=os.getenv("DATABASE_PASSWORD", ""),
#                             port=os.getenv("DATABASE_PORT", "5432"))
#     c= conn.cursor()
#     c.execute("""DROP TABLE %s"""%table_name)
#     conn.commit()
#     conn.close()


def update_db():
    db_utils.verify_db_connection()
    db_utils.index_nft_price_data()
    db_utils.index_nft_bought_data()








    














