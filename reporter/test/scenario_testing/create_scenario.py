"""
Create the JSON Object for on-chain and off-chain votes, using the existing mocks as a template
https://docs.google.com/spreadsheets/d/11-WOWGjQDJJpKAUqJN0JsxzyMGhoEhV0Pt-isW5NHxk/edit#gid=0
"""
import json
import os
from dataclasses import dataclass
import time

from pydantic import parse_file_as

from reporter.models import Vote as OffChainVote
from reporter.utils import write_json

# initial ARV amount for each user
BASE_ARV_QTY = 1000 * 10**18


@dataclass
class User:
    address: str
    ARV_amount: str = str(BASE_ARV_QTY)
    boosted_amount: str = str(BASE_ARV_QTY)
    active_onchain: bool = False
    active_offchain: bool = False
    PRV_amount: str = "0"
    staked_PRV: bool = False
    _stubs_dir: str = "reporter/test/stubs"

    @property
    def _template_on_chain(self):
        with open(f"{self._stubs_dir}/votes/onchain-votes.json") as j:
            api_resp = json.load(j)
        return api_resp["data"]["voteCasts"][0]

    @property
    def _template_off_chain(self) -> OffChainVote:
        return parse_file_as(list[OffChainVote], f"{self._stubs_dir}/votes/votes.json")[
            0
        ]

    @property
    def _template_token_holding(self):
        with open(f"{self._stubs_dir}/tokens/prv.json") as j:
            api_resp = json.load(j)
        return api_resp["data"]["erc20Contract"]["balances"][0]

    @property
    def _template_prv_stake(self):
        return self._template_token_holding

    @property
    def is_active(self):
        return self.active_onchain or self.active_offchain

    def create_on_chain_vote(self):
        template = self._template_on_chain
        template["voter"] = {"id": self.address}
        return template

    def create_off_chain_vote(self) -> OffChainVote:
        template: OffChainVote = self._template_off_chain
        template.voter = self.address
        return template

    def create_prv_holding(self):
        template = self._template_token_holding
        template["account"] = {"id": self.address}
        template["valueExact"] = self.PRV_amount
        return template

    def create_arv_holding(self):
        template = self._template_token_holding
        template["account"] = {"id": self.address}
        template["valueExact"] = self.ARV_amount
        return template

    def create_arv_lock(self):
        return [self.ARV_amount, int(time.time()), 86400 * 36]

    def create_prv_depositor(self):
        template = self._template_token_holding
        template["account"] = {"id": self.address}
        template["valueExact"] = self.ARV_amount
        return template

    def create_prv_deposit(self):
        return self.PRV_amount

    @staticmethod
    def ssn(number):
        """suppress scientific notation"""
        return "{:.0f}".format(number)


