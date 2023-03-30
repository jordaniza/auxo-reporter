class EmptyQueryError(Exception):
    """Raise if GraphQL Query returns no results"""

    pass


class TooManyLoopsError(Exception):
    """Raise if a loop runs too many times"""

    pass


class MissingRewardException(Exception):
    """Raise if a reward token is not found in a user's list of rewards"""

    pass


class BadConfigException(Exception):
    pass


class MissingEnvironmentVariableException(Exception):
    pass


class InvalidXAUXOHaircutPercentageException(Exception):
    pass


class MissingStakingManagerAddressError(Exception):
    pass


class MissingBoostBalanceException(Exception):
    pass


class MissingDBException(Exception):
    pass
