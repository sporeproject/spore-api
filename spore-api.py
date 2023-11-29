import os
import json
from flask import Flask, jsonify
from flask_cors import CORS, cross_origin

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

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5001))
    app.run(host='127.0.0.1', port=port)

    