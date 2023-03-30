from pytest import raises
from reporter.models import *

USER = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"


def test_user_checksum_address():
    # Valid Ethereum addresses in lowercase, mixed case, and checksum format
    valid_addresses = [
        "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        "0x742d35cc6634c0532925a3b844bc454e4438f44e",
        "0x742d35CC6634C0532925a3b844Bc454e4438f44E",
    ]

    # Invalid Ethereum addresses
    invalid_addresses = [
        "",
        "0x",
        "0x742d35cc6634c0532925a3b844bc454e4438f44",
        "0x742d35cc6634c0532925a3b844bc454e4438f44ex",
    ]

    # Test valid Ethereum addresses
    for address in valid_addresses:
        user = User(address=address)
        assert user.address == USER

    # Test invalid Ethereum addresses
    for address in invalid_addresses:
        with raises(ValueError):
            user = User(address=address)


def test_staker():
    arv = ARVStaker(arv_holding="100", address=USER)

    assert arv.token.amount == "100"
    assert arv.address == USER
    assert arv.token == ARV(amount="100")

    prv = PRVStaker(prv_holding="100", address=USER)

    assert prv.token.amount == "100"
    assert prv.address == USER
    assert prv.token == PRV(amount="100")


def test_account_from_prv_staker():
    staker = PRVStaker(prv_holding="100", address=USER)
    rewards = ERC20Amount(
        address=ADDRESSES.GOVERNOR, amount="200", symbol="TEST", decimals=18
    )

    state = AccountState.ACTIVE

    account = Account.from_prv_staker(staker, rewards, state)

    assert isinstance(account, Account)
    assert account.rewards == rewards
    assert account.state == state


def test_account_from_arv_staker():
    staker = ARVStaker(arv_holding="100", address=USER)
    rewards = ERC20Amount(
        address=ADDRESSES.GOVERNOR, amount="200", symbol="TEST", decimals=18
    )
    state = AccountState.INACTIVE

    account = Account.from_arv_staker(staker, rewards, state)

    assert isinstance(account, Account)
    assert account.rewards == rewards
    assert account.state == state
