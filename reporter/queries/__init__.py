from reporter.queries.common import *
from reporter.queries.total_supply import *
from reporter.queries.voters import *
from reporter.queries.xauxo_stakers import *
from reporter.queries.veauxo_stakers import *


def get_stakers(conf: Config) -> tuple[list[Staker], list[Staker]]:
    # utility function to get both stakers in one call
    return get_veauxo_stakers(conf), get_xauxo_stakers()
