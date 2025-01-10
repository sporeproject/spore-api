import json
import time
import math
import requests
from web3 import Web3
from web3.middleware import geth_poa_middleware
from decimal import Decimal
import os

# Token configurations
avax_tokens = {
    "wavax": {
        "symbol": "AVAX",
        "address": {
            43114: "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
            43113: "",
        },
        "decimals": 18,
    },
    "usdt": {
        "symbol": "USDT",
        "address": {
            43114: "0xc7198437980c041c805A1EDcbA50c1Ce5db95118",
            43113: "",
        },
        "decimals": 18,
    },
    "spore": {
        "symbol": "SPORE",
        "address": {
            43114: "0x6e7f5C0b9f4432716bDd0a77a3601291b9D9e985",
            43113: "",
        },
        "decimals": 9,
    }
}

bsc_tokens = {
    "wbnb": {
        "chainId": 56,
        "symbol": "BNB",
        "address": {
            56: "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
            97: "",
        },
        "decimals": 18,
    },
    "usdt": {
        "chainId": 56,
        "symbol": "USDT",
        "address": {
            56: "0x55d398326f99059fF775485246999027B3197955",
            97: "",
        },
        "decimals": 18,
    },
    "spore": {
        "chainId": 56,
        "symbol": "SPORE",
        "address": {
            56: "0x33A3d962955A3862C8093D1273344719f03cA17C",
            97: "",
        },
        "decimals": 9,
    }
}

# Load contract ABI
with open('abi/spore_abi.json') as abi_file:
    spore_abi = json.load(abi_file)

# RPC URLs
avax_rpc_url = "https://api.avax.network/ext/bc/C/rpc"
bsc_rpc_url = "https://bsc-dataseed1.defibit.io/"

# Wallet addresses
avax_LP = "0x0a63179a8838b5729e79d239940d7e29e40a0116"
bsc_LP = "0x4aA8F0ef7dd950e260d5EeaF50A1D796D0cefd2f"

# Initialize Web3 providers
avax_web3 = Web3(Web3.HTTPProvider(avax_rpc_url))
bsc_web3 = Web3(Web3.HTTPProvider(bsc_rpc_url))

# verify connection
if not avax_web3.is_connected():
    raise ConnectionError("Avalanche Web3 connection failed.")
if not bsc_web3.is_connected():
    raise ConnectionError("Binance Smart Chain Web3 connection failed.")

avax_web3.middleware_onion.inject(geth_poa_middleware, layer=0)
bsc_web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Cache for calc results
cache = {
    "data": None,
    "timestamp": time.time()
}


def fetch_asset_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=1&interval=daily"
    try:
        response = requests.get(url)
        response.raise_for_status()
        price = response.json()['prices'][0][1]
        return Decimal(price)
    except Exception as e:
        return Decimal(0)

def get_checksum_address(address):
    try:
        return Web3.to_checksum_address(address)
    except ValueError:
        return None

def get_balance(web3, contract_address, wallet, abi):
    contract = web3.eth.contract(address=contract_address, abi=abi)
    try:
        checksum_wallet = get_checksum_address(wallet)
        if not checksum_wallet:
            return Decimal(0)
        balance = contract.functions.balanceOf(checksum_wallet).call()
        return Decimal(balance) / Decimal(1e9)
    except Exception:
        return Decimal(0)

def read_price_indexing_file():
    file_exists = os.path.isfile('price_indexing.json')
    if not file_exists:
        default_data = {"last_timestamp": "0", "price_avax": "0", "price_bsc": "0", "price_diff": "0", "market_cap": "0"}
        with open('price_indexing.json', 'w+') as file:
            json.dump(default_data, file)
        return default_data
    else:
        with open('price_indexing.json', 'r') as file:
            return json.load(file)


def write_price_indexing_file(data):
    with open('price_indexing.json', 'w+') as file:
        json.dump(data, file)

