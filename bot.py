from web3 import Web3
import json

w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:9650/ext/bc/C/rpc'))

with open("pool.json") as poolFile :
    poolABI = json.load(poolFile )
with open("ERC20.json") as erc20File:
    ERC20ABI = json.load(erc20File)

liquidityContract = w3.eth.contract(address=w3.toChecksumAddress("0x9ee0a4e21bd333a6bb2ab298194320b8daa26516"), abi=poolABI)

reserves = liquidityContract.functions.getReserves().call()
reserveToken0 = reserves[0]
reserveToken1 = reserves[1]

token0Address = liquidityContract.functions.token0().call()
token1Address = liquidityContract.functions.token1().call()

token0 = w3.eth.contract(address=w3.toChecksumAddress(token0Address), abi=ERC20ABI)
token1 = w3.eth.contract(address=w3.toChecksumAddress(token1Address), abi=ERC20ABI)

token0Symbol = token0.functions.symbol().call()
token0Decimals = token0.functions.decimals().call()

token1Symbol = token1.functions.symbol().call()
token1Decimals = token1.functions.decimals().call()


if token0Symbol == "WAVAX" :
    price = (reserveToken1/10**token1Decimals) / (reserveToken0/10**token0Decimals)
else :
    price = (reserveToken0/10**token0Decimals) / (reserveToken1/10**token1Decimals)
print("The current price of AVAX is {:4.2f} USDT".format(price))
