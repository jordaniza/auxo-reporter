from reporter.helpers import get_db
from decimal import *
from reporter.account import (
    AccountState,
)
from reporter.conf_generator import load_conf, Config, RewardToken

import datetime
import itertools
import functools

from eth_utils import to_checksum_address
from pydantic import BaseModel, parse_obj_as, validator
from typing import TypeVar, Any, TypedDict, Tuple, Optional
import requests
from dataclasses import dataclass
from tinydb import TinyDB

T = TypeVar("T")


@dataclass
class SUBGRAPHS:
    VEDOUGH = "https://api.thegraph.com/subgraphs/name/pie-dao/vedough"
    SNAPSHOT = "https://hub.snapshot.org/graphql"


class Staker(BaseModel):
    id: str
    accountVeTokenBalance: str

    @validator("id")
    @classmethod
    def checksum_id(cls, _id: str) -> str:
        return to_checksum_address(_id)


class Stakers(BaseModel):
    stakers: list[Staker]


class GraphQLConfig(TypedDict):
    query: str
    variables: dict[str, Any]


class EmptyQueryError(Exception):
    pass


class VoteProposal(BaseModel):
    id: str
    title: str
    author: str
    created: int
    start: int
    end: int
    choices: list[str]


class Vote(BaseModel):
    voter: str
    choice: int
    created: int
    proposal: VoteProposal

    @validator("voter")
    @classmethod
    def checksum_id(cls, _voter: str) -> str:
        return to_checksum_address(_voter)


class Delegate(BaseModel):
    delegator: str
    delegate: str

    @validator("delegator")
    @classmethod
    def checksum_delegator(cls, d: str) -> str:
        return to_checksum_address(d)

    @validator("delegate")
    @classmethod
    def checksum_delegate(cls, d: str) -> str:
        return to_checksum_address(d)


def graphql_iterate_query(url: str, accessor: str, params: GraphQLConfig) -> list[T]:
    res: dict[str, Any] = requests.post(url, json=params).json()
    if not res:
        raise EmptyQueryError(f"No results for graph query to {url}")

    results: list[T] = res["data"][accessor]
    container = results
    while len(container) > 0:
        params["variables"]["skip"] = len(container)
        res = requests.post(url, json=params).json()
        container = res["data"][accessor]
        results += container
    return results


# How to fix the 'first' problem?
def get_stakers_v2(conf: Config) -> list[Staker]:
    query = f"{{ stakers(first: 1000, block: {{number: {conf.block_snapshot}}}) {{ id, accountVeTokenBalance }} }}"
    graphQl_response = requests.post(
        url=SUBGRAPHS.VEDOUGH, json={"query": query}
    ).json()
    return parse_obj_as(Stakers, graphQl_response.get("data")).stakers


def get_votes_v2(conf: Config):
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
        "created_gte": conf.start_timestamp,
        "created_lte": conf.end_timestamp,
    }

    votes: list[Any] = graphql_iterate_query(
        SUBGRAPHS.SNAPSHOT, "votes", dict(query=votes_query, variables=variables)
    )
    return votes


def parse_votes(conf: Config) -> list[Vote]:
    return parse_obj_as(list[Vote], get_votes_v2(conf))


def yes_or_no(question: str):
    while "the answer is invalid":
        reply = input(f"{question} [y/N]: ")
        if not reply:
            return False
        reply = str(reply).lower().strip()
        if reply[:1] == "y":
            return True
        if reply[:1] == "n":
            return False


def filter_votes_by_proposal_v2(
    votes: list[Vote],
) -> Tuple[list[Vote], list[VoteProposal]]:
    unique_proposals = {v.proposal.id: v.proposal for v in votes}
    if yes_or_no("Do you want to filter proposals?"):
        proposals = []
        proposals_ids = []
        for p in unique_proposals.values():

            if yes_or_no(f"Is proposal {p.title} a valid proposal?"):
                proposals.append(p)
                proposals_ids.append(p.id)

        return ([v for v in votes if v.proposal.id in proposals_ids], proposals)

    else:
        return (votes, list(unique_proposals.values()))


def get_delegates_v2() -> list[Delegate]:
    query = "{ delegates(first: 1000) { delegator, delegate } }"
    delegates = requests.post(SUBGRAPHS.VEDOUGH, json={"query": query})
    delegate_data = delegates.json().get("data")
    return parse_obj_as(list[Delegate], delegate_data.get("delegates"))


def unique(ls: list[T]) -> list[T]:
    return list(set(ls))


def get_voters_v2(votes: list[Vote], stakers: list[Staker], delegates: list[Delegate]):
    voters = set([v.voter for v in votes])
    stakers_addrs = [s.id for s in stakers]

    stakers_addrs_no_delegators = [
        addr for addr in stakers_addrs if addr not in delegates
    ]

    voted = [addr for addr in stakers_addrs_no_delegators if addr in voters] + [
        d.delegator for d in delegates if d.delegate in voters
    ]

    not_voted = [addr for addr in stakers_addrs_no_delegators if addr not in voters] + [
        d.delegator for d in delegates if d.delegate not in voters
    ]

    return (unique(voted), unique(not_voted))


