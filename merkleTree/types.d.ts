// TS has no real string utils but these help the reader understanding the output a bit more
type Address = string;
type Bytes32 = string;

type BaseReward = { token: Address; amount: string };
type Reward = BaseReward & { decimals: number; symbol: string };

type RecipientData = {
  rewards: BaseReward[];
  windowIndex: number;
  accountIndex: number;
};

type Recipient = {
  [recipient: Address]: RecipientData;
};

type MRecipient = {
  [recipient: Address]: RecipientData & { proof: Bytes32[] };
};

type MerkleDistributorInput = {
  chainId: number;
  aggregateRewards: Reward[];
  windowIndex: number;
  recipients: Recipient;
};

type MerkleDistributor = MerkleDistributorInput & {
  root: Bytes32;
  recipients: MRecipient;
};
