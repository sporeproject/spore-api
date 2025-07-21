


import psycopg2, os, uuid, time
from dotenv import load_dotenv
from web3.auto import w3
from eth_account.messages import encode_defunct

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
    conn.commit()
    conn.close()


def initialize_connection():
    try:
        conn = psycopg2.connect(
            database=os.getenv("DATABASE_NAME", "spore_db"),
            host=os.getenv("host", "localhost"),
            user=os.getenv("user", "postgres"),
            password=os.getenv("password", ""),
            port=os.getenv("port", "5432")
        )
        return conn
    except psycopg2.Error as e:
        print("Unable to connect to the database")
        print(e.pgerror)
        print(e.diag.message_detail)
        return False


def create_challenge(wallet):
    conn = initialize_connection()
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
