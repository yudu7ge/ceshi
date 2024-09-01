// 用户注册API
app.post('/register', async (req, res) => {
    const { telegram_id, referral_code } = req.body;

    try {
        const user = await User.create({ telegram_id, referred_by: referral_code });
        res.json(user);
    } catch (error) {
        console.error('Error registering user:', error);
        res.status(500).json({ error: error.message });
    }
});

// 掷骰子API
app.post('/roll_dice', async (req, res) => {
    const { telegram_id } = req.body;

    try {
        const user = await User.findOne({ where: { telegram_id } });

        if (user.balance < 100) {
            return res.status(400).json({ error: '余额不足，无法继续游戏' });
        }

        // 扣除100游戏币
        user.balance -= 100;

        const roll1 = Math.floor(Math.random() * 6) + 1;
        const roll2 = Math.floor(Math.random() * 6) + 1;
        const roll3 = Math.floor(Math.random() * 6) + 1;
        const total = roll1 + roll2 + roll3;

        let resultMessage;
        if (total > 9) {
            user.balance += 90;  // 胜利获得90游戏币
            user.win_count += 1;
            resultMessage = '你赢了！';
        } else {
            user.lose_count += 1;
            resultMessage = '你输了！';
        }

        await user.save();
        await Game.create({ user_id: user.id, result: total });

        res.json({ message: resultMessage, total, balance: user.balance });
    } catch (error) {
        console.error('Error processing roll:', error);
        res.status(500).json({ error: error.message });
    }
});
const express = require('express');
const { Sequelize, DataTypes } = require('sequelize');
const cors = require('cors');
const app = express();

app.use(express.json());
app.use(cors());

// 连接到数据库
const sequelize = new Sequelize('mydatabase', 'postgres', 'your_password', {
    host: 'localhost',
    dialect: 'postgres'
});

// 定义用户模型
const User = sequelize.define('User', {
    telegram_id: {
        type: DataTypes.STRING,
        unique: true,
        allowNull: false
    },
    balance: {
        type: DataTypes.DECIMAL(10, 2),
        defaultValue: 1000  // 新用户的空投金额
    },
    referral_code: DataTypes.STRING,
    referred_by: DataTypes.STRING,
    win_count: {
        type: DataTypes.INTEGER,
        defaultValue: 0
    },
    lose_count: {
        type: DataTypes.INTEGER,
        defaultValue: 0
    },
    referral_earnings: {
        type: DataTypes.DECIMAL(10, 2),
        defaultValue: 0
    }
});

// 定义游戏模型
const Game = sequelize.define('Game', {
    user_id: {
        type: DataTypes.INTEGER,
        references: {
            model: User,
            key: 'id'
        }
    },
    result: DataTypes.INTEGER,
    created_at: {
        type: DataTypes.DATE,
        defaultValue: Sequelize.NOW
    }
});

// 同步模型到数据库
sequelize.sync();

// 用户注册API
app.post('/register', async (req, res) => {
    const { telegram_id, referral_code } = req.body;

    try {
        const user = await User.create({ telegram_id, referred_by: referral_code });
        res.json(user);
    } catch (error) {
        console.error('Error registering user:', error);
        res.status(500).json({ error: error.message });
    }
});

// 掷骰子API
app.post('/roll_dice', async (req, res) => {
    const { telegram_id } = req.body;

    try {
        const user = await User.findOne({ where: { telegram_id } });

        if (user.balance < 100) {
            return res.status(400).json({ error: '余额不足，无法继续游戏' });
        }

        // 扣除100游戏币
        user.balance -= 100;

        const roll1 = Math.floor(Math.random() * 6) + 1;
        const roll2 = Math.floor(Math.random() * 6) + 1;
        const roll3 = Math.floor(Math.random() * 6) + 1;
        const total = roll1 + roll2 + roll3;

        let resultMessage;
        if (total > 9) {
            user.balance += 90;  // 胜利获得90游戏币
            user.win_count += 1;
            resultMessage = '你赢了！';
        } else {
            user.lose_count += 1;
            resultMessage = '你输了！';
        }

        await user.save();
        await Game.create({ user_id: user.id, result: total });

        res.json({ message: resultMessage, total, balance: user.balance });
    } catch (error) {
        console.error('Error processing roll:', error);
        res.status(500).json({ error: error.message });
    }
});

// 启动服务器
app.listen(3000, () => {
    console.log('Server is running on port 3000');
});
