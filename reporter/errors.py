class EmptyQueryError(Exception):
    """Raise if GraphQL Query returns no results"""

    pass


class MissingRewardException(Exception):
    """Raise if a reward token is not found in a user's list of rewards"""

    pass
