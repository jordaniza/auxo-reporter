from eth_utils import to_checksum_address

import requests
from helpers import yes_or_no


def subgraph_query(query, response_key):
    subgraph = "https://api.thegraph.com/subgraphs/name/pie-dao/vedough"
    response = requests.post(subgraph, json={"query": query}).json()
    return response["data"][response_key]


def get_stakers(conf):
    subgraph_stakers = subgraph_query(
        f"{{ stakers(first: 1000, block: {{number: {conf['block_snapshot']}}}) {{ id, accountVeTokenBalance }} }}",
        "stakers",
    )

    return [
        (to_checksum_address(s["id"]), s["accountVeTokenBalance"])
        for s in subgraph_stakers
    ]


def filter_votes_by_proposal(votes):
    proposals_map = {v["proposal"]["id"]: v["proposal"] for v in votes}

    if yes_or_no("Do you want to filter proposals?"):
        proposals = []
        proposals_ids = []
        for (p_id, p) in proposals_map.items():
            title = p["title"]
            if yes_or_no(f"Is proposal {title} a valid proposal?"):
                proposals.append(p)
                proposals_ids.append(p_id)
        return ([v for v in votes if v["proposal"]["id"] in proposals_ids], proposals)
    else:
        return (votes, list(proposals_map.values()))


def get_delegates():
    delegates = subgraph_query(
        "{ delegates(first: 1000) { delegator, delegate } }", "delegates"
    )

    return list(
        map(
            lambda addrs: tuple(map(to_checksum_address, addrs)),
            [(d["delegator"], d["delegate"]) for d in delegates],
        )
    )


def get_voters(votes, stakers):
    delegates = get_delegates()

    voters = set([to_checksum_address(v["voter"]) for v in votes])
    stakers_addrs = [to_checksum_address(addr) for (addr, _) in stakers]
    delegators = [delegator for (delegator, _) in delegates]

    stakers_addrs_no_delegators = [
        addr for addr in stakers_addrs if addr not in delegators
    ]

    voted = [addr for addr in stakers_addrs_no_delegators if addr in voters] + [
        delegator for (delegator, delegate) in delegates if delegate in voters
    ]

    not_voted = [addr for addr in stakers_addrs_no_delegators if addr not in voters] + [
        delegator for (delegator, delegate) in delegates if delegate not in voters
    ]

    return (voted, not_voted)


def get_votes(conf, stakers):
    snapshot_graphql = "https://hub.snapshot.org/graphql"
    votes_query = """
        query($skip: Int, $space: String, $created_gte: Int, $created_lte: Int) { 
            votes(skip: $skip, first: 1000, where: {space: $space, created_gte: $created_gte, created_lte: $created_lte}) {
                voter
                choice
                created
                proposal {
                    id
                    title
                    author
                    created
                    start
                    end
                    choices
                }
            }
        }
    """

    variables = {
        "skip": 0,
        "space": "piedao.eth",
        "created_gte": conf["start_timestamp"],
        "created_lte": conf["end_timestamp"],
    }

    response = requests.post(
        snapshot_graphql, json={"query": votes_query, "variables": variables}
    )

    tmp_votes = response.json()["data"]["votes"]
    votes = tmp_votes
    while len(tmp_votes) > 0:
        variables["skip"] = len(votes)

        response = requests.post(
            snapshot_graphql, json={"query": votes_query, "variables": variables}
        )

        tmp_votes = response.json()["data"]["votes"]
        votes += tmp_votes

    (votes, proposals) = filter_votes_by_proposal(votes)
    (voters, non_voters) = get_voters(votes, stakers)

    return (votes, proposals, voters, non_voters)


def get_claimed_for_window(window_index):
    snapshot_graphql = "https://api.thegraph.com/subgraphs/name/pie-dao/vedough"
    rewards_query = """
        query($windowId: BigInt) { 
            rewards(first: 1000, where: {windowIndex: $windowId}) {
                account
            }
        }
    """

    variables = {"windowId": window_index}
    response = requests.post(
        snapshot_graphql, json={"query": rewards_query, "variables": variables}
    )
    claimed = response.json()["data"]["rewards"]

    return [to_checksum_address(account["account"]) for account in claimed]
