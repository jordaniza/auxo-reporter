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
    XAUXO = env_var("XAUXO_ADDRESS")
    VEAUXO = env_var("VEAUXO_ADDRESS")
    XAUXO_ROLLSTAKER = env_var("XAUXO_ROLLSTAKER")
    STAKING_MANAGER = env_var("STAKING_MANAGER_ADDRESS")
    DECAY_ORACLE = env_var("DECAY_ORACLE")


SNAPSHOT_SPACE_ID = env_var("SNAPSHOT_SPACE_ID")
RPC_URL = env_var("RPC_URL")