def fetch_market_cap(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=1&interval=daily"
    try:
        response = requests.get(url)
        response.raise_for_status()
        market_caps = response.json().get('market_caps', [])
        if market_caps:
            market_cap = market_caps[-1][-1]
            return "{:,.0f}".format(market_cap)  # Format with commas
        return "0"
    except Exception as e:
        print(f"Error fetching market cap: {e}")
        return "0"
    
def format_large_number(number):
    """
    Formats a large number into a more readable format with suffixes (K, M, B).
    """
    if number >= 1_000_000_000:
        return f"{number // 1_000_000_000}B"
    elif number >= 1_000_000:
        return f"{number // 1_000_000}M"
    elif number >= 1_000:
        return f"{number // 1_000}K"
    else:
        return str(number)


def calc():
    
    global cache
    current_time = time.time()

    

    # Serve cached data if still fresh
    if cache["data"]!=None and (current_time - cache["timestamp"]) < 120:

        
        return cache["data"]
    

            



    spore_address_avax = get_checksum_address(avax_tokens["spore"]["address"][43114])
    wavax_address = get_checksum_address(avax_tokens["wavax"]["address"][43114])
    
    spore_balance = get_balance(avax_web3, spore_address_avax, avax_LP, spore_abi)
    wavax_balance = get_balance(avax_web3, wavax_address, avax_LP, spore_abi)
    avax_usdt_price = fetch_asset_price("avalanche-2")


    spore_price_avax = (wavax_balance * avax_usdt_price) / (spore_balance * Decimal(1e3))

    liquidity_avax = wavax_balance * avax_usdt_price * 2

    spore_address_bnb = get_checksum_address(bsc_tokens["spore"]["address"][56])
    wbnb_address = get_checksum_address(bsc_tokens["wbnb"]["address"][56])

    spore_balance_bsc = get_balance(bsc_web3, spore_address_bnb, bsc_LP, spore_abi)
    bnb_balance = get_balance(bsc_web3, wbnb_address, bsc_LP, spore_abi)
    bsc_usdt_price = fetch_asset_price("binancecoin")

    bsc_spore_price = (bnb_balance * bsc_usdt_price) / (spore_balance_bsc * Decimal(1e3))

    liquidity_bnb = bnb_balance * bsc_usdt_price * 2


    percent_liquidity_avax= (liquidity_avax / (liquidity_avax + liquidity_bnb)) * 100
    percent_liquidity_bnb = (liquidity_bnb / (liquidity_avax + liquidity_bnb)) * 100

    percent_difference_raw = ((spore_price_avax - (bnb_balance * bsc_usdt_price) / (spore_balance_bsc * Decimal(1e3))) / spore_price_avax) * 100

    # formatted_diff = "{:.2f}%".format(abs(price_diff))

    percent_difference = "{:.2f}".format(abs(percent_difference_raw))


    market_cap = fetch_market_cap("spore")

    if market_cap == "0":
        #open file and get last timestamp
        data = read_price_indexing_file()
        last_timestamp = data["last_timestamp"]
        if current_time - float(last_timestamp) < 120:
            # do not return the last_timestam
            data.pop("last_timestamp")
            return data
    


    formatted_liquidity_avax = format_large_number(liquidity_avax/10**9)
    formatted_liquidity_bnb = format_large_number(liquidity_bnb/10**9)

    # Save updated data
    updated_data = {
        "AvaxSporePrice": format(spore_price_avax, '.8f'),
        "BscSporePrice": format(bsc_spore_price/10**6, '.8f'),
        "PriceDiff": percent_difference,
        "MarketCap": market_cap,
        "LiquidityAvax": formatted_liquidity_avax,
        "LiquidityBnb": formatted_liquidity_bnb,
        "PercentLiquidityAvax": format(percent_liquidity_avax, '.2f'),
        "PercentLiquidityBnb": format(percent_liquidity_bnb, '.2f')
    }



    # Update cache
    cache["data"] = updated_data
    cache["timestamp"] = current_time

    # add timestamp updated data
    updated_data["last_timestamp"] = current_time
    write_price_indexing_file(updated_data)



    return {
        "AvaxSporePrice": format(spore_price_avax*Decimal(1e6), '.8f'),
        "BscSporePrice": format(bsc_spore_price*Decimal(1e6), '.8f'),
        "PriceDiff": percent_difference,
        "MarketCap": market_cap,
        "LiquidityAvax": formatted_liquidity_avax,
        "LiquidityBnb": formatted_liquidity_bnb,
        "PercentLiquidityAvax": format(percent_liquidity_avax, '.2f'),
        "PercentLiquidityBnb": format(percent_liquidity_bnb, '.2f')

    }

