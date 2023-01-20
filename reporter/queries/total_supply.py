from reporter.queries.common import w3
from reporter.env import ADDRESSES

# simplified ABI containing just the fragment we want to use
ERC20_TOTAL_SUPPLY_ABI = """
    [{
      "inputs": [],
      "name": "totalSupply",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    }]
    """


def get_xauxo_total_supply():
    XAUXO_CONTRACT = w3.eth.contract(abi=ERC20_TOTAL_SUPPLY_ABI, address=ADDRESSES.XAUXO)  # type: ignore
    return XAUXO_CONTRACT.functions.totalSupply().call()
