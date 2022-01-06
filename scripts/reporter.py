from pathlib import Path
from brownie import web3
from decimal import Decimal
from functools import reduce
from scripts.helpers import *

import csv
import requests
import datetime
import json

SLICE_ADDRESS = web3.toChecksumAddress('0x1083D743A1E53805a95249fEf7310D75029f7Cd6')
proposals_fieldnames = ['id', 'title', 'author', 'choices', 'created', 'start', 'end']
votes_fieldnames = ['voter', 'choice', 'proposal', 'created']
stakers_fieldnames = ['address', 'amount']

def write_staking_csv(start_timestamp, dicts, filename, fieldnames):
    date = datetime.date.fromtimestamp(start_timestamp)
    path = f'reports/staking/{date.year}-{date.month}/{filename}'

    write_csv(dicts, path, fieldnames)

def write_staking_json(start_timestamp, filename, data):
    date = datetime.date.fromtimestamp(start_timestamp)
    path = f'reports/staking/{date.year}-{date.month}/{filename}'

    write_json(data, path)

def participation(address, voters):
    if web3.toChecksumAddress(address) in voters:
        return 1
    else:
        return 0

def write_participation(start_timestamp, voted):
    voters = [v['address'] for v in voted]
    stakers = {web3.toChecksumAddress(addr): participation(addr, voters) for (addr, _) in get_stakers() }
    write_staking_json(start_timestamp, 'participation.json', stakers)

def get_delegates():
    subgraph = "https://api.thegraph.com/subgraphs/name/pie-dao/vedough"
    query = '{ delegates(first: 1000) { delegator, delegate } }'
    response = requests.post(subgraph, json={'query': query})
    subgraph_delegates = response.json()['data']['delegates']

    return [(web3.toChecksumAddress(d['delegator']), web3.toChecksumAddress(d['delegate'])) for d in subgraph_delegates]

def get_stakers():
    subgraph = "https://api.thegraph.com/subgraphs/name/pie-dao/vedough"
    query = '{ stakers(first: 1000, block: {number: 13916165}) { id, accountVeTokenBalance } }'
    response = requests.post(subgraph, json={'query': query})
    subgraph_stakers = response.json()['data']['stakers']

    return [(s['id'], s['accountVeTokenBalance']) for s in subgraph_stakers]

def filter_proposals(proposals):
    if yes_or_no('Do you want to filter proposals?'):
        take = []
        for p in proposals:
            title = p['title']
            if yes_or_no(f'Is proposal {title} a valid proposal?'):
                take.append(p['id'])
        proposals = [p for p in proposals if p['id'] in take]

    return proposals

    
def report_proposals(start_timestamp, end_timestamp):
    snapshot_graphql = 'https://hub.snapshot.org/graphql'
    proposals_query = """
        query($space: String, $created_gt: Int, $end_lt: Int) { 
            proposals(first: 1000, where: {space: $space, created_gt: $created_gt, end_lt: $end_lt}) { 
                id
                title
                author
                created
                start
                end
                choices
            } 
        }
    """

    variables = {
        'space': "piedao.eth",
        'created_gt': start_timestamp,
        'end_lt': end_timestamp
    }
    response = requests.post(snapshot_graphql, json={'query': proposals_query, 'variables': variables})
    proposals = response.json()['data']['proposals']
    proposals = filter_proposals(proposals)
    write_staking_csv(start_timestamp, proposals, 'proposals.csv', proposals_fieldnames)

    return proposals


def report_votes(start_timestamp, proposals):
    proposals_ids = [p['id'] for p in proposals]

    snapshot_graphql = 'https://hub.snapshot.org/graphql'
    votes_query = """
        query($skip: Int, $space: String, $proposals: [String]) { 
            votes(skip: $skip, first: 1000, where: {space: $space, proposal_in: $proposals}) {
                voter
                choice
                proposal {
                    id
                }
                created
            } 
        }
    """

    votes = []
    variables = {'skip': 0, 'space': "piedao.eth", 'proposals': proposals_ids}
    response = requests.post(snapshot_graphql, json={'query': votes_query, 'variables': variables})
    tmp_votes = response.json()['data']['votes']
    votes = tmp_votes
    while len(tmp_votes) > 0:
        variables = {'skip': len(votes), 'space': "piedao.eth", 'proposals': proposals_ids}
        response = requests.post(snapshot_graphql, json={'query': votes_query, 'variables': variables})
        tmp_votes = response.json()['data']['votes']
        votes += tmp_votes

    write_staking_csv(start_timestamp, votes, 'votes.csv', votes_fieldnames)

    return votes


