import os

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


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5001))
    app.run(host='127.0.0.1', port=port)

    