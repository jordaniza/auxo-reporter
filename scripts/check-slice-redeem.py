import json

from brownie import web3, interface, accounts, Wei

SAFE_ADDRESS = web3.toChecksumAddress('0x6458A23B020f489651f2777Bd849ddEd34DfCcd2')
REWARDS_ADDRESS = web3.toChecksumAddress('0xE6136F2e90EeEA7280AE5a0a8e6F48Fb222AF945')
SLICE_ADDRESS = web3.toChecksumAddress('0x1083D743A1E53805a95249fEf7310D75029f7Cd6')
SLICE_AMOUNT = 1350000000000000000000000

def read_epoch_file(filename):
    with open(filename, 'r') as f:
        epoch = json.load(f)
    
    return epoch

def post_execution(rewards):
    rewards_contract = interface.IRewards(REWARDS_ADDRESS)
    slice = interface.ERC20(SLICE_ADDRESS)

    print(f'Participation root: {rewards_contract.participationMerkleRoot()}')
    print(f'Rewards contract ({REWARDS_ADDRESS}) has {slice.balanceOf(REWARDS_ADDRESS)} SLICE (undistributed rewards)')
    print(f'Users that claimed: {len(rewards)}')
    print(f'Total SLICE claimed: {SLICE_AMOUNT - slice.balanceOf(REWARDS_ADDRESS)}')

def set_merkle_root(root):
    safe_account = accounts.at(SAFE_ADDRESS, force=True)
    rewards_contract = interface.IRewards(REWARDS_ADDRESS)

    rewards_contract.setParticipationMerkleRoot(root, {'from': safe_account})

def distribute_rewards():
    safe_account = accounts.at(SAFE_ADDRESS, force=True)
    rewards_contract = interface.IRewards(REWARDS_ADDRESS)
    slice = interface.ERC20(SLICE_ADDRESS)

    slice.approve(REWARDS_ADDRESS, SLICE_AMOUNT, {'from': safe_account})
    rewards_contract.distributeRewards(SLICE_AMOUNT, {'from': safe_account})
    
    print(f'Rewards contract ({REWARDS_ADDRESS}) has {slice.balanceOf(REWARDS_ADDRESS)} SLICE')

def redistribute(addresses, proofs):
    safe_account = accounts.at(SAFE_ADDRESS, force=True)
    rewards_contract = interface.IRewards(REWARDS_ADDRESS)

    rewards_contract.redistribute(addresses, proofs, {'from': safe_account})

def redeem(address, proof):
    user_account = accounts.at(address, force=True)
    rewards_contract = interface.IRewards(REWARDS_ADDRESS)
    slice = interface.ERC20(SLICE_ADDRESS)

    rewards_contract.claim(proof, {'from': user_account})

    return {'address': address, 'amount': Wei(slice.balanceOf(address))}

def main():
    epoch = read_epoch_file('epochs/epoch-21-10.json')

    distribute_rewards()
    set_merkle_root(epoch['merkleTree']['root'])

    redistribute_addresses = []
    redistribute_proofs = []
    for leaf in epoch['merkleTree']['leafs']:
        if leaf['participation'] == 0:
            redistribute_addresses.append(web3.toChecksumAddress(leaf['address']))
            redistribute_proofs.append(leaf['proof'])

    redistribute(redistribute_addresses, redistribute_proofs)
    
    rewards = []
    for leaf in epoch['merkleTree']['leafs']:
        if leaf['participation'] == 1:
            rewards.append(redeem(web3.toChecksumAddress(leaf['address']), leaf['proof']))
    
    post_execution(rewards)

    print(rewards)