def report_voters(start_timestamp, votes):
    stakers = get_stakers()
    delegates = get_delegates()

    voters = set([web3.toChecksumAddress(v['voter']) for v in votes])
    stakers_addrs = [web3.toChecksumAddress(addr) for (addr, _) in stakers]
    delegators = [delegator for (delegator, _) in delegates]
    stakers_addrs_no_delegators = [addr for addr in stakers_addrs if addr not in delegators]


    voted = [{'address': addr} for addr in stakers_addrs_no_delegators if addr in voters]
    voted.extend([{'address': delegator} for (delegator, delegate) in delegates if delegate in voters])
    
    not_voted = [{'address': addr} for addr in stakers_addrs_no_delegators if addr not in voters]
    not_voted.extend([{'address': delegator} for (delegator, delegate) in delegates if delegate not in voters])

    write_staking_csv(start_timestamp, voted, 'voted.csv', ['address'])
    write_staking_csv(start_timestamp, not_voted, 'not_voted.csv', ['address'])

    return (voted, not_voted)

def get_stakers_from_file(f):
    with open(f, 'r') as stakers_file:
        reader = csv.DictReader(stakers_file,fieldnames=["address","amount"])
        stakers = []

        for staker in reader:
            if reader.line_num == 1:
                continue
            
            checksum_address = web3.toChecksumAddress(staker['address'])
            stakers.append({"address": checksum_address, "amount": int(staker['amount'])})

    return stakers

def write_reward_window(window_index, rewards):
    total_distributed = reduce(lambda x,y: x + y, rewards.values(), 0)
    reward_window = {'chainId': 1, 'rewardToken': SLICE_ADDRESS, 'windowIndex': window_index, 'totalRewardsDistributed': str(total_distributed)}
    recipients = {addr : {"amount": str(amount), "metaData": {"reason": [f'Distribution for epoch {window_index}']}} for (addr, amount) in rewards.items()}
    reward_window['recipients'] = recipients

    with open(f'reports/epochs/{window_index}/claims.json', 'w+') as f:
        reward_window_json = json.dumps(reward_window, indent=4)
        f.write(reward_window_json)

def get_claimed_for_window(window_index):
    snapshot_graphql = 'https://api.thegraph.com/subgraphs/name/pie-dao/vedough'
    rewards_query = """
        query($windowId: BigInt) { 
            rewards(first: 1000, where: {windowIndex: $windowId}) {
                account
            }
        }
    """

    variables = {'windowId': window_index}
    response = requests.post(snapshot_graphql, json={'query': rewards_query, 'variables': variables})
    claimed = response.json()['data']['rewards']

    return claimed



def compound_for_window(window_index, rewards):
    if window_index == 0:
        return ([], [])
    
    prev_window = 0
    prev_window_claims = f'reports/epochs/{prev_window}/claims.json'
    claimed = [web3.toChecksumAddress(item['account']) for item in get_claimed_for_window(prev_window)]

    with open(prev_window_claims, 'r') as f:
        claims_prev_window = json.load(f)['recipients']

        # Needed to report who claimed last month
        claimed_prev_window = [{'address': web3.toChecksumAddress(address), 'amount': item['amount']} for (address, item) in claims_prev_window.items() if address in claimed]
        claimed_prev_file = open('reports/staking/2021-11/claimed.csv', 'w+')
        claimed_writer = csv.DictWriter(claimed_prev_file, fieldnames=['address','amount'])
        claimed_writer.writeheader()
        claimed_writer.writerows(claimed_prev_window)

        unclaimed = []
        unclaimed_tokens = 0
        for (claim_addr, claim_obj) in claims_prev_window.items(): # get unclaimed claims from previous epoch
            if web3.toChecksumAddress(claim_addr) not in claimed: # unclaimed
                unclaimed.append({'address': claim_addr, 'amount': int(claim_obj['amount'])})
                unclaimed_tokens += int(claim_obj['amount'])

        compounded = 0
        for unclaim in unclaimed:
            rewards[unclaim['address']] += unclaim['amount']
            compounded += unclaim['amount']

    compound_report = {'unclaimed_tokens': unclaimed_tokens, 'compounded': compounded, 'total_addresses_unclaimed': len(unclaimed)}

    return (rewards, unclaimed, compound_report)

