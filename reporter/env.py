import os
from dotenv import load_dotenv
from reporter.errors import MissingEnvironmentVariableException

load_dotenv()


def env_var(accessor: str) -> str:
    """
    Attempt to fetch an environment variable and throw
    an error if not found
    """
    var = os.environ.get(accessor)
    if not var:
        raise MissingEnvironmentVariableException(accessor)
    return var


class ADDRESSES:
    GOVERNOR = env_var("GOVERNOR_ADDRESS")
    PRV = env_var("PRV_ADDRESS")
    ARV = env_var("ARV_ADDRESS")
    PRV_ROLLSTAKER = env_var("PRV_ROLLSTAKER")
    STAKING_MANAGER = env_var("STAKING_MANAGER_ADDRESS")
    DECAY_ORACLE = env_var("DECAY_ORACLE")


class SUBGRAPHS:
    SNAPSHOT = "https://hub.snapshot.org/graphql"
    VEDOUGH = "https://api.thegraph.com/subgraphs/name/pie-dao/vedough"

    AUXO_TOKEN = env_var("SUBGRAPH_AUXO_TOKEN")
    AUXO_GOV = env_var("SUBGRAPH_AUXO_GOV")
    ROLLSTAKER = env_var("SUBGRAPH_ROLLSTAKER")


SNAPSHOT_SPACE_ID = env_var("SNAPSHOT_SPACE_ID")
RPC_URL = env_var("RPC_URL")
