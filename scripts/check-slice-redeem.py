import json

from ape_safe import ApeSafe
from brownie import web3, interface, accounts

SAFE_ADDRESS = web3.toChecksumAddress('0x6458A23B020f489651f2777Bd849ddEd34DfCcd2')
MERKLE_DISTRIBUTOR_ADDRESS = web3.toChecksumAddress('0xbaB795479bfF02c6ef52a10a54a95a42A1afa456')
SLICE_ADDRESS = web3.toChecksumAddress('0x1083D743A1E53805a95249fEf7310D75029f7Cd6')

def read_epoch_file(filename):
    with open(filename, 'r') as f:
        epoch = json.load(f)
    
    return epoch

def post_execution(redeemed):
    slice = interface.ERC20(SLICE_ADDRESS)

    print(f'Rewards contract ({MERKLE_DISTRIBUTOR_ADDRESS}) has {slice.balanceOf(MERKLE_DISTRIBUTOR_ADDRESS)} SLICE (undistributed rewards)')
    print(f'Total SLICE claimed: {redeemed - slice.balanceOf(MERKLE_DISTRIBUTOR_ADDRESS)}')

def set_window(amount, merkle_root, ipfs_hash='', account=None):
    safe_account = account if account != None else accounts.at(SAFE_ADDRESS, force=True)
    merkle_distributor = interface.IMerkleDistributor(MERKLE_DISTRIBUTOR_ADDRESS)
    slice = interface.ERC20(SLICE_ADDRESS)

    print(f'Balance before: {slice.balanceOf(merkle_distributor.address)}')

    slice.approve(MERKLE_DISTRIBUTOR_ADDRESS, 0, {'from': safe_account})
    slice.approve(MERKLE_DISTRIBUTOR_ADDRESS, int(amount), {'from': safe_account})
    merkle_distributor.setWindow(int(amount), SLICE_ADDRESS, merkle_root, ipfs_hash, {'from': safe_account})
    
    print(f'Balance after: {slice.balanceOf(merkle_distributor.address)}')

    print(f'Rewards contract ({MERKLE_DISTRIBUTOR_ADDRESS}) has {slice.balanceOf(MERKLE_DISTRIBUTOR_ADDRESS)} SLICE')

def claim(account, claim):
    user_account = accounts.at(account, force=True)
    merkle_distributor = interface.IMerkleDistributor(MERKLE_DISTRIBUTOR_ADDRESS)
    slice = interface.ERC20(SLICE_ADDRESS)

    call_values = (claim['windowIndex'], int(claim['amount']), claim['accountIndex'], account, claim['proof'])

    balance_before = slice.balanceOf(user_account.address)

    merkle_distributor.claim(call_values, {'from': user_account})

    balance_after = slice.balanceOf(user_account.address)

    return {'address': account, 'amount': balance_after - balance_before}

def main():
    epoch = read_epoch_file('reports/epochs/2/merkle-tree.json')

    set_window(epoch['totalRewardsDistributed'], epoch['merkleRoot'])

    redeemed = 0
    for address in epoch['claims']:
        redeem = claim(web3.toChecksumAddress(address), epoch['claims'][address])
        redeemed += redeem['amount']
    
    post_execution(redeemed)

def build_and_post_tx():
    safe = ApeSafe(SAFE_ADDRESS)
    epoch = read_epoch_file('reports/epochs/2/merkle-tree.json')
    
    set_window(epoch['totalRewardsDistributed'], epoch['merkleRoot'], ipfs_hash='QmcWF96drTaUQ6FyKwgQSCRZm9LJaW5HqdfsduPyperAfz', account=safe.account)

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx)
    safe.post_transaction(safe_tx)