const TelegramBot = require('node-telegram-bot-api');

const token = 'YOU7434695508:AAGpRHmiFjYbSxdpbY0GBYR6l4ySogQrolo';

try {
    const bot = new TelegramBot(token, { polling: true });

    bot.on('polling_error', (error) => {
        console.error('Polling Error:', error.code, error.message);
    });

    bot.onText(/\/start/, (msg) => {
        bot.sendMessage(msg.chat.id, "欢迎来到去中心化多人掷骰子游戏！请选择游戏模式和投注金额。");
    });
} catch (error) {
    console.error('Unexpected Error:', error);
}
