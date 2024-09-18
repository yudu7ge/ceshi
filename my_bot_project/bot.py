import os
import logging
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
import random
import string
import uuid
import urllib.parse
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DB_URL = os.getenv('DB_URL')

if not BOT_TOKEN:
    raise ValueError("在 .env 文件中未找到 BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 检查 updated_at 列是否存在，如果不存在则添加
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='updated_at'")
        if cur.fetchone() is None:
            cur.execute("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        cur.execute('''
    CREATE TABLE IF NOT EXISTS game_history (
        id SERIAL PRIMARY KEY,
        game_id TEXT,
        player_a_id INTEGER REFERENCES users(id),
        player_b_id INTEGER REFERENCES users(id),
        bet_amount INTEGER,
        player_a_score INTEGER,
        player_b_score INTEGER,
        winner_id INTEGER REFERENCES users(id),
        win_amount INTEGER,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
    conn.commit()
    conn.close()

def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
        return user
    except psycopg2.Error as e:
        logger.error(f"Error fetching user by ID: {e}")
        return None
    finally:
        conn.close()

def get_user_by_telegram_id(telegram_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
        user = cur.fetchone()
    conn.close()
    return user

def get_user_by_invite_code(invite_code):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE UPPER(invite_code) = UPPER(%s)", (invite_code,))
            user = cur.fetchone()
        return user
    except psycopg2.Error as e:
        logger.error(f"Error fetching user by invite code: {e}")
        return None
    finally:
        conn.close()

def create_user(telegram_id, username, inviter_id=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO users (telegram_id, username, inviter_id, balance, created_at, updated_at) 
                VALUES (%s, %s, %s, 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING *""",
                (telegram_id, username, inviter_id)
            )
            new_user = cur.fetchone()
        conn.commit()
        return new_user
    except psycopg2.Error as e:
        logger.error(f"Error creating user: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def generate_invite_code(user_id):
    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET invite_code = %s WHERE id = %s",
                (invite_code, user_id)
            )
        conn.commit()
        return invite_code
    except psycopg2.Error as e:
        logger.error(f"Error generating invite code: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def update_user_balance(telegram_id, amount, is_invite_earning=False):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if is_invite_earning:
                cur.execute("""
                    UPDATE users 
                    SET balance = balance + %s, 
                        invite_earnings = invite_earnings + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = %s
                """, (amount, amount, telegram_id))
            else:
                cur.execute("""
                    UPDATE users 
                    SET balance = balance + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = %s
                """, (amount, telegram_id))
        conn.commit()
    except psycopg2.Error as e:
        logger.error(f"Error updating user balance: {e}")
        conn.rollback()
    finally:
        conn.close()

def add_game_history(game_id, player_a_id, player_b_id, bet_amount, player_a_score, player_b_score, winner_id, win_amount, status):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO game_history (game_id, player_a_id, player_b_id, bet_amount, player_a_score, player_b_score, winner_id, win_amount, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (game_id, player_a_id, player_b_id, bet_amount, player_a_score, player_b_score, winner_id, win_amount, status))
        conn.commit()
        logger.info(f"Added game history: game_id={game_id}, player_a_id={player_a_id}, player_b_id={player_b_id}, status={status}")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error adding game history: {e}")
    finally:
        conn.close()

async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # 清理游戏数据
    if 'game_id' in context.user_data:
        game_id = context.user_data['game_id']
        if game_id in context.bot_data.get('pending_games', {}):
            del context.bot_data['pending_games'][game_id]

    # 重置用户数据
    context.user_data.clear()
    context.user_data['game_state'] = 'idle'

    await query.edit_message_text("游戏已取消。", reply_markup=create_main_menu())

def get_user_game_history(user_id, status='completed', limit=5, offset=0):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT gh.*, 
                       ua.username as player_a_username, 
                       ub.username as player_b_username
                FROM game_history gh
                LEFT JOIN users ua ON gh.player_a_id = ua.id
                LEFT JOIN users ub ON gh.player_b_id = ub.id
                WHERE (gh.player_a_id = %s OR gh.player_b_id = %s)
                  AND gh.status = %s
                ORDER BY gh.created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, user_id, status, limit, offset))
            game_history = cur.fetchall()
        return game_history
    except psycopg2.Error as e:
        logger.error(f"Error fetching user game history: {e}")
        return []
    finally:
        conn.close()

def get_invited_users(user_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE inviter_id = %s", (user_id,))
        invited_users = cur.fetchall()
    conn.close()
    return invited_users

def calculate_invite_earnings(user_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT SUM(win_amount) * 0.07 as earnings
            FROM game_history
            JOIN users ON game_history.winner_id = users.id
            WHERE users.inviter_id = %s
        """, (user_id,))
        earnings = cur.fetchone()['earnings'] or 0
    conn.close()
    return earnings

def create_main_menu():
    keyboard = [
        [InlineKeyboardButton("🎮 开始游戏", callback_data='start_game')],
        [InlineKeyboardButton("📜 对战历史", callback_data='game_history')],
        [InlineKeyboardButton("🔗 邀约收益", callback_data='invite_earnings')],  # 修改这里
        [InlineKeyboardButton("💰 余额", callback_data='balance')],
        [InlineKeyboardButton("❓ 帮助", callback_data='help')]
    ]
    return InlineKeyboardMarkup(keyboard)

def update_user_info(telegram_id, username):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET username = %s, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = %s",
                (username, telegram_id)
            )
        conn.commit()
    except psycopg2.Error as e:
        logger.error(f"Error updating user info: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_game_share_button(game_id, bot_username):
    return InlineKeyboardButton(
        "分享这个游戏",
        url=f"https://t.me/share/url?url=https://t.me/{bot_username}?start={game_id}&text=来和我一起玩游戏吧！"
    )

def create_game_history_keyboard(has_more, page=0):
    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("上一页", callback_data=f"history_prev_{page}"))
    if has_more:
        keyboard.append(InlineKeyboardButton("下一页", callback_data=f"history_next_{page}"))
    keyboard.append(InlineKeyboardButton("刷新", callback_data=f"history_refresh_{page}"))
    keyboard.append(InlineKeyboardButton("返回主菜单", callback_data="main_menu"))
    return InlineKeyboardMarkup([keyboard])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "Unknown"
    update_user_info(telegram_id, username)
    user = get_user_by_telegram_id(telegram_id)
    
    if args and args[0]:
        game_id = args[0]
        if user:
            await join_game(update, context, game_id)
        else:
            context.user_data['pending_game_id'] = game_id
            await update.message.reply_text("请先注册，然后您将自动加入游戏。", reply_markup=create_main_menu())
    elif user:
        if 'pending_game_id' in context.user_data:
            await join_game(update, context, context.user_data['pending_game_id'])
            del context.user_data['pending_game_id']
        else:
            await update.message.reply_text(
                f"欢迎回来,{user['username']}！您的当前余额是：{user['balance']} 游戏币。",
                reply_markup=create_main_menu()
            )
    else:
        await update.message.reply_text("请输入邀请码完成注册,注册后可获得1000空投游戏币：", reply_markup=create_main_menu())
        context.user_data['awaiting_invite_code'] = True

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id: str) -> None:
    user = get_user_by_telegram_id(str(update.effective_user.id))
    game = context.bot_data.get('pending_games', {}).get(game_id)
    
    if not game:
        await update.message.reply_text("对不起，这个游戏已经结束或不存在。", reply_markup=create_main_menu())
        return

    if user['balance'] < game['bet_amount']:
        await update.message.reply_text("您的余额不足以加入这个游戏。", reply_markup=create_main_menu())
        return

    # 立即扣除下注金额
    update_user_balance(user['telegram_id'], -game['bet_amount'])

    creator = get_user_by_id(game['creator_id'])
    await update.message.reply_text(
        f"您已成功加入 @{creator['username']} 发起的 {game['bet_amount']} 游戏币的对决，"
        f"他的成绩是 {game['creator_score']}。\n"
        f"请发送三次骰子表情来尝试大过他吧！"
    )

    context.user_data['game_state'] = 'rolling_dice'
    context.user_data['game_id'] = game_id
    context.user_data['dice_count'] = 0
    context.user_data['total_score'] = 0
    context.user_data['bet_amount'] = game['bet_amount']

async def handle_invite_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'awaiting_invite_code' not in context.user_data or not context.user_data['awaiting_invite_code']:
        return

    telegram_id = str(update.message.from_user.id)
    username = update.message.from_user.username or "Unknown"
    invite_code = update.message.text.strip().upper()

    logger.info(f"Attempting to register user {telegram_id} with invite code {invite_code}")

    inviter = get_user_by_invite_code(invite_code)
    
    if not inviter:
        logger.error(f"Invalid invite code: {invite_code}")
        await update.message.reply_text("邀请码无效,请重新输入。")
        return

    try:
        new_user = create_user(telegram_id, username, inviter['id'])
        if new_user:
            logger.info(f"User {telegram_id} registered successfully")
            welcome_message = f"注册成功！您已通过 @{inviter['username']} 的邀请获得了1000游戏币。"
            await update.message.reply_text(welcome_message, reply_markup=create_main_menu())
            context.user_data['awaiting_invite_code'] = False
            
            if 'pending_game_id' in context.user_data:
                await join_game(update, context, context.user_data['pending_game_id'])
                del context.user_data['pending_game_id']
        else:
            logger.error(f"Failed to create user {telegram_id}")
            await update.message.reply_text("注册失败,请稍后重试或联系客服。")
    except Exception as e:
        logger.error(f"Error during user registration: {e}", exc_info=True)
        await update.message.reply_text("注册过程中发生错误,请稍后重试或联系客服。")

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = get_user_by_telegram_id(str(query.from_user.id))
    
    if user:
        await query.edit_message_text(f"您当前的余额是：{user['balance']} 游戏币。", reply_markup=create_main_menu())
    else:
        await query.edit_message_text("未找到您的账户信息，请先注册。", reply_markup=create_main_menu())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'start_game':
        await start_game(update, context)
    elif query.data == 'game_history':
        await show_game_history(update, context)
    elif query.data.startswith('history_'):
        _, action, page = query.data.split('_')
        page = int(page)
        if action == 'prev':
            await show_game_history(update, context, page - 1)
        elif action == 'next':
            await show_game_history(update, context, page + 1)
        elif action == 'refresh':
            await show_game_history(update, context, page)
    elif query.data == 'invite_earnings':
        await show_invite_earnings(update, context)
    elif query.data == 'balance':
        await show_balance(update, context)
    elif query.data == 'help':
        await show_help(update, context)
    elif query.data == 'cancel_game':
        await cancel_game(update, context)
    elif query.data == 'main_menu':
        await show_menu(update, context)
    else:
        await query.edit_message_text("未知的操作。", reply_markup=create_main_menu())

import html
import urllib.parse

async def show_game_history(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    user = get_user_by_telegram_id(str(user_id))
    
    logger.info(f"Showing game history for user: {user_id}, page: {page}")
    
    if not user:
        logger.warning(f"User not found: {user_id}")
        await update.effective_message.reply_text("请先注册后再查看游戏历史。", reply_markup=create_main_menu())
        return

    pending_games = get_user_pending_games(user['id'])
    completed_games = get_user_game_history(user['id'], status='completed', limit=5, offset=page*5)
    has_more = len(get_user_game_history(user['id'], status='completed', limit=1, offset=(page+1)*5)) > 0
    
    logger.info(f"Retrieved {len(completed_games)} completed games and {len(pending_games)} pending games for user: {user_id}")
    
    if not completed_games and not pending_games:
        logger.info(f"No game history found for user: {user_id}")
        await update.effective_message.reply_text("您还没有任何游戏记录。", reply_markup=create_main_menu())
        return

    try:
        # 待分享的对战消息
        if pending_games:
            pending_text = "🕒 待分享的对战：\n\n"
            pending_buttons = []
            for game in pending_games:
                invite_message = create_invite_message(user, game, context)
                invite_link = f"https://t.me/{context.bot.username}?start={game['game_id']}"
                pending_text += f"下注金额: {game['bet_amount']} 游戏币\n"
                pending_text += f"分享链接: {invite_link}\n\n"
                escaped_message = urllib.parse.quote(invite_message)
                pending_buttons.append([InlineKeyboardButton(
                    "分享这个游戏",
                    url=f"https://t.me/share/url?url={invite_link}&text={escaped_message}"
                )])
            
            await update.effective_message.reply_text(
                pending_text,
                reply_markup=InlineKeyboardMarkup(pending_buttons),
                disable_web_page_preview=True
            )

        # 已完成的对战消息
        completed_text = f"✅ 已完成的对战 (第 {page+1} 页)：\n\n"
        if completed_games:
            for game in completed_games:
                player_a_name = html.escape(game['player_a_username'] or "未知玩家")
                player_b_name = html.escape(game['player_b_username'] or "未知玩家")
                winner_name = player_a_name if game['winner_id'] == game['player_a_id'] else player_b_name
                completed_text += f"{player_a_name} vs {player_b_name}\n"
                completed_text += f"下注金额: {game['bet_amount']} 游戏币, 赢家: {winner_name}\n"
                completed_text += f"得分: {game['player_a_score']} - {game['player_b_score']}\n\n"
        else:
            completed_text += "暂无已完成的对战\n"

        history_keyboard = create_game_history_keyboard(has_more, page)
        await update.effective_message.reply_text(completed_text, reply_markup=history_keyboard)

    except Exception as e:
        logger.error(f"Error in show_game_history: {e}")
        await update.effective_message.reply_text("获取游戏历史时出错，请稍后再试。", reply_markup=create_main_menu())

def create_game_history_keyboard(has_more, page=0):
    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("上一页", callback_data=f"history_prev_{page}"))
    if has_more:
        keyboard.append(InlineKeyboardButton("下一页", callback_data=f"history_next_{page}"))
    keyboard.append(InlineKeyboardButton("刷新", callback_data=f"history_refresh_{page}"))
    keyboard.append(InlineKeyboardButton("返回主菜单", callback_data="main_menu"))
    return InlineKeyboardMarkup([keyboard])

def create_invite_message(user, game, context):
    invite_link = f"https://t.me/{context.bot.username}?start={game['game_id']}"
    return (
        f"@{html.escape(user['username'] or 'Unknown')} 发起了一个{game['bet_amount']}游戏币的挑战！\n"
        f"点击链接加入游戏：{invite_link}\n\n"
        f"快使用我的邀请码 {html.escape(user['invite_code'] or 'Unknown')} 获取1000代币空投！！"
    )

async def show_pending_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    user = get_user_by_telegram_id(str(user_id))
    
    pending_games = get_user_pending_games(user['id'])
    
    if not pending_games:
        await query.edit_message_text("您没有等待挑战的游戏。", reply_markup=create_main_menu())
        return
    if query.message.text != history_text:
        await query.edit_message_text(history_text, reply_markup=create_main_menu())
    else:
        await query.answer("游戏历史没有变化")
    history_text = "您的游戏历史：\n\n"
    message = "您的等待挑战游戏：\n\n"
    for game in pending_games:
        message += f"🕒 下注金额: {game['bet_amount']} 游戏币\n"
        message += f"   创建时间: {game['created_at']}\n"
        message += f"   邀请链接: https://t.me/{context.bot.username}?start={game['game_id']}\n"
        message += f"   [点击转发](tg://msg_url?url=https://t.me/{context.bot.username}?start={game['game_id']}&text={create_invite_message(user, game)})\n\n"

    keyboard = [
        [InlineKeyboardButton("返回", callback_data='game_history')],
        [InlineKeyboardButton("返回主菜单", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown', disable_web_page_preview=True)

async def show_completed_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    user = get_user_by_telegram_id(str(user_id))
    
    completed_games = get_user_completed_games(user['id'])
    
    if not completed_games:
        await query.edit_message_text("您没有已完成的游戏记录。", reply_markup=create_main_menu())
        return

    message = "您的游戏历史记录：\n\n"
    for game in completed_games:
        opponent = game['player_a_id'] == user['id'] and game['player_b_username'] or game['player_a_username']
        user_score = game['player_a_id'] == user['id'] and game['player_a_score'] or game['player_b_score']
        opponent_score = game['player_a_id'] == user['id'] and game['player_b_score'] or game['player_a_score']
        result = game['winner_id'] == user['id'] and "胜利" or "失败"
        
        message += f"🎮 对手: {opponent}\n"
        message += f"   下注金额: {game['bet_amount']} 游戏币\n"
        message += f"   得分: {user_score} - {opponent_score}\n"
        message += f"   结果: {result}\n"
        message += f"   时间: {game['created_at']}\n\n"

    keyboard = [
        [InlineKeyboardButton("返回", callback_data='game_history')],
        [InlineKeyboardButton("返回主菜单", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup)

def create_invite_message(user, game, context):
    invite_link = f"https://t.me/{context.bot.username}?start={game['game_id']}"
    return (
        f"@{user['username'] or 'Unknown'} 发起了一个{game['bet_amount']}游戏币的挑战！\n"
        f"点击链接加入游戏：{invite_link}\n\n"
        f"快使用我的邀请码 {user['invite_code'] or 'Unknown'} 获取1000代币空投！！"
    )

def get_user_pending_games(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM game_history
                WHERE player_a_id = %s AND player_b_id IS NULL AND status = 'pending'
                ORDER BY created_at DESC
            """, (user_id,))
            pending_games = cur.fetchall()
        return pending_games
    except psycopg2.Error as e:
        logger.error(f"Error fetching user pending games: {e}")
        return []
    finally:
        conn.close()

def get_user_completed_games(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT gh.*, 
                       ua.username as player_a_username, 
                       ub.username as player_b_username
                FROM game_history gh
                LEFT JOIN users ua ON gh.player_a_id = ua.id
                LEFT JOIN users ub ON gh.player_b_id = ub.id
                WHERE (gh.player_a_id = %s OR gh.player_b_id = %s)
                  AND gh.status = 'completed'
                ORDER BY gh.created_at DESC
                LIMIT 10
            """, (user_id, user_id))
            completed_games = cur.fetchall()
        return completed_games
    except psycopg2.Error as e:
        logger.error(f"Error fetching user completed games: {e}")
        return []
    finally:
        conn.close()

async def show_invite_earnings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = get_user_by_telegram_id(str(query.from_user.id))
    if user:
        if user['invite_code']:
            invite_code = user['invite_code']
            invited_users = get_invited_users(user['id'])
            
            message = f"您的邀请码是: {invite_code}\n"
            message += f"总邀约收益: {user.get('invite_earnings', 0)} 游戏币\n\n"  # 使用 get 方法，如果 'invite_earnings' 不存在，默认为 0
            message += "已邀请用户:\n"
            for invited_user in invited_users:
                message += f"- {invited_user['username']}\n"
        else:
            message = "您还没有邀请码。完成注册后即可获得专属邀请码。"
        
        await query.edit_message_text(message, reply_markup=create_main_menu())
    else:
        await query.edit_message_text("未找到您的账户信息，请先注册。", reply_markup=create_main_menu())
        
async def process_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 这里需要实现实际的充值逻辑
    deposit_successful = False  # 这应该根据实际充值结果来设置
    if deposit_successful:
        user = get_user_by_telegram_id(str(update.effective_user.id))
        if not user['invite_code']:
            invite_code = generate_invite_code(user['id'])
            await update.message.reply_text(f"充值成功！您的专属邀请码是: {invite_code}", reply_markup=create_main_menu())
        else:
            await update.message.reply_text("充值成功！", reply_markup=create_main_menu())
    else:
        await update.message.reply_text("充值失败，请稍后重试或联系客服。", reply_markup=create_main_menu())

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 这里需要实现实际的提现逻辑
    withdrawal_successful = False  # 这应该根据实际提现结果来设置
    if withdrawal_successful:
        user = get_user_by_telegram_id(str(update.effective_user.id))
        if not user['invite_code']:
            invite_code = generate_invite_code(user['id'])
            await update.message.reply_text(f"提现成功！您的专属邀请码是: {invite_code}", reply_markup=create_main_menu())
        else:
            await update.message.reply_text("提现成功！", reply_markup=create_main_menu())
    else:
        await update.message.reply_text("提现失败，请稍后重试或联系客服。", reply_markup=create_main_menu())

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "游戏规则和帮助：\n"
        "1. 注册后获得1000游戏币空投\n"
        "2. 在1v1挖矿中下注，赢家获得奖励\n"
        "3. 邀请朋友使用您的邀请码注册，获得额外奖励\n"
        "如需更多帮助，请联系客服。"
    )
    await update.callback_query.edit_message_text(help_text, reply_markup=create_main_menu())

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = get_user_by_telegram_id(str(query.from_user.id))
    
    if not user:
        await query.edit_message_text("请先注册后再开始游戏。", reply_markup=create_main_menu())
        return

    context.user_data['game_state'] = 'awaiting_bet'
    await query.edit_message_text(
        f"您当前的余额是：{user['balance']} 游戏币。\n"
        "请输入您要下注的金额（必须是100的倍数，最小100，最大1000）：",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("取消", callback_data='cancel_game')]])
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # 检查游戏状态
        game_state = context.user_data.get('game_state', 'idle')
        
        if game_state == 'idle':
            # 如果游戏状态是空闲，只显示主菜单
            await update.message.reply_text("请选择一个操作：", reply_markup=create_main_menu())
            return
        
        if 'awaiting_invite_code' in context.user_data and context.user_data['awaiting_invite_code']:
            await handle_invite_code(update, context)
        elif game_state == 'awaiting_bet':
            await process_bet(update, context)
        else:
            # 如果不是以上任何状态，显示主菜单
            await update.message.reply_text("请选择一个操作：", reply_markup=create_main_menu())
    except Exception as e:
        logger.error(f"Error in handle_message: {e}", exc_info=True)
        await update.message.reply_text("发生错误，请稍后重试或联系客服。", reply_markup=create_main_menu())
        # 重置用户状态
        context.user_data.clear()
        context.user_data['game_state'] = 'idle'

async def process_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(str(update.message.from_user.id))
    try:
        bet_amount = int(update.message.text)
    except ValueError:
        await update.message.reply_text("请输入有效的数字。", reply_markup=create_main_menu())
        return

    if bet_amount % 100 != 0 or bet_amount < 100 or bet_amount > 1000:
        await update.message.reply_text("下注金额必须是100的倍数，最小100，最大1000。请重新输入：")
        return

    if user['balance'] < bet_amount:
        await update.message.reply_text("余额不足，请重新输入较小的金额：")
        return

    # 立即扣除下注金额
    update_user_balance(user['telegram_id'], -bet_amount)

    game_id = str(uuid.uuid4())
    context.user_data['game_id'] = game_id
    context.user_data['bet_amount'] = bet_amount
    context.user_data['dice_count'] = 0
    context.user_data['total_score'] = 0
    context.user_data['game_state'] = 'rolling_dice'
    
    # 添加游戏历史记录，状态为 'pending'
    add_game_history(game_id, user['id'], None, bet_amount, 0, 0, None, 0, 'pending')

    if 'pending_games' not in context.bot_data:
        context.bot_data['pending_games'] = {}
    context.bot_data['pending_games'][game_id] = {
        'game_id': game_id,
        'bet_amount': bet_amount,
        'creator_id': user['id'],
        'creator_score': 0
    }
    
    await update.message.reply_text("请发送骰子表情来进行游戏。您需要发送3次骰子。")

async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = get_user_by_telegram_id(str(query.from_user.id))
    game_id = context.user_data.get('game_id')
    
    if game_id and game_id in context.bot_data.get('pending_games', {}):
        game = context.bot_data['pending_games'][game_id]
        bet_amount = game['bet_amount']
        
        # 退还下注金额
        update_user_balance(user['telegram_id'], bet_amount)
        
        # 清理游戏数据
        del context.bot_data['pending_games'][game_id]

    # 重置用户数据
    context.user_data.clear()
    context.user_data['game_state'] = 'idle'

    await query.edit_message_text("游戏已取消，下注金额已退还。", reply_markup=create_main_menu())


async def handle_dice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if 'game_state' not in context.user_data or context.user_data['game_state'] != 'rolling_dice':
            return

        if 'dice_count' not in context.user_data or context.user_data['dice_count'] >= 3:
            return

        dice_value = update.message.dice.value
        context.user_data['total_score'] = context.user_data.get('total_score', 0) + dice_value
        context.user_data['dice_count'] = context.user_data.get('dice_count', 0) + 1

        if context.user_data['dice_count'] < 3:
            await update.message.reply_text(f"您的第 {context.user_data['dice_count']} 次骰子点数为 {dice_value}。还需要再投 {3 - context.user_data['dice_count']} 次骰子。")
        else:
            game_id = context.user_data['game_id']
            total_score = context.user_data['total_score']
            bet_amount = context.user_data['bet_amount']
            game = context.bot_data['pending_games'].get(game_id)
            
            user = get_user_by_telegram_id(str(update.effective_user.id))
            
            if game and game['creator_id'] != user['id']:
                # 这是挑战者
                await finish_game(update, context, game_id, total_score)
            else:
                # 这是游戏创建者，生成邀请链接
                context.bot_data['pending_games'][game_id] = {
                    'bet_amount': bet_amount,
                    'creator_id': user['id'],
                    'creator_score': total_score
                }
                
                invite_link = f"https://t.me/{context.bot.username}?start={game_id}"
                
                await update.message.reply_text(
                    f"您已下注 {bet_amount} 游戏币，您的总得分是 {total_score}。\n\n"
                    f"分享以下消息邀请对手："
                )

                invite_message = (
                    f"@{user['username'] or 'Unknown'} 发起了一个{bet_amount}游戏币的挑战！\n"
                    f"点击链接加入游戏：{invite_link}\n\n"
                    f"快使用我的邀请码 {user['invite_code'] or 'Unknown'} 获取1000代币空投！！"
                )
 
                await update.message.reply_text(invite_message)

                context.user_data['game_state'] = 'waiting_for_opponent'

            # 清理游戏数据
            context.user_data.clear()
            context.user_data['game_state'] = 'idle'

    except Exception as e:
        logger.error(f"Error in handle_dice: {e}", exc_info=True)
        await update.message.reply_text("发生错误，请稍后重试或联系客服。", reply_markup=create_main_menu())
        # 重置游戏状态
        context.user_data.clear()
        context.user_data['game_state'] = 'idle'
        if 'game_id' in context.user_data:
            game_id = context.user_data['game_id']
            if game_id in context.bot_data.get('pending_games', {}):
                del context.bot_data['pending_games'][game_id]
                
async def finish_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id: str, challenger_score: int):
    game = context.bot_data['pending_games'].get(game_id)
    if not game:
        await update.message.reply_text("游戏已结束或不存在。", reply_markup=create_main_menu())
        return

    creator = get_user_by_id(game['creator_id'])
    challenger = get_user_by_telegram_id(str(update.effective_user.id))
    
    creator_score = game['creator_score']
    bet_amount = game['bet_amount']

    if challenger_score > creator_score:
        winner = challenger
        loser = creator
    elif challenger_score < creator_score:
        winner = creator
        loser = challenger
    else:
        # 平局，退还下注金额
        update_user_balance(creator['telegram_id'], bet_amount)
        update_user_balance(challenger['telegram_id'], bet_amount)
        tie_message = f"游戏结束！双方平局，各自的分数是 {challenger_score}。下注金额已退还。"
        await update.message.reply_text(tie_message, reply_markup=create_main_menu())
        await context.bot.send_message(
            chat_id=creator['telegram_id'],
            text=tie_message,
            reply_markup=create_main_menu()
        )
        # 清理游戏数据
        del context.bot_data['pending_games'][game_id]
        context.user_data.clear()
        return

    # 计算赢家获得的奖金（下注金额的90%）
    win_amount = bet_amount * 0.9

    # 计算上级邀约者的7%收益
    inviter_amount = bet_amount * 0.07

    # 计算项目方的3%收益
    project_amount = bet_amount * 0.03

    # 发送结果通知
    winner_message = (
        f"游戏结束！\n您的得分：{winner['id'] == creator['id'] and creator_score or challenger_score}\n"
        f"对手得分：{winner['id'] == creator['id'] and challenger_score or creator_score}\n"
        f"恭喜您赢得了 {win_amount} 游戏币！"
    )
    loser_message = (
        f"游戏结束！\n您的得分：{loser['id'] == creator['id'] and creator_score or challenger_score}\n"
        f"对手得分：{loser['id'] == creator['id'] and challenger_score or creator_score}\n"
        f"很遗憾，您输掉了 {bet_amount} 游戏币。"
    )

    # 发送消息给挑战者
    await update.message.reply_text(
        winner['id'] == challenger['id'] and winner_message or loser_message,
        reply_markup=create_main_menu()
    )
    
    # 发送消息给创建者
    await context.bot.send_message(
        chat_id=creator['telegram_id'],
        text=winner['id'] == creator['id'] and winner_message or loser_message,
        reply_markup=create_main_menu()
    )

    # 更新赢家余额（下注金额的190%）
    update_balance_amount = bet_amount * 1.9
    update_user_balance(winner['telegram_id'], update_balance_amount)

    # 处理上级邀约者的7%收益
    inviter = get_user_by_id(winner.get('inviter_id'))
    if inviter:
        update_user_balance(inviter['telegram_id'], inviter_amount, is_invite_earning=True)

    # 处理项目方的3%收益
    project_account = get_user_by_id(1)  # 假设项目方账户的ID为1
    if project_account:
        update_user_balance(project_account['telegram_id'], project_amount)

    # 清理游戏数据
    del context.bot_data['pending_games'][game_id]
    
    # 清理挑战者的用户数据
    context.user_data.clear()
    
    # 清理创建者的用户数据（如果创建者不是当前用户）
    if creator['telegram_id'] != str(update.effective_user.id):
        user_data = context.application.user_data.get(creator['telegram_id'])
        if user_data:
            user_data.clear()

    # 添加游戏历史记录
    add_game_history(game_id, creator['id'], challenger['id'], bet_amount, creator_score, challenger_score, winner['id'], win_amount, 'completed')

    # 重置游戏状态
    context.user_data['game_state'] = 'idle'
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("请选择以下操作：", reply_markup=create_main_menu())
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("请选择以下操作：", reply_markup=create_main_menu())

def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}", exc_info=True)
    
    if isinstance(context.error, telegram.error.BadRequest) and "Message is not modified" in str(context.error):
        logger.info("Ignored 'Message is not modified' error")
        return
    
    if update and isinstance(update, Update) and update.effective_message:
        error_message = "处理您的请求时发生错误。请稍后再试。"
        try:
            update.effective_message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

def main() -> None:
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice))
        
        application.add_handler(MessageHandler(filters.ALL, show_menu))

        application.add_error_handler(error_handler)
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == '__main__':
    create_tables()
    main()











