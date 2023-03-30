"""
Create the JSON Object for on-chain and off-chain votes, using the existing mocks as a template
https://docs.google.com/spreadsheets/d/11-WOWGjQDJJpKAUqJN0JsxzyMGhoEhV0Pt-isW5NHxk/edit#gid=0
"""
import json
from dataclasses import dataclass

from pydantic import parse_file_as

from reporter.env import ADDRESSES
from reporter.models import OffChainVote
from reporter.utils import write_json

BASE_VEAUXO_QTY = 100


@dataclass
class User:
    address: str
    ARV_amount: str = str(BASE_VEAUXO_QTY)
    boosted_amount: str = str(BASE_VEAUXO_QTY)
    eligible_amount: str = str(BASE_VEAUXO_QTY)
    active_on_chain: bool = False
    active_snapshot: bool = False
    xAUXO_amount: str = "0"
    staked_xAUXO: bool = False

    @property
    def _template_on_chain(self):
        with open("reporter/test/stubs/votes/onchain-votes.json") as j:
            api_resp = json.load(j)
        return api_resp["data"]["voteCasts"][0]

    @property
    def _template_off_chain(self) -> OffChainVote:
        return parse_file_as(
            list[OffChainVote], "reporter/test/stubs/votes/votes.json"
        )[0]

    @property
    def _template_token_holding(self):
        with open("reporter/test/stubs/tokens/xauxo.json") as j:
            api_resp = json.load(j)
        return api_resp["data"]["erc20Contract"]["balances"][0]

    def create_on_chain_vote(self):
        template = self._template_on_chain
        template["voter"] = {"id": self.address}
        return template

    def create_off_chain_vote(self) -> OffChainVote:
        template: OffChainVote = self._template_off_chain
        template.voter = self.address
        return template

    def create_xauxo_holding(self):
        template = self._template_token_holding
        template["account"] = {"id": self.address}
        template["valueExact"] = self.xAUXO_amount
        return template

    def create_veauxo_holding(self):
        template = self._template_token_holding
        template["account"] = {"id": self.address}
        template["valueExact"] = self.ARV_amount
        return template


# setup the users
users = [
    User(
        "0x0000000000000000000000000000000000000001",
        active_on_chain=True,
        boosted_amount=str(BASE_VEAUXO_QTY / 2),
    ),
    User(
        "0x0000000000000000000000000000000000000002",
        active_snapshot=True,
        boosted_amount=str(BASE_VEAUXO_QTY * (3 / 4)),
    ),
    User(
        "0x0000000000000000000000000000000000000003",
        active_on_chain=True,
        active_snapshot=True,
        boosted_amount=str(BASE_VEAUXO_QTY / 2),
    ),
    User(
        "0x0000000000000000000000000000000000000004",
        eligible_amount="0",
        boosted_amount=str(BASE_VEAUXO_QTY * (3 / 4)),
    ),
    User(
        ADDRESSES.STAKING_MANAGER,
        eligible_amount="0",
        ARV_amount="400",
    ),
    User(
        "0x0000000000000000000000000000000000000005",
        xAUXO_amount="200",
        ARV_amount="0",
        eligible_amount="0",
        boosted_amount="0",
    ),
    User(
        "0x0000000000000000000000000000000000000006",
        ARV_amount="0",
        eligible_amount="0",
        xAUXO_amount="200",
        staked_xAUXO=True,
        boosted_amount="0",
    ),
]


def test_go():
    votes_on = []
    votes_off = []
    xauxo_stakers = {}
    xauxo_holders = []
    veauxo_holders = []
    veauxo_boost_data = {}
    for u in users:
        if u.active_on_chain:
            votes_on.append(u.create_on_chain_vote())
        if u.active_snapshot:
            votes_off.append(u.create_off_chain_vote())
        if u.staked_xAUXO:
            xauxo_stakers[u.address] = True
        else:
            xauxo_stakers[u.address] = False
        if int(u.xAUXO_amount) > 0:
            xauxo_holders.append(u.create_xauxo_holding())
        if int(u.ARV_amount) > 0:
            veauxo_holders.append(u.create_veauxo_holding())
            veauxo_boost_data[u.address] = u.boosted_amount

    write_json(
        {"data": {"voteCasts": [v for v in votes_on]}},
        "reporter/test/scenario_testing/votes_on.json",
    )
    write_json(
        [v.dict() for v in votes_off], "reporter/test/scenario_testing/votes_off.json"
    )

    write_json(
        {"data": {"erc20Contract": {"balances": [v for v in veauxo_holders]}}},
        "reporter/test/scenario_testing/mock_veauxo.json",
    )
    write_json(
        {"data": {"erc20Contract": {"balances": [x for x in xauxo_holders]}}},
        "reporter/test/scenario_testing/mock_xauxo.json",
    )

    write_json(xauxo_stakers, "reporter/test/scenario_testing/xauxo_stakers.json")
    write_json(veauxo_boost_data, "reporter/test/scenario_testing/veauxo_boosted.json")
