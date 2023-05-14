import os

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/avax-holders',methods=['GET'])
def avax_holders():
    response = Flask.jsonify({'avax-holders': '6000'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5001))
    app.run(host='127.0.0.1', port=port)

    