# **Option 1: Calculate from veAUXO**

# 1. Take the total veAUXO held by the Staking Manager (representing all xAUXO deposits)
# 2. Set total rewards *initially* allocated to xAUXO as `rewardPerActiveVeToken` * `StakingManagerVeTokenBalance`
# 3. Remove x% of rewards as `xAUXOPremium` and save
# 4. Calculate the quantity of inactive xAUXO tokens
# 5. Remove these rewards from circulation (or redistribute) and save
#     1. If redistributing:
#         1. Get total active tokens
#         2. Compute the xAUXOPerActiveToken
#     2. If not
#         1. Get rewards per token as veAUXO held by staking manager / xAUXO reward total
from ..types import EthereumAddress


STAKING_MANAGER_ADDRESS: EthereumAddress
