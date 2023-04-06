import { BigNumber } from "ethers";

export function validateTree(tree: MerkleDistributor): boolean {
  return addressesUnique(tree) && accountIndexUnique(tree) && totalRewardCorrect(tree);
}

// check that each account index is unique
function addressesUnique(tree: MerkleDistributor): boolean {
  const addresses = Object.keys(tree.recipients);
  return addresses.length === new Set(addresses).size;
}

// check only one of each account index in tree
function accountIndexUnique(tree: MerkleDistributor): boolean {
  const accountIndexes = Object.values(tree.recipients).map((recipient) => recipient.accountIndex);
  return accountIndexes.length === new Set(accountIndexes).size;
}

// check that the sum of all rewards is equal to the total reward
function totalRewardCorrect(tree: MerkleDistributor): boolean {
  const totalReward = tree.aggregateRewards.amount;
  const sum = Object.values(tree.recipients).reduce((acc, recipient) => acc.add(recipient.rewards), BigNumber.from(0));
  return totalReward === sum.toString();
}
