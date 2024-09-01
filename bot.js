const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

// 使用从BotFather获取的Token
const token = '7434695508:AAGpRHmiFjYbSxdpbY0GBYR6l4ySogQrolo';
const bot = new TelegramBot(token, { polling: true });

// 处理 /start 命令
bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;

    // 发送欢迎消息并提示用户输入邀请码
    bot.sendMessage(chatId, '欢迎来到掷骰子游戏！请输入您的邀请码进行注册（或输入"skip"跳过）：');
});

// 处理用户消息
bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const referralCode = msg.text.trim();

    if (referralCode.toLowerCase() === 'skip') {
        // 如果用户输入了skip，跳过邀请注册
        bot.sendMessage(chatId, '正在为您注册...');
    } else {
        try {
            // 调用后端API进行注册
            const response = await axios.post('http://localhost:3000/register', {
                telegram_id: chatId.toString(),
                referral_code: referralCode
            });
            bot.sendMessage(chatId, `注册成功！您获得了1000游戏币。`);
        } catch (error) {
            bot.sendMessage(chatId, `注册失败: ${error.response.data.error}`);
        }
    }
});

// 处理 /roll 命令
bot.onText(/\/roll/, async (msg) => {
    const chatId = msg.chat.id;

    try {
        // 调用后端API进行掷骰子
        const response = await axios.post('http://localhost:3000/roll_dice', {
            telegram_id: chatId.toString()
        });
        const { message, total, balance } = response.data;
        bot.sendMessage(chatId, `${message} 总点数: ${total}，当前余额: ${balance}`);
    } catch (error) {
        bot.sendMessage(chatId, `掷骰子失败: ${error.response.data.error}`);
    }
});
