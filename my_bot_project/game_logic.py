import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user_by_telegram_id, update_user_balance

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = get_user_by_telegram_id(str(query.from_user.id))
    
    if not user:
        await query.edit_message_text("请先注册后再开始游戏。")
        return

    context.user_data['game_state'] = 'awaiting_bet'
    await query.edit_message_text(
        "请输入您要下注的金额（必须是100的倍数，最小100，最大1000）：",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("取消", callback_data='cancel_game')]])
    )

async def process_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(str(update.message.from_user.id))
    bet_amount = int(update.message.text)

    if bet_amount % 100 != 0 or bet_amount < 100 or bet_amount > 1000:
        await update.message.reply_text("下注金额必须是100的倍数，最小100，最大1000。请重新输入：")
        return

    if user['balance'] < bet_amount:
        await update.message.reply_text("余额不足，请重新输入较小的金额：")
        return

    context.user_data['bet_amount'] = bet_amount
    player_score = roll_dice()
    opponent_score = roll_dice()

    result_message = f"您的得分：{player_score}\n对手的得分：{opponent_score}\n"

    if player_score > opponent_score:
        winnings = calculate_winnings(bet_amount)
        update_user_balance(str(user['telegram_id']), winnings)
        result_message += f"恭喜！您赢得了 {winnings} 游戏币！"
    elif player_score < opponent_score:
        update_user_balance(str(user['telegram_id']), -bet_amount)
        result_message += f"很遗憾，您输掉了 {bet_amount} 游戏币。"
    else:
        result_message += "平局！您的下注金额已退回。"

    await update.message.reply_text(result_message)
    context.user_data['game_state'] = None

def roll_dice():
    return sum(random.randint(1, 6) for _ in range(3))

def calculate_winnings(bet_amount):
    gross_winnings = bet_amount * 2
    project_fee = int(gross_winnings * 0.03)
    inviter_fee = int(gross_winnings * 0.07)
    return gross_winnings - project_fee - inviter_fee

async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    context.user_data['game_state'] = None
    await query.edit_message_text("游戏已取消。")