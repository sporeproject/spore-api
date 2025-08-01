import os
import json
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS, cross_origin
import spore_api_utils as api_utils
import spore_db_utils as db_utils
import spore_price_utils as price_utils
from cmc_api import handler  # Import the function from cmc_api.py
from ipfs_utils import create_challenge, verify_login, is_session_valid, logoff, get_user_info, upload_and_pin_file, unpin_file_by_cid
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, support_credentials=True)

@app.route('/')
@cross_origin(supports_credentials=True)
def hello():
    return jsonify({'success': 'ok'})

@app.route('/avax-holders',methods=['GET'])
@cross_origin(supports_credentials=True)
def avax_holders():
    origin = request.headers.get('Origin', '')
    if 'spore.earth' in origin:
        return 'sporeproject.com is the official domain of Spore. Beware of impersonators.'
    return '5336'



@app.route('/contributors',methods=['GET'])
@cross_origin(supports_credentials=True)
def current_contributors():
    origin = request.headers.get('Origin', '')
    if 'spore.earth' in origin:
        return jsonify('sporeproject.com is the official domain of Spore. Beware of impersonators.')
    #open json file containing contributors
    with open('contributors.json') as json_file:
        json_data = json.load(json_file)
        return jsonify(json_data)

@app.route('/token/prices',methods=['GET'])
@cross_origin(supports_credentials=True)
def get_token_prices():
    origin = request.headers.get('Origin', '')
    if 'spore.earth' in origin:
        return False    
    data=price_utils.calc()
    return jsonify(data)

@app.route('/last-indexed',methods=['GET'])
@cross_origin(supports_credentials=True)
def last_indexed():
    origin = request.headers.get('Origin', '')
    if 'spore.earth' in origin:
        return jsonify('sporeproject.com is the official domain of Spore. Beware of impersonators.')
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
    origin = request.headers.get('Origin', '')
    if 'spore.earth' in origin:
        return jsonify('sporeproject.com is the official domain of Spore. Beware of impersonators.')
    if not api_utils.verify_db_connection():
        return jsonify({'error': 'Database not connected'}), 502
    total_volume = db_utils.nft_get_total_volume()
    if total_volume == 0:
        return jsonify({'error': 'No data indexed yet'}), 204
    return jsonify({'total_volume': total_volume})

@app.route('/nft/get_floor_price',methods=['GET'])
@cross_origin(supports_credentials=True)
def get_floor_price():
    origin = request.headers.get('Origin', '')
    if 'spore.earth' in origin:
        return jsonify('sporeproject.com is the official domain of Spore. Beware of impersonators.')
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
    (indexing_in_progress, block_started, status) = db_utils.get_nft_indexing()
    current_block = db_utils.get_ava_latest_block()
    try:
        q = request.args.get('q')
        req_response=500
        if q == "consult":
            if not indexing_in_progress and block_started+120<current_block:
                status = "reload"
                db_utils.set_nft_indexing_json(False, 0, status)
            (indexing_in_progress, block_started, status) = db_utils.get_nft_indexing()
            json_response = {
                'indexing_in_progress': indexing_in_progress,
                'block_started': block_started,
                'current_block': current_block,
                'status': status
                }
            req_response=200

        else:
            thread_response= db_utils.nft_update_db()
            (indexing_in_progress, block_started, status) = db_utils.get_nft_indexing()
            json_response = {
            'indexing_in_progress': indexing_in_progress,
            'block_started': block_started,
            'current_block': current_block,
            'status': status
            }
            req_response=thread_response['http_status']
        return jsonify(json_response), req_response
    except Exception as e:
        print (f"Error: {jsonify(e)}")
        return jsonify({'error': 'Invalid request2'}), 500


@app.route('/nft/get_data',methods=['GET'])
@cross_origin(supports_credentials=True)
def get_nft_data():
    if not api_utils.verify_db_connection():
        return jsonify({'error': 'Database not connected'}), 502
    try:
        q = request.args.get('q')
        nft_data= db_utils.nft_get_data(q)
        return nft_data
    except Exception as e:
        print (f"Error: {jsonify(e)}")
        return jsonify({'error': 'Invalid request2'}), 500



@app.route("/ipfs/challenge")
def api_challenge():
    wallet = request.args.get("wallet", "").lower()
    message = create_challenge(wallet)
    return jsonify({"message": message})

@app.route("/ipfs/login", methods=["POST"])
def api_login():
    data = request.json
    session_id = verify_login(data["wallet"].lower(), data["message"], data["signature"])
    if session_id:
        return jsonify({"session_id": session_id})
    return jsonify({"error": "Invalid login"}), 401

@app.route("/ipfs/session")
def api_session():
    session_id = request.headers.get("Authorization", "").replace("Bearer ", "")
    wallet = is_session_valid(session_id)
    if wallet:
        return jsonify({"valid": True, "wallet": wallet})
    return jsonify({"valid": False}), 401

@app.route("/ipfs/user/info")
def ipfs_user_info():
    session_id = request.headers.get("Authorization", "").replace("Bearer ", "")
    data = get_user_info(session_id)
    if not data:
        return jsonify({"error": "Invalid session"}), 401
    return jsonify(data)

@app.route("/ipfs/logoff", methods=["POST"])
def api_logoff():
    session_id = request.headers.get("Authorization", "").replace("Bearer ", "")
    logoff(session_id)
    return jsonify({"logged_off": True})


@app.route("/ipfs/upload", methods=["POST"])
def ipfs_upload():
    session_id = request.headers.get("Authorization", "").replace("Bearer ", "")
    wallet = is_session_valid(session_id)
    if not wallet:
        return jsonify({"error": "Invalid session"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)

    # Save file to temp file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        file.save(tmp)
        tmp_path = tmp.name

    result = upload_and_pin_file(session_id, tmp_path, filename=filename)

    # Clean up temp file
    os.unlink(tmp_path)

    if "error" in result:
        return jsonify(result), 400

    return jsonify(result), 200

@app.route("/ipfs/unpin", methods=["POST"])
def ipfs_unpin():
    session_id = request.headers.get("Authorization", "").replace("Bearer ", "")
    wallet = is_session_valid(session_id)
    if not wallet:
        return jsonify({"error": "Invalid session"}), 401

    data = request.get_json()
    cid = data.get("cid")
    if not cid:
        return jsonify({"error": "Missing CID"}), 400

    result = unpin_file_by_cid(session_id, cid)
    if "error" in result:
        return jsonify(result), 400

    return jsonify(result), 200

if os.getenv("ENVIRONMENT", "production"):
    if __name__ == '__main__':
        # Bind to PORT if defined, otherwise default to 5000.
        port = int(os.environ.get('PORT', 5001))
        app.run(host='127.0.0.1', port=port)
        app.env = 'production'  # Set the environment to development

else:
    if __name__ == '__main__':
        # Bind to PORT if defined, otherwise default to 5000.s
        port = int(os.environ.get('PORT', 5001))
        app.debug = True  # Enable debugging
        app.run(host='127.0.0.1', port=port)