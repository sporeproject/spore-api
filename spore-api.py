import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
import spore_api_utils as api_utils
import spore_db_utils as db_utils

from cmc_api import handler  # Import the function from cmc_api.py
    
app = Flask(__name__)
CORS(app, support_credentials=True)

@app.route('/')
@cross_origin(supports_credentials=True)
def hello():
    return jsonify({'success': 'ok'})

@app.route('/avax-holders',methods=['GET'])
@cross_origin(supports_credentials=True)
def avax_holders():
    return '2082'

@app.route('/contributors',methods=['GET'])
@cross_origin(supports_credentials=True)
def current_contributors():
    #open json file containing contributors
    with open('contributors.json') as json_file:
        json_data = json.load(json_file)
        return jsonify(json_data)

@app.route('/last-indexed',methods=['GET'])
@cross_origin(supports_credentials=True)
def last_indexed():
    #you will return a code 502 if the database is not connected
    if not api_utils.verify_db_connection():
        return jsonify({'error': 'Database not connected'}), 502
    nft_buys_last_indexed, nft_prices_last_indexed = api_utils.last_indexed_nft_control()
    if nft_buys_last_indexed == 0 and nft_prices_last_indexed == 0:
        return jsonify({'error': 'No data indexed yet'}), 204
    return jsonify({'nft_buys_last_indexed': nft_buys_last_indexed, 'nft_prices_last_indexed': nft_prices_last_indexed})

@app.route('/api', methods=['GET'])  # New route for CoinMarketCap data
@cross_origin(supports_credentials=True)
def cmc_api():
    try:
        q = request.args.get('q')
        res= handler(q)
        if res:
            return res
        else:
            return jsonify({'error': 'Invalid request1'}), 500
    except Exception as e:
        print (f"Error: {jsonify(e)}")
        return jsonify({'error': 'Invalid request2'}), 500
    
@app.route('/nft/get_total_volume',methods=['GET'])
@cross_origin(supports_credentials=True)
def get_total_volume():
    if not api_utils.verify_db_connection():
        return jsonify({'error': 'Database not connected'}), 502
    total_volume = db_utils.nft_get_total_volume()
    if total_volume == 0:
        return jsonify({'error': 'No data indexed yet'}), 204
    return jsonify({'total_volume': total_volume})

@app.route('/nft/get_floor_price',methods=['GET'])
@cross_origin(supports_credentials=True)
def get_floor_price():
    if not api_utils.verify_db_connection():
        return jsonify({'error': 'Database not connected'}), 502
    floor_price = db_utils.nft_get_floor_price()
    if floor_price == 0:
        return jsonify({'error': 'No data indexed yet'}), 204
    return jsonify({'floor_price': floor_price})

@app.route('/nft/get_last_sale',methods=['GET'])
@cross_origin(supports_credentials=True)
def get_last_sale():
    if not api_utils.verify_db_connection():
        return jsonify({'error': 'Database not connected'}), 502
    last_sale = db_utils.nft_get_last_sale()
    if last_sale == 0:
        return jsonify({'error': 'No data indexed yet'}), 204
    return jsonify({'last_sale': last_sale})

@app.route('/nft/update_nft_db',methods=['GET'])
@cross_origin(supports_credentials=True)
def update_nft_db():
    if not api_utils.verify_db_connection():
        return jsonify({'error': 'Database not connected'}), 502
    db_utils.index_nft_price_data()
    db_utils.index_nft_bought_data()
    return jsonify({'success': 'NFT data updating', 'status': '202'})


@app.route('/nft/get_data',methods=['GET'])
@cross_origin(supports_credentials=True)
def get_nft_data():
    if not api_utils.verify_db_connection():
        return jsonify({'error': 'Database not connected'}), 502
    nft_data = db_utils.nft_get_data()
    if nft_data == 0:
        return jsonify({'error': 'No data indexed yet'}), 204
    return jsonify(nft_data)




if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5001))
    app.run(host='127.0.0.1', port=port)

