from typing import Optional

import eth_utils as eth
from pydantic import BaseModel, validator

from reporter.models.types import EthereumAddress, IDAddressDict


class Proposal(BaseModel):
    """
    Snapshot vote data fetch from the graph for a given proposal. Proposals are voted on by users.
    :param `id`: proposal id, hex number but not eth address
    :param `author`: eth address of the proposal creator, checksummed on read
    :param `choices`: typically `FOR`, `AGAINST`, `ABSTAIN` or something similar
    """

    id: str
    title: str
    author: EthereumAddress
    created: int
    start: int
    end: int
    choices: Optional[list[str]]

    @validator("author")
    @classmethod
    def checksum_id(cls, _author: str) -> str:
        return eth.to_checksum_address(_author)


class Vote(BaseModel):
    """
    Vote is captured whenenver a staker actually casts a vote for a given proposal.
    We use this to track who is active and inactive

    :param `voter`: checksummed eth address on read
    :param `choice`: will correspond to choice options in the proposal
    :param `proposal`: the proposal voted on
    :param `created`: when the vote was created
    """

    voter: EthereumAddress
    choice: int
    created: int
    proposal: Proposal

    @validator("voter")
    @classmethod
    def checksum_id(cls, _voter: str) -> str:
        return eth.to_checksum_address(_voter)


class OnChainProposal(BaseModel):
    """
    Parsing utility for GraphQL Data fetching on chain Proposals
    """

    description: str
    canceled: bool
    executed: bool
    id: str
    endBlock: int
    startBlock: int
    proposer: IDAddressDict
    proposalCreated: list

    @validator("proposer")
    @classmethod
    def checksum_id(cls, _proposerDict: IDAddressDict) -> str:
        return eth.to_checksum_address(_proposerDict["id"])

    @validator("proposalCreated")
    @classmethod
    def flatten_proposal(cls, created: list) -> int:
        return created[0]["timestamp"]

    def coerce_to_proposal(self) -> Proposal:
        return Proposal(
            id=self.id,
            title=self.description,
            author=self.proposer,
            start=self.startBlock,
            end=self.endBlock,
            created=self.proposalCreated,
            choices=None,
        )


class OnChainVote(BaseModel):
    """
    Parsing utility for GraphQL Data fetching on chain Votes
    """

    id: str
    receipt: dict[str, str]
    support: dict[str, int]
    governor: IDAddressDict
    voter: IDAddressDict
    proposal: OnChainProposal
    timestamp: int

    @validator("receipt")
    @classmethod
    def flatten_receipt(cls, receipt: dict[str, str]) -> str:
        return receipt["reason"]

    @validator("support")
    @classmethod
    def flatten_support(cls, support: dict[str, int]) -> int:
        return support["support"]

    @validator("governor")
    @classmethod
    def flatten_governor(cls, governor: IDAddressDict) -> EthereumAddress:
        return eth.to_checksum_address(governor["id"])

    @validator("voter")
    @classmethod
    def flatten_voter(cls, voter: IDAddressDict) -> EthereumAddress:
        return eth.to_checksum_address(voter["id"])

    def coerce_to_vote(self) -> Vote:
        return Vote(
            voter=self.voter,
            choice=self.support,
            created=self.timestamp,
            proposal=self.proposal.coerce_to_proposal(),
        )


class Delegate(BaseModel):
    """
    We do not allow vote delegation for EOAs, but smart contracts such as Gnosis Safes cannot use platforms such as snapshot.
    In these specific instances, we allow `delegates` to vote on behalf of `delegators`.
    """

    delegator: EthereumAddress
    delegate: EthereumAddress

    @validator("delegator")
    @classmethod
    def checksum_delegator(cls, d: str) -> str:
        return eth.to_checksum_address(d)

    @validator("delegate")
    @classmethod
    def checksum_delegate(cls, d: str) -> str:
        return eth.to_checksum_address(d)