# setup the users
users_scenario = [
    [
        # ARV Users
        User(
            address="0x0000000000000000000000000000000000000001",
            active_onchain=True,
        ),
        User(
            address="0x0000000000000000000000000000000000000002",
            active_offchain=True,
        ),
        User(
            address="0x0000000000000000000000000000000000000003",
            active_onchain=True,
            active_offchain=True,
        ),
        # Inactive ARV Users
        User(
            address="0x0000000000000000000000000000000000000004",
        ),
        User(
            address="0x0000000000000000000000000000000000000005",
        ),
        # PRV Users
        User(
            address="0x0000000000000000000000000000000000000006",
            ARV_amount="0",
            PRV_amount=str(BASE_ARV_QTY),
            staked_PRV=True,
        ),
        User(
            address="0x0000000000000000000000000000000000000007",
            ARV_amount="0",
            PRV_amount=str(BASE_ARV_QTY),
            staked_PRV=True,
        ),
        User(
            address="0x0000000000000000000000000000000000000008",
            ARV_amount="0",
            PRV_amount=str(BASE_ARV_QTY),
            staked_PRV=True,
        ),
        # unstaked PRV Users
        User(
            address="0x0000000000000000000000000000000000000009",
            ARV_amount="0",
            PRV_amount=str(BASE_ARV_QTY),
            staked_PRV=False,
        ),
    ],
    # next scenario
    [
        # ARV Users
        User(
            address="0x0000000000000000000000000000000000000001",
            active_onchain=True,
            boosted_amount=User.ssn((BASE_ARV_QTY * 2) / 3),
        ),
        User(
            address="0x0000000000000000000000000000000000000002",
            active_offchain=True,
            boosted_amount=User.ssn((BASE_ARV_QTY * 3) / 4),
        ),
        User(
            address="0x0000000000000000000000000000000000000003",
            active_onchain=True,
            active_offchain=True,
        ),
        User(
            address="0x0000000000000000000000000000000000000004",
            active_onchain=True,
            ARV_amount=str(1500 * 10**18),
            boosted_amount=str(1500 * 10**18),
        ),
        # Inactive ARV Users
        User(
            address="0x0000000000000000000000000000000000000005",
        ),
        # PRV Users
        User(
            address="0x0000000000000000000000000000000000000006",
            ARV_amount="0",
            PRV_amount=str(BASE_ARV_QTY),
            staked_PRV=True,
        ),
        User(
            address="0x0000000000000000000000000000000000000007",
            ARV_amount="0",
            PRV_amount=str(User.ssn(BASE_ARV_QTY)),
            staked_PRV=True,
        ),
        # unstaked PRV Users
        User(
            address="0x0000000000000000000000000000000000000008",
            ARV_amount="0",
            PRV_amount=str(BASE_ARV_QTY),
            staked_PRV=False,
        ),
    ],
    # works with all ARV not fully staked
    [
        # ARV Users
        User(
            address="0x0000000000000000000000000000000000000001",
            active_onchain=True,
            boosted_amount=User.ssn((BASE_ARV_QTY * 9) / 10),
        ),
        User(
            address="0x0000000000000000000000000000000000000002",
            active_offchain=True,
            boosted_amount=User.ssn((BASE_ARV_QTY * 7) / 10),
        ),
        # Inactive ARV Users
        User(
            address="0x0000000000000000000000000000000000000004",
        ),
        User(
            address="0x0000000000000000000000000000000000000005",
        ),
        # PRV Users
        User(
            address="0x0000000000000000000000000000000000000006",
            ARV_amount="0",
            PRV_amount=str(BASE_ARV_QTY),
            staked_PRV=True,
        ),
        User(
            address="0x0000000000000000000000000000000000000007",
            ARV_amount="0",
            PRV_amount=str(BASE_ARV_QTY),
            staked_PRV=True,
        ),
        User(
            address="0x0000000000000000000000000000000000000008",
            ARV_amount="0",
            PRV_amount=str(BASE_ARV_QTY),
            staked_PRV=True,
        ),
        # unstaked PRV Users
        User(
            address="0x0000000000000000000000000000000000000009",
            ARV_amount="0",
            PRV_amount=str(BASE_ARV_QTY),
            staked_PRV=False,
        ),
    ],
]


def init_users(scenario: int):
    votes_on = []
    votes_off = []
    prv_stakers = {}
    prv_holders = []
    arv_holders = []
    arv_boost_data = {}
    arv_locks = {}
    prv_depositeds = []
    prv_stakes = {}
    users = users_scenario[scenario]

    for u in users:
        if u.active_onchain:
            votes_on.append(u.create_on_chain_vote())

        if u.active_offchain:
            votes_off.append(u.create_off_chain_vote())

        if u.staked_PRV or int(u.PRV_amount) > 0:
            prv_depositeds.append(u.create_prv_depositor())

        if u.staked_PRV:
            prv_stakers[u.address] = True
            prv_stakes[u.address] = u.create_prv_deposit()
        else:
            prv_stakers[u.address] = False

        if int(u.PRV_amount) > 0:
            prv_holders.append(u.create_prv_holding())

        if int(u.ARV_amount) > 0:
            arv_holders.append(u.create_arv_holding())
            arv_boost_data[u.address] = str(u.boosted_amount)
            arv_locks[u.address] = u.create_arv_lock()

    directory = f"reporter/test/scenario_testing/{scenario}"
    if not os.path.exists(directory):
        os.makedirs(directory)

    write_json(
        {"data": {"voteCasts": [v for v in votes_on]}},
        directory + "/votes_on.json",
    )
    write_json(
        [v.dict() for v in votes_off],
        directory + "/votes_off.json",
    )

    write_json(
        {"data": {"erc20Contract": {"balances": [v for v in arv_holders]}}},
        directory + "/mock_arv.json",
    )
    write_json(
        {"data": {"erc20Contract": {"balances": [x for x in prv_holders]}}},
        directory + "/mock_prv.json",
    )

    write_json(
        {"data": {"depositeds": prv_depositeds}}, directory + "/prv_depositeds.json"
    )

    write_json(prv_stakes, directory + "/prv_stakes.json")

    write_json(prv_stakers, directory + "/prv_stakers.json")
    write_json(arv_boost_data, directory + "/arv_boosted.json")

    write_json(arv_locks, directory + "/arv_locks.json")
    return users


if __name__ == "__main__":
    SCENARIO_NUMBER = 999
    init_users(SCENARIO_NUMBER)
