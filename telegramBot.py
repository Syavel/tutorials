from web3 import Web3
from telegram.ext import Updater
from telegram.ext import CommandHandler
import logging
import json

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

#Web3
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:9650/ext/bc/C/rpc'))

class Dex():
    def __init__(self, factoryContract, name):
        self.factoryContract = factoryContract
        self.name = name
        self.pairs = list()
    
    def updatePairs(self):
        #We get the number of pairs on this dex
        pairsOnDex = self.factoryContract.functions.allPairsLength().call()
        #And we want to retrieve pairs we don't know yet
        for i in range(len(self.pairs), pairsOnDex) :
            #We ask what is the pair i and it returns its address
            newPairAddress = self.factoryContract.functions.allPairs(i).call()
            #Now we instantiate a pair contract for this pair
            newPairContract = w3.eth.contract(address=newPairAddress, abi=poolABI)
            token0Address = newPairContract.functions.token0().call()
            token1Address = newPairContract.functions.token1().call()
            #We check if we already know it
            if token0Address in tokensWeKnow :
                newToken0 = tokensWeKnow[token0Address]
            else :
                newToken0Contract = w3.eth.contract(address=token0Address, abi=ERC20ABI)
                #And a Token object
                newToken0Symbol = newToken0Contract.functions.symbol().call()
                newToken0Decimals = newToken0Contract.functions.decimals().call()
                newToken0Name = newToken0Contract.functions.name().call()
                newToken0 = Token(newToken0Contract, token0Address, newToken0Symbol, newToken0Decimals, newToken0Name)
                tokensWeKnow[token0Address] = newToken0
            if token1Address in tokensWeKnow :
                newToken1 = tokensWeKnow[token1Address]
            else :
                newToken1Contract = w3.eth.contract(address=token1Address, abi=ERC20ABI)
                newToken1Symbol = newToken1Contract.functions.symbol().call()
                newToken1Decimals = newToken1Contract.functions.decimals().call()
                newToken1Name = newToken1Contract.functions.name().call()
                newToken1 = Token(newToken1Contract, token1Address, newToken1Symbol, newToken1Decimals, newToken1Name)
                tokensWeKnow[token1Address] = newToken1

            #We can create the Pair object
            newPair = Pair(newPairContract, newToken0, newToken1)
            #And we update its liquidity
            newPair.updateLiquidity()
            self.pairs.append(newPair)

class Token():
    def __init__(self, contract, address, symbol, decimals, name):
        self.contract = contract
        self.address = address
        self.symbol = symbol
        self.decimals = decimals
        self.name = name

class Pair():
    def __init__(self, contract, token0, token1):
        self.contract = contract
        self.token0 = token0
        self.token1 = token1
        self.token0Liquidity = 0
        self.token1Liquidity = 0
        
    def updateLiquidity(self):
        reserves = self.contract.functions.getReserves().call()
        self.token0Liquidity = reserves[0]
        self.token1Liquidity = reserves[1]

def findPair(tokenSymbol, otherSymbol, dexes):
    #We must care if there is multiple pair with same Symbol
    liquidity = 0
    for dex in dexes :
        for pair in dex.pairs :
            if pair.token0.symbol == tokenSymbol and pair.token1.symbol == otherSymbol or pair.token1.symbol == tokenSymbol and pair.token0.symbol == otherSymbol :
                if pair.token0.symbol == tokenSymbol and pair.token1Liquidity > liquidity :
                    currentPair = pair
                    liquidity = pair.token1Liquidity
                    currentDex = dex
                elif pair.token1.symbol == tokenSymbol and pair.token0Liquidity > liquidity :
                    currentPair = pair
                    liquidity = pair.token0Liquidity
                    currentDex = dex
    try :
        return currentPair, currentDex
    except :
        return None, None

def findAVAXPair(tokenSymbol, dex):
    return findPair(tokenSymbol, "WAVAX", dex)

def findUSDTPair(tokenSymbol, dex):
    return findPair(tokenSymbol, "USDT", dex)

def price(tokenSymbol, pair):
    if pair.token0.symbol == tokenSymbol :
        return (pair.token1Liquidity / 10**pair.token1.decimals) / (pair.token0Liquidity / 10**pair.token0.decimals)
    else :
        return (pair.token0Liquidity / 10**pair.token0.decimals) / (pair.token1Liquidity / 10**pair.token1.decimals)

#Telegram
updater = Updater(token="YOUR_TOKEN", use_context=True)
dispatcher = updater.dispatcher

with open("Factory.json") as factoryFile:
    factoryABI = json.load(factoryFile)
with open("Pool.json") as poolFile :
    poolABI = json.load(poolFile )
with open("ERC20.json") as erc20File:
    ERC20ABI = json.load(erc20File)

dexesAddresses = [
    ["Yetiswap",  "0x58C8CD291Fa36130119E6dEb9E520fbb6AcA1c3a"],
    ["Pangolin", "0xefa94DE7a4656D787667C749f7E1223D71E9FD88"],
    ["Complus", "0x5C02e78A3969D0E64aa2CFA765ACc1d671914aC0"],
    ["SushiSwap", "0xc35DADB65012eC5796536bD9864eD8773aBc74C4"],
    ["Zero", "0x2Ef422F30cdb7c5F1f7267AB5CF567A88974b308"],
    ["Elk", "0x091d35d7f63487909c863001ddca481c6de47091"],
    ["PandaSwap", "0xc7e37A28bB17EdB59E99d5485Dc8c51BC87aE699"]
]
tokensWeKnow = dict()
dexes = list()

for dex in dexesAddresses :
    dexName = dex[0]
    dexAddress = dex[1]
    #We instantiate the dex contract
    dexContract = w3.eth.contract(address=w3.toChecksumAddress(dexAddress), abi=factoryABI)
    #We instantiate a new dex object and add it to our list
    newDex = Dex(dexContract, dexName)
    newDex.updatePairs()
    dexes.append(newDex)


def telegramPrice(update, context):
    tokenSymbol = update.message.text[7:]
    tokenSymbol = tokenSymbol.upper()
    if tokenSymbol == "AVAX" :
        tokenSymbol = "WAVAX"
    pairAVAX, dex1 = findAVAXPair(tokenSymbol, dexes)
    pairUSDT, dex2 = findUSDTPair(tokenSymbol, dexes)
    if pairAVAX != None :
        #We update the liquidity
        pairAVAX.updateLiquidity()
        tokenPriceAVAX = price(tokenSymbol, pairAVAX)
        context.bot.send_message(chat_id=update.effective_chat.id, text="Price : {:,.4f}{}/{} (on {})".format(tokenPriceAVAX, "AVAX", tokenSymbol, dex1.name))
    if pairUSDT != None :
        pairUSDT.updateLiquidity()
        tokenPriceUSDT = price(tokenSymbol, pairUSDT)
        context.bot.send_message(chat_id=update.effective_chat.id, text="Price : {:,.4f}{}/{} (on {})".format(tokenPriceUSDT, "USDT", tokenSymbol, dex2.name))

telegramPriceHandler = CommandHandler('price', telegramPrice)
dispatcher.add_handler(telegramPriceHandler)
#Starting listening to commands
updater.start_polling()

