from tonsdk.provider import ToncenterClient
from tonsdk.utils import to_nano

TONCENTER_API_KEY = "your_api_key_here"
TONCENTER_ENDPOINT = "https://testnet.toncenter.com/api/v2/jsonRPC"
ton_client = ToncenterClient(TONCENTER_ENDPOINT, TONCENTER_API_KEY)

DICE_CONTRACT_ADDRESS = "EQ..."  # 替换为实际部署的合约地址
TRADE_AMOUNT = 10000000000  # 10,000 DICE (with 9 decimals)
SLIPPAGE_THRESHOLD = 0.05  # 5% slippage threshold

async def get_pool_info():
    result = await ton_client.run_get_method(DICE_CONTRACT_ADDRESS, "get_pool_info", [])
    return result

async def get_exchange_rate():
    result = await ton_client.run_get_method(DICE_CONTRACT_ADDRESS, "get_exchange_rate", [])
    return result[0]

async def deposit_ton(wallet, expected_ton):
    # 使用 TON 充值（买入 DICE）
    message = wallet.create_transfer_message(
        to_addr=DICE_CONTRACT_ADDRESS,
        amount=to_nano(expected_ton + 0.1),  # 额外 0.1 TON 用于存储费
        payload=create_buy_payload(expected_ton)
    )
    result = await ton_client.send_message(message)
    return result

async def deposit_dice(wallet):
    # 使用 DICE 充值（直接存入 DICE）
    message = wallet.create_transfer_message(
        to_addr=DICE_CONTRACT_ADDRESS,
        amount=to_nano(0.1),  # 0.1 TON 用于 gas 费
        payload=create_deposit_payload(TRADE_AMOUNT)
    )
    result = await ton_client.send_message(message)
    return result

async def withdraw_ton(wallet, expected_ton):
    # 提现为 TON（卖出 DICE）
    message = wallet.create_transfer_message(
        to_addr=DICE_CONTRACT_ADDRESS,
        amount=to_nano(0.1),  # 0.1 TON 用于 gas 费
        payload=create_sell_payload(TRADE_AMOUNT, expected_ton)
    )
    result = await ton_client.send_message(message)
    return result

async def withdraw_dice(wallet):
    # 提现为 DICE（直接提取 DICE）
    message = wallet.create_transfer_message(
        to_addr=DICE_CONTRACT_ADDRESS,
        amount=to_nano(0.1),  # 0.1 TON 用于 gas 费
        payload=create_withdraw_payload(TRADE_AMOUNT)
    )
    result = await ton_client.send_message(message)
    return result

def create_buy_payload(expected_ton):
    from tonsdk.boc import Cell
    cell = Cell()
    cell.bits.write_uint(2, 32)  # op code for buy
    cell.bits.write_coins(to_nano(expected_ton))
    return cell.begin_parse()

def create_sell_payload(amount, expected_ton):
    from tonsdk.boc import Cell
    cell = Cell()
    cell.bits.write_uint(3, 32)  # op code for sell
    cell.bits.write_coins(to_nano(amount))
    cell.bits.write_coins(to_nano(expected_ton))
    return cell.begin_parse()

def create_deposit_payload(amount):
    from tonsdk.boc import Cell
    cell = Cell()
    cell.bits.write_uint(4, 32)  # op code for deposit DICE
    cell.bits.write_coins(to_nano(amount))
    return cell.begin_parse()

def create_withdraw_payload(amount):
    from tonsdk.boc import Cell
    cell = Cell()
    cell.bits.write_uint(5, 32)  # op code for withdraw DICE
    cell.bits.write_coins(to_nano(amount))
    return cell.begin_parse()