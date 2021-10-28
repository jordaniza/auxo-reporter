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
    with open(f'reports/staking/{date}/proposals.csv', 'w+') as f:
        fieldnames = ['id', 'title', 'author', 'choices', 'created', 'start', 'end']
        writer = csv.DictWriter(f, delimiter=',', fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(proposals)


def write_votes(start_timestamp, votes):
    date = datetime.date.fromtimestamp(start_timestamp)
    with open(f'reports/staking/{date}/votes.csv', 'w+') as f:
        fieldnames = ['voter', 'choice', 'proposal', 'created']
        writer = csv.DictWriter(f, delimiter=',', fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(votes)


def write_dictionaries(start_timestamp, dicts, filename, fieldnames):
    date = datetime.date.fromtimestamp(start_timestamp)
    with open(f'reports/staking/{date}/{filename}', 'w+') as f:
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
    with open(f'reports/staking/{date}/participation.json', 'w+') as f:
        voters = [v['address'] for v in voted]
        stakers = {web3.toChecksumAddress(addr): participation(addr, voters) for (addr, _) in get_stakers() }
        participation_json = json.dumps(stakers, indent=4)
        f.write(participation_json)


def write_to_slash(start_timestamp, not_voted):
    date = datetime.date.fromtimestamp(start_timestamp)
    with open(f'reports/staking/{date}/to-slash.json', 'w+') as f:
        voters = [v['address'] for v in not_voted]
        to_slash_json = json.dumps(voters, indent=4)
        f.write(to_slash_json)

def write_kpi_options(date, airdrop_map):
    with open(f'reports/staking/{date}/kpi-options.json', 'w+') as f:
        kpi_airdrop_json = json.dumps(airdrop_map, indent=4)
        f.write(kpi_airdrop_json)



def get_stakers():
    subgraph = "https://api.thegraph.com/subgraphs/name/pie-dao/vedough"
    query = '{ stakers(first: 1000) { id, accountVeTokenBalance } }'
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

    variables = {'space': "piedao.eth", 'proposals_in': proposals_ids}
    response = requests.post(snapshot_graphql, json={'query': votes_query, 'variables': variables})
    votes = response.json()['data']['votes']

    write_votes(start_timestamp, votes)

    return votes


def report_voters(start_timestamp, votes):
    stakers = get_stakers()
    voters = set([web3.toChecksumAddress(v['voter']) for v in votes])

    stakers_addrs = [web3.toChecksumAddress(addr) for (addr, _) in stakers]

    voted = [{'address': addr} for addr in stakers_addrs if addr in voters]
    
    # TODO: we add safes that staked here (hardcoded) while we ponder about how to deal with delegation
    voted.extend([{'address': address} for address in safes_staked])  
    
    not_voted = [{
        'address': addr
    } for addr in stakers_addrs if addr not in voters]

    write_dictionaries(start_timestamp, voted, 'voted.csv', ['address'])
    write_dictionaries(start_timestamp, not_voted, 'not_voted.csv', ['address'])

    return (voted, not_voted)


def report():
    month = int(input('What month? [1-12]: '))
    (date, start_date, end_date) = get_timestamps(month)

    Path(f'reports/staking/{date}').mkdir(parents=True, exist_ok=True)

    print(f'Thank you. Reporting from {start_date} to {end_date}...')

    proposals = report_proposals(int(start_date.timestamp()), int(end_date.timestamp()))
    votes = report_votes(int(start_date.timestamp()), proposals)
    (voted, not_voted) = report_voters(int(start_date.timestamp()), votes)
    print("Generating JSONs for distribution...")

    write_participation(int(start_date.timestamp()), voted)
    write_to_slash(int(start_date.timestamp()), not_voted)

def kpi_airdrop():
    Path(f'reports/airdrops').mkdir(parents=True, exist_ok=True)

    print(f'Generating airdrop amounts for KPI options..')

    EXPLODE_DECIMALS = Decimal(1e18)
    KPI_OPTIONS_UNITS = Decimal(10_000_000 * EXPLODE_DECIMALS)
    total_supply = Decimal(interface.ERC20(VEDOUGH_ADDRESS).totalSupply())
    prorata = Decimal(KPI_OPTIONS_UNITS * EXPLODE_DECIMALS / total_supply)
    
    stakers = get_stakers()
    airdrop = []
    airdropped = 0
    for (addr, bal) in stakers:
        staker_balance = Decimal(bal)
        staker_prorata = int(prorata * staker_balance / EXPLODE_DECIMALS)
        airdrop.append({"address": web3.toChecksumAddress(addr), "amount": staker_prorata})
        airdropped += staker_prorata
    
    with open(f'reports/airdrops/kpi_options.csv', 'w+') as f:
        writer = csv.DictWriter(f, delimiter=',', fieldnames=["address", "amount"])

        writer.writeheader()
        writer.writerows(airdrop)
    
    print(f'Generated report in reports/airdrops/kpi_options.csv')
    print(f'KPI options to airdrop: {airdropped}')
