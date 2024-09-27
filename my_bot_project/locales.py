MESSAGES = {
    'en': {
        'welcome': "Welcome to the Dice Game!",
        'balance': "Your current balance is: {} DICE",
        # ... 其他英文消息
    },
    'zh': {
        'welcome': "欢迎来到骰子游戏!",
        'balance': "您当前的余额是: {} DICE",
        # ... 其他中文消息
    }
}

def get_message(key, lang='en'):
    return MESSAGES.get(lang, MESSAGES['en']).get(key, MESSAGES['en'].get(key, key))