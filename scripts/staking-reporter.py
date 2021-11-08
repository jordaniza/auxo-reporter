from pathlib import Path
from brownie import web3, interface, Wei
from decimal import Decimal

import csv
import requests
import datetime
import calendar
import json

safes_staked = map(web3.toChecksumAddress, ['0xea9f2e31ad16636f4e1af0012db569900401248a'])
VEDOUGH_ADDRESS = web3.toChecksumAddress('0xe6136f2e90eeea7280ae5a0a8e6f48fb222af945')
SLICE_ADDRESS = web3.toChecksumAddress('0x1083D743A1E53805a95249fEf7310D75029f7Cd6')

def yes_or_no(question):
    while "the answer is invalid":
        reply = str(input(f'{question} [y/n]: ')).lower().strip()
        if reply[:1] == 'y':
            return True
        if reply[:1] == 'n':
            return False

def get_timestamps(month):
    today = datetime.date.today()
    (_, n_days) = calendar.monthrange(today.year, month)

    date = datetime.date(today.year, month, 1)
    start_date = datetime.datetime(today.year, month, 1, 0, 0, 0)
    end_date = datetime.datetime(today.year, month, n_days, 23, 59, 59)

    return (date, start_date, end_date)


def write_proposals(start_timestamp, proposals):
    date = datetime.date.fromtimestamp(start_timestamp)
    with open(f'reports/staking/{date.year}-{date.month}/proposals.csv', 'w+') as f:
        fieldnames = ['id', 'title', 'author', 'choices', 'created', 'start', 'end']
        writer = csv.DictWriter(f, delimiter=',', fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(proposals)


def write_votes(start_timestamp, votes):
    date = datetime.date.fromtimestamp(start_timestamp)
    with open(f'reports/staking/{date.year}-{date.month}/votes.csv', 'w+') as f:
        fieldnames = ['voter', 'choice', 'proposal', 'created']
        writer = csv.DictWriter(f, delimiter=',', fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(votes)

def write_stakers(start_timestamp, stakers):
    date = datetime.date.fromtimestamp(start_timestamp)
    with open(f'reports/staking/{date.year}-{date.month}/stakers.csv', 'w+') as f:
        fieldnames = ['address', 'amount']
        writer = csv.DictWriter(f, delimiter=',', fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(stakers)


def write_dictionaries(start_timestamp, dicts, filename, fieldnames):
    date = datetime.date.fromtimestamp(start_timestamp)
    with open(f'reports/staking/{date.year}-{date.month}/{filename}', 'w+') as f:
        writer = csv.DictWriter(f, delimiter=',', fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(dicts)

def participation(address, voters):
    if web3.toChecksumAddress(address) in voters:
        return 1
    else:
        return 0

def write_participation(start_timestamp, voted):
    date = datetime.date.fromtimestamp(start_timestamp)
    with open(f'reports/staking/{date.year}-{date.month}/participation.json', 'w+') as f:
        voters = [v['address'] for v in voted]
        stakers = {web3.toChecksumAddress(addr): participation(addr, voters) for (addr, _) in get_stakers() }
        participation_json = json.dumps(stakers, indent=4)
        f.write(participation_json)

def write_to_slash(start_timestamp, not_voted):
    date = datetime.date.fromtimestamp(start_timestamp)
    with open(f'reports/staking/{date.year}-{date.month}/to-slash.json', 'w+') as f:
        voters = [v['address'] for v in not_voted]
        to_slash_json = json.dumps(voters, indent=4)
        f.write(to_slash_json)

def get_delegates():
    subgraph = "https://api.thegraph.com/subgraphs/name/pie-dao/vedough"
    query = '{ delegates(first: 1000) { delegator, delegate } }'
    response = requests.post(subgraph, json={'query': query})
    subgraph_delegates = response.json()['data']['delegates']

    return [(web3.toChecksumAddress(d['delegator']), web3.toChecksumAddress(d['delegate'])) for d in subgraph_delegates]

def get_stakers():
    subgraph = "https://api.thegraph.com/subgraphs/name/pie-dao/vedough"
    query = '{ stakers(first: 1000, block: {number: 13527858}) { id, accountVeTokenBalance } }'
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
    write_proposals(start_timestamp, proposals)

    return proposals


def report_votes(start_timestamp, proposals):
    proposals_ids = [p['id'] for p in proposals]

    snapshot_graphql = 'https://hub.snapshot.org/graphql'
    votes_query = """
        query($space: String, $proposals: [String]) { 
            votes(first: 1000, where: {space: $space, proposal_in: $proposals}) {
                voter
                choice
                proposal {
                    id
                }
                created
            } 
        }
    """

    variables = {'space': "piedao.eth", 'proposals': proposals_ids}
    response = requests.post(snapshot_graphql, json={'query': votes_query, 'variables': variables})
    votes = response.json()['data']['votes']

    write_votes(start_timestamp, votes)

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
    not_voted.extend([{'address': delegator}] for (delegator, delegate) in delegates if delegate not in voters)

    write_dictionaries(start_timestamp, voted, 'voted.csv', ['address'])
    write_dictionaries(start_timestamp, not_voted, 'not_voted.csv', ['address'])

    return (voted, not_voted)

def get_stakers_from_voters_file(f):
    with open(f, 'r') as voters_file:
        reader = csv.DictReader(voters_file,fieldnames=["address"])
        stakers = []

        for voter in reader:
            if reader.line_num == 1:
                continue
            
            checksum_address = web3.toChecksumAddress(voter['address'])
            stakers.append(checksum_address)

    return stakers

def write_reward_window(window_index, rewards, rewarded):
    reward_window = {'chainId': 1, 'rewardToken': SLICE_ADDRESS, 'windowIndex': window_index, 'totalRewardsDistributed': str(rewarded)}
    recipients = {reward["address"] : {"amount": str(reward["amount"]), "metaData": {"reason": [f'Distribution for epoch {window_index}']}} for reward in rewards}
    reward_window['recipients'] = recipients

    with open(f'reports/reward_windows/{window_index}/{window_index}.json', 'w+') as f:
        reward_window_json = json.dumps(reward_window, indent=4)
        f.write(reward_window_json)

def report_prorata():    
    print(f'Generating amounts for SLICE rewards...')

    vedough = interface.ERC20(VEDOUGH_ADDRESS)

    EXPLODE_DECIMALS = Decimal(1e18)
    SLICE_UNITS = Decimal(1350000 * EXPLODE_DECIMALS)
    
    voters = get_stakers_from_voters_file('reports/staking/2021-10/voted.csv')
    stakers = [(web3.toChecksumAddress(addr), Decimal(bal)) for (addr, bal) in get_stakers() if web3.toChecksumAddress(addr) in voters]
    total_supply = Decimal(0)
    for (_, bal) in stakers:
        total_supply += bal

    prorata = Decimal(SLICE_UNITS * EXPLODE_DECIMALS / total_supply)

    rewards = []
    rewarded = 0
    for (addr, bal) in stakers:
        staker_balance = Decimal(bal)
        staker_prorata = int(prorata * staker_balance / EXPLODE_DECIMALS)
        rewards.append({"address": web3.toChecksumAddress(addr), "amount": staker_prorata})
        rewarded += staker_prorata
        
    with open(f'reports/staking/2021-10/slice_amounts.csv', 'w+') as f:
        writer = csv.DictWriter(f, delimiter=',', fieldnames=["address", "amount"])

        writer.writeheader()
        writer.writerows(rewards)
    
    with open(f'reports/staking/2021-10/slice_amounts.json', 'w+') as f:
        slice_amounts_json = json.dumps(rewards, indent=4)
        f.write(slice_amounts_json)
    
    print(f'Generated report in reports/staking/2021-10/slice_amount.csv')
    print(f'SLICE to distribute: {rewarded}')

    window_index = int(input('Window index number? [1-12]: '))
    Path(f'reports/reward_windows/{window_index}').mkdir(parents=True, exist_ok=True)
    write_reward_window(window_index, rewards, rewarded)

def report():
    month = int(input('What month? [1-12]: '))
    (date, start_date, end_date) = get_timestamps(month)

    Path(f'reports/staking/{date.year}-{date.month}').mkdir(parents=True, exist_ok=True)

    print(f'Thank you. Reporting from {start_date} to {end_date}...')

    proposals = report_proposals(int(start_date.timestamp()), int(end_date.timestamp()))
    votes = report_votes(int(start_date.timestamp()), proposals)
    (voted, not_voted) = report_voters(int(start_date.timestamp()), votes)
    print("Generating JSONs for distribution...")

    write_participation(int(start_date.timestamp()), voted)
    write_to_slash(int(start_date.timestamp()), not_voted)

    stakers = [{'address': addr, 'amount': amount} for (addr, amount) in get_stakers()]
    write_stakers(int(start_date.timestamp()), stakers)

def kpi_airdrop():
    Path(f'reports/airdrops/kpi').mkdir(parents=True, exist_ok=True)

    print(f'Generating airdrop amounts for KPI options..')

    EXPLODE_DECIMALS = Decimal(1e18)
    KPI_OPTIONS_UNITS = Decimal(10_000_000 * EXPLODE_DECIMALS)
    
    stakers = get_stakers()
    total_supply = Decimal(0)
    for (_, bal) in stakers:
        total_supply += Decimal(bal)

    prorata = Decimal(KPI_OPTIONS_UNITS * EXPLODE_DECIMALS / total_supply)

    airdrop = []
    airdropped = 0
    for (addr, bal) in stakers:
        staker_balance = Decimal(bal)
        staker_prorata = int(prorata * staker_balance / EXPLODE_DECIMALS)
        airdrop.append({"address": web3.toChecksumAddress(addr), "amount": staker_prorata})
        airdropped += staker_prorata
    
    with open('reports/airdrops/kpi/kpi_options.csv', 'w+') as f:
        writer = csv.DictWriter(f, delimiter=',', fieldnames=["address", "amount"])

        writer.writeheader()
        writer.writerows(airdrop)
    
    with open('reports/airdrops/kpi/kpi_options.json', 'w+') as f:
        airdrop_json = json.dumps(airdrop, indent=4)
        f.write(airdrop_json)
    
    with open('reports/airdrops/kpi/claims.json', 'w+') as f:
        reward_window = {'chainId': 1, 'rewardToken': '', 'windowIndex': '1', 'totalRewardsDistributed': str(airdropped)}
        recipients = {reward["address"] : {"amount": str(reward["amount"]), "metaData": {"reason": ['wKPI-DOUGH airdrop']}} for reward in airdrop}
        reward_window['recipients'] = recipients

        reward_window_json = json.dumps(reward_window, indent=4)
        f.write(reward_window_json)

    
    print(f'Generated report in reports/airdrops/kpi_options.csv')
    print(f'KPI options to airdrop: {airdropped}')
