import os, time, requests
import json
from web3 import Web3
from spore_db_utils import initialize_connection
import requests

import psycopg2, os, uuid, time
from dotenv import load_dotenv
from web3.auto import w3
from eth_account.messages import encode_defunct
from flask import jsonify
from spore_db_utils import initialize_connection    
load_dotenv()

SESSION_DURATION = 15 * 60  # 15 minutes

def init_login_tables():
    conn = initialize_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS ipfs_users (
            wallet VARCHAR(42) PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ipfs_sessions (
            session_id UUID PRIMARY KEY,
            wallet VARCHAR(42) REFERENCES ipfs_users(wallet) ON DELETE CASCADE,
            challenge TEXT,
            expires_at BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    
    """)
    c.execute("""
               CREATE TABLE IF NOT EXISTS ipfs_files (
                id SERIAL PRIMARY KEY,
                wallet VARCHAR(42) REFERENCES ipfs_users(wallet) ON DELETE CASCADE,
                cid VARCHAR(64) NOT NULL,
                filename VARCHAR(256),
                size_bytes BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
    """)
    
    conn.commit()
    conn.close()


def create_challenge(wallet):
    init_login_tables()
    conn = initialize_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    c = conn.cursor()

    c = conn.cursor()
    nonce = uuid.uuid4().hex
    message = f"Login to Spore at {int(time.time())}: {nonce}"

    # upsert user
    c.execute("""
        INSERT INTO ipfs_users (wallet) VALUES (%s)
        ON CONFLICT (wallet) DO NOTHING
    """, (wallet,))

    # store challenge
    c.execute("""
        INSERT INTO ipfs_sessions (session_id, wallet, challenge, expires_at)
        VALUES (%s, %s, %s, %s)
    """, (str(uuid.uuid4()), wallet, message, int(time.time()) + SESSION_DURATION))
    conn.commit()
    conn.close()
    return message


def verify_login(wallet, message, signature):
    conn = initialize_connection()
    c = conn.cursor()

    # find challenge
    c.execute("""
        SELECT session_id, challenge FROM ipfs_sessions
        WHERE wallet=%s AND expires_at > %s
        ORDER BY created_at DESC LIMIT 1
    """, (wallet, int(time.time())))
    row = c.fetchone()
    if not row:
        conn.close()
        return None  # no valid challenge found

    session_id, challenge = row

    if challenge != message:
        conn.close()
        return None

    # verify signature
    encoded = encode_defunct(text=message)
    recovered = w3.eth.account.recover_message(encoded, signature=signature).lower()
    if recovered != wallet.lower():
        conn.close()
        return None

    # extend session
    c.execute("""
        UPDATE ipfs_sessions SET expires_at=%s WHERE session_id=%s
    """, (int(time.time()) + SESSION_DURATION, session_id))
    conn.commit()
    conn.close()
    return session_id


def is_session_valid(session_id):
    conn = initialize_connection()
    c = conn.cursor()
    c.execute("""
        SELECT wallet FROM ipfs_sessions WHERE session_id=%s AND expires_at>%s
    """, (session_id, int(time.time())))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]  # wallet
    return None


def logoff(session_id):
    conn = initialize_connection()
    c = conn.cursor()
    c.execute("DELETE FROM ipfs_sessions WHERE session_id=%s", (session_id,))
    conn.commit()
    conn.close()
    return True

def ipfs_node_stats():
    print("hello here there")
    IPFS_URL = os.getenv("IPFS_INTERFACE", "http://ipfs.sporeproject.com:5001")
    print("IPFS URL", IPFS_URL)
    try:
        resp = requests.post(f"{IPFS_URL}/api/v0/repo/stat")
        resp.raise_for_status()
        data = resp.json()
        return {
            "repo_size": data.get("RepoSize"),
            "storage_max": data.get("StorageMax"),
            "num_objects": data.get("NumObjects"),
            "repo_path": data.get("RepoPath"),
            "version": data.get("Version"),
        }
    except Exception as e:
        print(f"Error getting IPFS stats: {e}")
        return None


def check_eligibility(wallet):
    if not wallet:
        return None

    wallet = Web3.to_checksum_address(wallet)

    with open("abi/spore_abi.json") as f:
        ERC20_ABI = json.load(f)

    with open("abi/nftv1_abi.json") as f:
        NFT_ABI = json.load(f)

    chains = [
        {
            "name": "avax",
            "rpc": "https://api.avax.network/ext/bc/C/rpc",
            "spore_address": "0x6e7f5C0b9f4432716bDd0a77a3601291b9D9e985",
            "nft_address": "0xc2457F6Eb241C891EF74E02CCd50E5459c2E28Ea"
        },
        {
            "name": "bsc",
            "rpc": "https://bsc-dataseed.binance.org",
            "spore_address": "0x33A3d962955A3862C8093D1273344719f03cA17C",
            "nft_address": None  # replace with BSC NFT if needed
        }
    ]

    total_spore = 0
    total_nft = 0
    eligible = False
    details = {}

    for chain in chains:
        try:
            w3 = Web3(Web3.HTTPProvider(chain["rpc"]))
            spore_contract = w3.eth.contract(
                address=Web3.to_checksum_address(chain["spore_address"]),
                abi=ERC20_ABI
            )
            spore_balance = spore_contract.functions.balanceOf(wallet).call()
            total_spore += spore_balance

            nft_balance = 0
            if chain["nft_address"]:
                nft_contract = w3.eth.contract(
                    address=Web3.to_checksum_address(chain["nft_address"]),
                    abi=NFT_ABI
                )
                nft_balance = nft_contract.functions.balanceOf(wallet).call()
                total_nft += nft_balance

            details[chain["name"]] = {
                "spore_balance": spore_balance,
                "nft_balance": nft_balance
            }

            if spore_balance > 0 or nft_balance > 0:
                eligible = True

        except Exception as e:
            print(f"Error checking {chain['name']}: {e}")
            details[chain["name"]] = {
                "spore_balance": "0",
                "nft_balance": 0,
                "error": str(e)
            }

    # Convert total_spore to trillions
    # NOTE: Spore is 9 decimals (like gwei) so to show "T" we divide by 1e12
    total_spore_T = round(total_spore / 1e21, 2)

    return {
        "wallet": wallet,
        "eligible": eligible,
        "spore_balance": total_spore,
        "nft_balance": total_nft,
        "total_spore_balance": str(total_spore),
        "total_spore_balance_T": f"{total_spore_T}T",
        "details": details
    }


def upload_and_pin_file(session_id, file_path, filename=None):
    """
    Upload and pin a file to local IPFS, record in DB.

    Args:
        session_id (str): Session ID to validate
        file_path (str): Path to uploaded file on disk
        filename (str): Optional display filename

    Returns:
        dict: Result including CID, URL, or error
    """
    wallet = is_session_valid(session_id)
    if not wallet:
        return {"error": "Invalid session"}

    # Check quota
    user_info = get_user_info(session_id)
    if user_info["used"] >= user_info["quota"]:
        return {"error": "Quota exceeded"}

    # Use provided filename or fallback to path basename
    if not filename:
        filename = os.path.basename(file_path)

    ipfs_api_url = os.getenv("IPFS_INTERFACE", "http://127.0.0.1:5001")

    # Upload and pin to IPFS
    try:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f)}
            resp = requests.post(
                f"{ipfs_api_url}/api/v0/add",
                files=files,
                params={"pin": "true"}
            )
            resp.raise_for_status()
            result = resp.json()
            cid = result["Hash"]
            size_bytes = os.path.getsize(file_path)
    except Exception as e:
        print(f"IPFS upload error: {e}")
        return {"error": "Failed to upload & pin on IPFS"}

    # Record in DB
    try:
        conn = initialize_connection()
        with conn:
            with conn.cursor() as c:
                c.execute(
                    """
                    INSERT INTO ipfs_files (wallet, cid, filename, size_bytes, created_at)
                    VALUES (%s, %s, %s, %s, to_timestamp(%s))
                    """,
                    (wallet, cid, filename, size_bytes, int(time.time()))
                )
    except Exception as e:
        print(f"DB insert error: {e}")
        return {"error": "Failed to record in DB"}

    # Return result
    return {
        "wallet": wallet,
        "cid": cid,
        "filename": filename,
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / 1024 / 1024, 2),
        "url": f"https://ipfs.sporeproject.com/ipfs/{cid}"
    }

def unpin_file_by_cid(session_id, cid):
    """
    Unpin a file from local IPFS by its CID.

    Args:
        session_id (str): Session ID to validate
        cid (str): CID of the file to unpin

    Returns:
        dict: Result or error
    """
    wallet = is_session_valid(session_id)
    if not wallet:
        return {"error": "Invalid session"}

    ipfs_api_url = os.getenv("IPFS_INTERFACE", "http://127.0.0.1:5001")

    # Unpin from IPFS
    try:
        resp = requests.post(
            f"{ipfs_api_url}/api/v0/pin/rm",
            params={"arg": cid}
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"IPFS unpin error: {e}")
        return {"error": "Failed to unpin file from IPFS"}

    # Optionally remove from DB
    try:
        conn = initialize_connection()
        with conn:
            with conn.cursor() as c:
                c.execute(
                    """
                    DELETE FROM ipfs_files
                    WHERE wallet=%s AND cid=%s
                    """,
                    (wallet, cid)
                )
    except Exception as e:
        print(f"DB delete error: {e}")
        return {"error": "Failed to remove record from DB"}

    return {"wallet": wallet, "cid": cid, "unpinned": True}


def get_user_info(session_id):

    wallet = is_session_valid(session_id)
    if not wallet:
        return None  # invalid session

    data = {
        "wallet": wallet,
        "used": 0,
        "quota": 100,  # quota in MB
        "files": []
    }

    conn = None
    try:
        conn = initialize_connection()
        if conn:
            c = conn.cursor()
            c.execute("""
                SELECT cid, filename, size_bytes
                FROM ipfs_files
                WHERE wallet = %s
                ORDER BY created_at DESC
            """, (wallet,))
            rows = c.fetchall()
            total_used = 0
            files = []
            for cid, filename, size_bytes in rows:
                files.append({
                    "cid": cid,
                    "filename": filename,
                    "size": size_bytes
                })
                total_used += size_bytes

            data["files"] = files
            data["used"] = round(total_used / 1024 / 1024, 2)  # bytes → MB
    finally:
        if conn:
            conn.close()

    # Get eligibility verdict
    eligibility = check_eligibility(wallet)
    if eligibility:
        data.update({
            "eligible": eligibility["eligible"],
            "spore_balance": eligibility["spore_balance"],
            "total_spore_balance_T": eligibility["total_spore_balance_T"],
            "nft_balance": eligibility["nft_balance"],
        })
    else:
        data.update({
            "eligible": False,
            "spore_balance": "0",
            "nft_balance": 0,
            "total_spore_balance_T":0
        })
    
    # Add node-wide info
    node_stats = ipfs_node_stats()
    if node_stats:
        data.update({
            "repo_size_mb": round(node_stats["repo_size"] / 1024 / 1024, 2),
            "storage_max_mb": round(node_stats["storage_max"] / 1024 / 1024, 2),
            "num_objects": node_stats["num_objects"]
        })
    else:
        data["node"] = {
            "error": "Unable to fetch node stats"
        }

    print(data)
    return data