def inactive_for_window(window_index, rewards, path):
    prev_window = window_index - 1
    prev_inactive = json.load(open(f'reports/epochs/{prev_window}/inactive.json', 'r'))

    with open(f'{path}/not_voted.csv') as non_voters_file:
        reader = csv.DictReader(non_voters_file, fieldnames=['address'])
        inactive_addresses = [item['address'] for item in list(reader)[1:]]
        prev_inactive_addresses = [item['address'] for item in prev_inactive]
        prev_inactive = {item['address']:{'amount': item['amount'], 'inactive_windows': item['inactive_windows']} for item in prev_inactive}

        inactive = []
        for (addr, amount) in rewards.items():
            if addr in inactive_addresses:
                if addr in prev_inactive_addresses:
                    inactive_item = {'address': addr, 'amount': amount + prev_inactive[addr]['amount'], 'inactive_windows': prev_inactive[addr]['inactive_windows'] + [window_index]}
                else:
                    inactive_item = {'address': addr, 'amount': amount, 'inactive_windows': [window_index]}
                
                inactive.append(inactive_item)
            else:
                if addr in prev_inactive_addresses:
                    amount += prev_inactive[addr]['amount']
                rewards[addr] = amount

    return (rewards, inactive)


def report_prorata(path):    
    print(f'Generating amounts for SLICE rewards...')

    units = Decimal(input('How many units to distribute? '))

    EXPLODE_DECIMALS = Decimal(1e18)
    SLICE_UNITS = Decimal(int(units * EXPLODE_DECIMALS))
    
    stakers = [(stk['address'], stk['amount']) for stk in get_stakers_from_file(f'{path}/stakers.csv')]
    total_supply = Decimal(0)
    for (_, bal) in stakers:
        total_supply += bal

    prorata = Decimal(SLICE_UNITS * EXPLODE_DECIMALS / total_supply)

    rewards = {}
    rewarded = 0
    min_rewarded = SLICE_UNITS
    min_reward_staker = ''
    for (addr, bal) in stakers:
        staker_balance = Decimal(bal)
        staker_prorata = int(prorata * staker_balance / EXPLODE_DECIMALS)
        
        # calc min reward to add delta
        if staker_prorata < min_rewarded:
            min_rewarded = staker_prorata 
            min_reward_staker = addr
        
        rewards[addr] = staker_prorata
        rewarded += staker_prorata

    # add delta (due to calc inaccuracies) to min reward
    if min_rewarded != SLICE_UNITS:
        delta = int(SLICE_UNITS - rewarded)
        rewards[min_reward_staker] += delta
        rewarded += delta

    rewards_serialized = [{'address': addr, 'amount': amt} for (addr, amt) in rewards.items()]

    write_csv(rewards_serialized, f'{path}/slice_amounts.csv', ["address", "amount"])
    write_json(rewards_serialized, f'{path}/slice_amounts.json')
    
    print(f'Generated prorata distribution in {path}/slice_amount.csv !')

    window_index = int(input('Window index? (int) '))

    (rewards, unclaimed, compound_report) = compound_for_window(window_index, rewards) # compound rewards

    rewards_serialized = [{'address': addr, 'amount': amt} for (addr, amt) in rewards.items()]

    write_csv(rewards_serialized, f'{path}/slice_amounts_after_unclaimed.csv', ["address", "amount"])

    (rewards, inactive) = inactive_for_window(window_index, rewards, path=path) # account inactive stakers

    Path(f'reports/epochs/{window_index}').mkdir(parents=True, exist_ok=True)
    
    write_csv(unclaimed, f'{path}/unclaimed.csv', ['address', 'amount'])
    write_json(compound_report, f'reports/epochs/{window_index}/compound_report.json')
    write_json(inactive, f'reports/epochs/{window_index}/inactive.json')
    write_reward_window(window_index, rewards)

def report():
    epoch = input('What epoch? [month-year, {1-12}-{year}]: ')
    epoch = [int(token) for token in epoch.split("-")]
    (date, start_date, end_date) = get_timestamps(epoch[0], epoch[1])

    Path(f'reports/staking/{date.year}-{date.month}').mkdir(parents=True, exist_ok=True)

    print(f'Thank you. Reporting from {start_date} to {end_date}...')

    proposals = report_proposals(int(start_date.timestamp()), int(end_date.timestamp()))
    votes = report_votes(int(start_date.timestamp()), proposals)
    (voted, _) = report_voters(int(start_date.timestamp()), votes)
    print("Generating JSONs for distribution...")

    write_participation(int(start_date.timestamp()), voted)

    stakers = [{'address': addr, 'amount': amount} for (addr, amount) in get_stakers()]
    write_staking_csv(int(start_date.timestamp()), stakers, 'stakers.csv', stakers_fieldnames)

    report_prorata(f'reports/staking/{date.year}-{date.month}')