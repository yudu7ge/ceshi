import asyncio
from tonsdk.contract.wallet import WalletV3ContractR2
from pytonlib import TonlibClient
from tonsdk.utils import to_nano

async def deploy_contract():
    # 连接到主网
    client = TonlibClient()
    await client.init()

    # 替换为您的主网钱包助记词
    mnemonic = ["word1", "word2", "..."]  # 24个助记词
    wallet = WalletV3ContractR2.from_mnemonic(mnemonic)

    with open('../telegramdice/build/liquidity_pool.cell', 'rb') as f:
        contract_code = f.read()

    deploy_message = wallet.create_deploy_message(contract_code, initial_data=b'')
    result = await client.send_message(deploy_message)

    print(f"Contract deployed at: {result['address']}")
    return result['address']

if __name__ == "__main__":
    contract_address = asyncio.run(deploy_contract())
    print(f"Deployed contract address: {contract_address}")