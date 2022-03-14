import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import fire
import json

from tinydb import TinyDB, Query
from eth_utils import to_checksum_address

Account = Query()

def check_rewards(db, epoch):
    accounts = db.table("accounts").all()

    rewards_db = {acc['address']:int(acc['slice_amount']) for acc in accounts}
    
    rewards_json = {to_checksum_address(key):int(val['amount']) for (key, val) in epoch['merkleTree']['claims'].items()}
    for (addr, item) in epoch['merkleTree']['stats']['notVotingAddresses'].items():
        rewards_json[to_checksum_address(addr)] = int(item['amount'])

    common_addrs = [addr for addr in set([*rewards_db.keys(), *rewards_json.keys()]) if addr in rewards_db.keys() and addr in rewards_json.keys()]

    print(f'Addresses in rewards_db: {len(rewards_db.keys())}')
    print(f'Addresses in rewards_json: {len(rewards_json.keys())}')

    diff = []
    for addr in common_addrs:
        if rewards_db[addr] != rewards_json[addr]:
            diff.append({'addr': addr, 'db': rewards_db[addr], 'json': rewards_json[addr], 'diff': abs(rewards_db[addr] - rewards_json[addr])})
    
    print(f'Differences found in: {len(diff)} accounts')
    for d in diff:
        print(d)

def check(db_file, epoch_file):
    db = TinyDB(db_file)
    epoch = json.load(open(epoch_file))

    # checks
    check_rewards(db, epoch)


if __name__ == "__main__":
    fire.Fire({
        "check": check
    })