import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import random
import string

load_dotenv()

DB_URL = os.getenv('DB_URL')

def get_db_connection():
    return psycopg2.connect(DB_URL, sslmode='require', cursor_factory=RealDictCursor)

def create_tables():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id TEXT UNIQUE,
                username TEXT,
                invite_code TEXT UNIQUE,
                balance INTEGER DEFAULT 1000,
                inviter_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建游戏历史表
        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_histories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                bet_amount INTEGER,
                result TEXT,
                profit INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')    

        # 创建游戏待对战表
        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_history (
                id SERIAL PRIMARY KEY,
                creator_id INTEGER REFERENCES users(id),
                joiner_id INTEGER REFERENCES users(id),
                bet_amount INTEGER,
                creator_score INTEGER,
                joiner_score INTEGER,
                winner_id INTEGER REFERENCES users(id),
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    conn.commit()
    conn.close()

def get_user_by_telegram_id(telegram_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
        user = cur.fetchone()
    conn.close()
    return user
def get_invited_users(user_id):
       # 实现获取邀请用户的逻辑
       pass

def calculate_invite_earnings(user_id):
       # 实现计算邀请收益的逻辑
       pass
def get_user_by_invite_code(invite_code):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE invite_code = %s", (invite_code,))
            user = cur.fetchone()
        return user
    except psycopg2.Error as e:
        print(f"Error fetching user by invite code: {e}")
        return None
    finally:
        conn.close()
def get_user_game_history(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM game_history 
                WHERE creator_id = %s OR joiner_id = %s 
                ORDER BY created_at DESC
            """, (user_id, user_id))
            history = cur.fetchall()
        return history
    finally:
        conn.close()
def create_user(telegram_id, username, inviter_id=None):
    conn = get_db_connection()
    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (telegram_id, username, invite_code, inviter_id, balance) VALUES (%s, %s, %s, %s, 1000) RETURNING *",
                (telegram_id, username, invite_code, inviter_id)
            )
            new_user = cur.fetchone()
        conn.commit()
        return new_user
    except psycopg2.Error as e:
        print(f"Error creating user: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()
def create_tables():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id TEXT UNIQUE,
                username TEXT,
                invite_code TEXT UNIQUE,
                balance INTEGER DEFAULT 1000,
                inviter_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    conn.close()

# 在主函数中调用这个函数
if __name__ == '__main__':
    create_tables()

def update_user_balance(telegram_id, amount):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET balance = balance + %s WHERE telegram_id = %s", (amount, telegram_id))
    conn.commit()
    conn.close()

def add_game_history(game_id, player_a_id, player_a_score, player_b_id, player_b_score, winner_id, bet_amount, win_amount):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO game_history (game_id, player_a_id, player_a_score, player_b_id, player_b_score, winner_id, bet_amount, win_amount)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (game_id, player_a_id, player_a_score, player_b_id, player_b_score, winner_id, bet_amount, win_amount))
    conn.commit()
    cur.close()
    conn.close()

def get_user_game_history(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT * FROM game_history 
        WHERE player_a_id = %s OR player_b_id = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, (user_id, user_id))
    history = cur.fetchall()
    cur.close()
    conn.close()
    return history

# 初始化数据库
create_tables()

# 创建官方账户（如果不存在）
def ensure_official_account():
    official_user = get_user_by_telegram_id("project_account_id")
    if not official_user:
        create_user("project_account_id", "OfficialAccount")
        print("Official account created")
    else:
        print("Official account already exists")

ensure_official_account()