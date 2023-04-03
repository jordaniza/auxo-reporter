// TS has no real string utils but these help the reader understanding the output a bit more
type Address = string;
type Bytes32 = string;

type BaseReward = { address: Address; amount: string };
type Reward = BaseReward & {
  decimals: number;
  symbol: string;
  pro_rata: string;
};

type RecipientData = {
  rewards: string;
  token: Address;
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
  aggregateRewards: Reward;
  windowIndex: number;
  recipients: Recipient;
};

type MerkleDistributor = MerkleDistributorInput & {
  root: Bytes32;
  recipients: MRecipient;
};

type WithdrawalDistributorInput = {
  windowIndex: number;
  maxAmount: string;
  startBlock: number;
  endBlock: number;
  recipients: WithdrawalRecipient;
};

type WRecipientData = {
  windowIndex: number;
  amount: string;
};

type WithdrawalRecipient = {
  [recipient: Address]: WRecipientData;
};

type WMRecipient = {
  [recipient: Address]: WRecipientData & { proof: Bytes32[] };
};

type WMerkleDistributor = WithdrawalDistributorInput & {
  root: Bytes32;
  recipients: WMRecipient;
};