def get_vote_data(conf: Config, stakers: list[Staker]):
    delegates = get_delegates_v2()
    votes = parse_votes(conf)
    (votes, proposals) = filter_votes_by_proposal_v2(votes)
    (voters, non_voters) = get_voters_v2(votes, stakers, delegates)

    return (votes, proposals, voters, non_voters)


class Account(BaseModel):
    address: str
    vetoken_balance: str
    rewards: list[RewardToken]
    state: AccountState


def init_accounts_v2(stakers: list[Staker], voters: list[str]) -> list[Account]:
    return [
        Account(
            address=staker.id,
            vetoken_balance=staker.accountVeTokenBalance,
            state=AccountState.ACTIVE if staker.id in voters else AccountState.SLASHED,
            rewards=[],
        )
        for staker in stakers
    ]


def filter_state(accounts: list[Account], state: AccountState) -> list[Account]:
    return list(filter(lambda a: a.state == state, accounts))


def distribute_v2(account: Account, pro_rata: Decimal, reward: RewardToken) -> Account:
    account_reward = 0
    if account.state == AccountState.ACTIVE:
        account_reward = int(
            pro_rata * Decimal(account.vetoken_balance) / Decimal(10**reward.decimals)
        )

    account.rewards.append(
        RewardToken(token=reward.token, amount=account_reward, decimals=reward.decimals)
    )
    return account


class MissingRewardException(Exception):
    pass


def find_reward(token: str, account: Account) -> RewardToken:
    found_token = next(filter(lambda r: r.token == token, account.rewards))
    if not found_token:
        raise MissingRewardException(
            f"Could not find {token=} for user {account.address}"
        )
    return found_token


class RewardSummary(RewardToken):
    pro_rata: str

    @validator("pro_rata")
    @classmethod
    def transform_pro_rata(cls, p: str):
        if float(p) >= 1:
            return str(int(float(p)))
        else:
            return f"{float(p):.18f}"


class VeTokenStats(BaseModel):
    total: str
    active: str
    inactive: str


def vetokens_by_status(
    accounts: list[Account], state: Optional[AccountState] = None
) -> Decimal:
    accounts_to_summarize = accounts
    if state:
        accounts_to_summarize = filter_state(accounts, state)
    return functools.reduce(
        lambda running_total, account: running_total + Decimal(account.vetoken_balance),
        accounts_to_summarize,
        Decimal(0),
    )


def compute_distribution_v2(
    conf: Config, accounts: list[Account]
) -> Tuple[list[Account], list[RewardSummary], VeTokenStats]:

    # get accounts and vetokens
    total_active_vetokens = vetokens_by_status(accounts, AccountState.ACTIVE)
    total_slashed_vetokens = vetokens_by_status(accounts, AccountState.SLASHED)
    total_vetokens = vetokens_by_status(accounts, None)

    distribution_rewards: list[RewardSummary] = []

    veTokenStats = VeTokenStats(
        total=str(int(total_vetokens)),
        active=str(int(total_active_vetokens)),
        inactive=str(int(total_slashed_vetokens)),
    )

    for reward in conf.rewards:

        pro_rata = (Decimal(reward.amount) / total_active_vetokens) * Decimal(
            10**reward.decimals
        )

        # append to existing accounts
        accounts = list(
            map(
                distribute_v2,
                accounts,
                itertools.repeat(pro_rata),
                itertools.repeat(reward),
            )
        )

        distribution_rewards.append(
            RewardSummary(
                **reward.dict(),
                pro_rata=str(pro_rata),
            )
        )
        # TODO remainder

    return (accounts, distribution_rewards, veTokenStats)


def write_governance_stats(
    db: TinyDB,
    stakers: list[Staker],
    votes: list[Vote],
    proposals: list[VoteProposal],
    voters: list[str],
    non_voters: list[str],
    rewards: list[RewardSummary],
    veTokenStats: VeTokenStats,
):
    db.table("governance_stats").insert(
        {
            "stakers": [s.dict() for s in stakers],
            "votes": [v.dict() for v in votes],
            "proposals": [p.dict() for p in proposals],
            "voters": voters,
            "non_voters": non_voters,
            "rewards": [r.dict() for r in rewards],
            "veTokenStats": veTokenStats.dict(),
        },
    )


def write_accounts_and_distribution(
    db: TinyDB, accounts: list[Account], distribution: list[Account]
):
    db.table("accounts").insert_multiple([a.dict() for a in accounts])
    db.table("distribution").insert_multiple([d.dict() for d in distribution])


def build_v2(path: str):
    conf = load_conf(path)

    getcontext().prec = 42

    db = get_db(path, drop=True)

    start_date = datetime.date.fromtimestamp(conf.start_timestamp)
    end_date = datetime.date.fromtimestamp(conf.end_timestamp)
    print(f"⚗ Building database from {start_date} to {end_date}...")

    stakers = get_stakers_v2(conf)

    (votes, proposals, voters, non_voters) = get_vote_data(conf, stakers)

    accounts = init_accounts_v2(stakers, voters)
    (distribution, reward_summaries, vetoken_stats) = compute_distribution_v2(
        conf, accounts
    )
    write_accounts_and_distribution(db, accounts, distribution)
    write_governance_stats(
        db,
        stakers,
        votes,
        proposals,
        voters,
        non_voters,
        reward_summaries,
        vetoken_stats,
    )
