from typing import Literal, Any, Union

# type aliases for clarity
EthereumAddress = str
BigNumber = str
IDAddressDict = dict[Literal["id"], EthereumAddress]
GraphQL_Response = dict[Literal["data"], Any]
