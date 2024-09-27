import asyncio
from tonsdk.contract.wallet import WalletV3ContractR2
from pytonlib import TonlibClient
from tonsdk.utils import to_nano

async def initialize_contract(contract_address):
    client = TonlibClient()
    await client.init()

    mnemonic = ["word1", "word2", "..."]  # 替换为您的主网钱包助记词
    wallet = WalletV3ContractR2.from_mnemonic(mnemonic)

    # 创建初始化消息
    init_message = wallet.create_transfer_message(
        to_addr=contract_address,
        amount=to_nano(1),  # 发送1 TON作为初始流动性
        payload=create_init_payload()
    )
    result = await client.send_message(init_message)
    print("Contract initialized")

def create_init_payload():
    from tonsdk.boc import Cell
    cell = Cell()
    cell.bits.write_uint(1, 32)  # op code for initialization
    return cell.begin_parse()

if __name__ == "__main__":
    contract_address = "EQ..."  # 替换为部署脚本输出的地址
    asyncio.run(initialize_contract(contract_address))