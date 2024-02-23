from web3 import Web3
import json

# Load ABI
with open('./abi/spore_abi.json') as f:
    abi_erc20 = json.load(f)



tokens = [
    {
        'bsc': '0x33A3d962955A3862C8093D1273344719f03cA17C',
        'id': '0x6e7f5C0b9f4432716bDd0a77a3601291b9D9e985',
        'avaburn': '0x000000000000000000000000000000000000dEaD',
        'avabridge': '0x1aFCEF48379ECad5a6D790cE85ad1c87458C0f07'
    }
]


def populate(token):
    # Connect to networks

    ava = Web3(Web3.HTTPProvider('https://avalanche.drpc.org'))

    contract = ava.eth.contract(address=token['id'], abi=abi_erc20)
    sporeAva = {}
    sporeAva['id']=token['id']
    sporeAva['totalSupply'] = int(contract.functions.totalSupply().call())
    sporeAva['decimals'] = int(contract.functions.decimals().call())
    sporeAva['name'] = contract.functions.name().call()
    sporeAva['symbol'] = contract.functions.symbol().call()
    sporeAva['owner'] = contract.functions.owner().call()
    sporeAva['totalFees'] = contract.functions.totalFees().call() / 1e18
    sporeAva['maxSupply'] = sporeAva['totalSupply'] / 10 ** sporeAva['decimals']

    return sporeAva

def handler(req):
    # try:
        spore = populate(tokens[0])
        # spore = find_token(tokens, { 'key': 'symbol', 'value': 'spore' })
        bsc = Web3(Web3.HTTPProvider('https://bsc-dataseed1.binance.org'))
        ava = Web3(Web3.HTTPProvider('https://avalanche.drpc.org'))
        contract_bsc = bsc.eth.contract(address=tokens[0]['bsc'], abi=abi_erc20)
        contract_ava = ava.eth.contract(address=tokens[0]['id'], abi=abi_erc20)
        bscBurned = contract_bsc.functions.balanceOf(tokens[0]['bsc']).call()
        avaBurned = contract_ava.functions.balanceOf(tokens[0]['avaburn']).call()
        avaxbridge = contract_ava.functions.balanceOf(tokens[0]['avabridge']).call()
        bsctotalsupply = contract_bsc.functions.totalSupply().call()
        report = {
            'bscBurned': bscBurned / 10 ** spore['decimals'],
            'avaBurned': avaBurned / 10 ** spore['decimals'],
            'avaxbridge': avaxbridge / 10 ** spore['decimals'],
            'bsctotalsupply': bsctotalsupply / 10 ** spore['decimals']
        }

        report['totalSupply'] = spore['maxSupply'] - (report['avaBurned'] + report['avaxbridge']) + (report['bsctotalsupply'] - report['bscBurned'])
        report['supplyavax'] = spore['maxSupply'] - report['avaBurned'] - report['avaxbridge']
        report['supplybsc'] = report['bsctotalsupply'] - report['bscBurned']
        report['circulatingSupply'] = report['supplyavax'] + report['supplybsc']
        spore.update(report)

        del spore['decimals']
        del spore['owner']

        spore['name'] = spore['name'].replace(".Finance", "") if len(spore['name']) > 4 else spore['name']


        if not req:
            return spore
        else:
            try:
                for key in spore.keys():
                    if key.lower() == req.lower():
                        if type(spore[key]) == str:
                            return spore[key]
                        elif type(spore[key]) == float:
                            return str(int(spore[key]))
                return spore
            except:
                print("error on key value pairs")
                return spore
