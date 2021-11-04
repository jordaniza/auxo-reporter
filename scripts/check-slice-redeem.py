import json

from brownie import web3, interface, accounts

SAFE_ADDRESS = web3.toChecksumAddress('0x6458A23B020f489651f2777Bd849ddEd34DfCcd2')
MERKLE_DISTRIBUTOR_ADDRESS = web3.toChecksumAddress('0xE7eD6747FaC5360f88a2EFC03E00d25789F69291')
SLICE_ADDRESS = web3.toChecksumAddress('0x1083D743A1E53805a95249fEf7310D75029f7Cd6')
SLICE_AMOUNT = 1350000000000000000000000

def read_epoch_file(filename):
    with open(filename, 'r') as f:
        epoch = json.load(f)
    
    return epoch

def post_execution(redeemed):
    slice = interface.ERC20(SLICE_ADDRESS)

    print(f'Rewards contract ({MERKLE_DISTRIBUTOR_ADDRESS}) has {slice.balanceOf(MERKLE_DISTRIBUTOR_ADDRESS)} SLICE (undistributed rewards)')
    print(f'Total SLICE claimed: {redeemed - slice.balanceOf(MERKLE_DISTRIBUTOR_ADDRESS)}')

def set_window(amount, merkle_root):
    safe_account = accounts.at(SAFE_ADDRESS, force=True)
    merkle_distributor = interface.IMerkleDistributor(MERKLE_DISTRIBUTOR_ADDRESS)
    slice = interface.ERC20(SLICE_ADDRESS)

    slice.approve(MERKLE_DISTRIBUTOR_ADDRESS, amount, {'from': safe_account})
    merkle_distributor.setWindow(amount, SLICE_ADDRESS, merkle_root, '', {'from': safe_account})
    
    print(f'Rewards contract ({MERKLE_DISTRIBUTOR_ADDRESS}) has {slice.balanceOf(MERKLE_DISTRIBUTOR_ADDRESS)} SLICE')

def claim(account, claim):
    user_account = accounts.at(account, force=True)
    merkle_distributor = interface.IMerkleDistributor(MERKLE_DISTRIBUTOR_ADDRESS)
    slice = interface.ERC20(SLICE_ADDRESS)

    call_values = (claim['windowIndex'], int(claim['amount']), claim['accountIndex'], account, claim['proof'])

    merkle_distributor.claim(call_values, {'from': user_account})

    return {'address': account, 'amount': slice.balanceOf(account)}

def main():
    epoch = read_epoch_file('reports/epochs/2021-10/0.json')

    set_window(epoch['totalRewardsDistributed'], epoch['merkleRoot'])

    redeemed = 0
    for address in epoch['claims']:
        redeem = claim(web3.toChecksumAddress(address), epoch['claims'][address])
        redeemed += redeem['amount']
    
    post_execution(redeemed)