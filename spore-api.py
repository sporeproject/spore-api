import os
import json
from flask import Flask, jsonify
from flask_cors import CORS, cross_origin
import spore_api_utils as api_utils


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
    

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5001))
    app.run(host='127.0.0.1', port=port)

    