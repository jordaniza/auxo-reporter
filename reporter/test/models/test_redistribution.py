from decimal import Decimal
from reporter.models import (
    RedistributionContainer,
    RedistributionOption,
    RedistributionWeight,
)


def test_normalized_redistribution_weights():
    # test normalization and reward assignment
    r1 = RedistributionWeight(
        weight=2, option=RedistributionOption.TRANSFER, address="0x1"
    )
    r2 = RedistributionWeight(weight=1, option=RedistributionOption.REDISTRIBUTE_PRV)
    container = RedistributionContainer(redistributions=[r1, r2])

    assert len(container.redistributions) == 2

    # check normalization
    assert container.redistributions[0].weight == 2
    assert container.redistributions[1].weight == 1

    # check reward assignment
    assert container.redistributions[0].rewards == "0"
    assert container.redistributions[1].rewards == "0"

    container.redistribute(Decimal(100))
    assert container.total_redistributed == Decimal(100)

    assert container.redistributions[0].distributed == True
    assert container.redistributions[0].rewards == "66"
    assert container.redistributions[1].rewards == "33"


def test_redistribution_container():
    # test total weights calculation
    r1 = RedistributionWeight(
        weight=2, option=RedistributionOption.TRANSFER, address="0x1"
    )
    r2 = RedistributionWeight(weight=1, option=RedistributionOption.REDISTRIBUTE_PRV)
    container = RedistributionContainer(redistributions=[r1, r2])
    assert container.total_weights == 3

    # test total rewards redistribution
    container.redistribute(Decimal(100))
    assert container.total_redistributed == Decimal(100)

    # test transfer reward calculation
    assert container.transferred == Decimal(66)

    # test staker reward calculation
    assert container.to_stakers == Decimal(33)
