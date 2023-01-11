import { BigNumber, ethers } from "ethers";

/// This script will generate a fake merkle tree from randomised data

const REWARD = {
  token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
  decimals: 18,
  symbol: "WETH",
};

const ADDRESSES = [
  "0xbecfc9f37bdd8ca3d35b53edc72fc8ea89d3584b",
  "0x1b5197f0bec8c0116bbda05dc331c0db6dbe0a14",
  "0x7de88b53477f9099a5551aaac71f4c6ed40052a1",
  "0x14b6b961a0b80558e92795dd2515eb8a650cb081",
  "0x3560e140ccec5793314b38ae63e8ddaee2bad8a4",
  "0xbba0a7d009614e392be190363925e52319a39d4d",
  "0x8bacffa2c13e8721974cff6a6281f18f559528e5",
  "0xccc9a67f57af353388dbc8009bc6e9429aff13b7",
  "0xd196d93594985b26460bacfbedf7667c36a3b243",
  "0x9db96adb915e51f61e2495afb026bb9e887a364b",
];

export function generateInputData(windowIndex: number): MerkleDistributorInput {
  let aggregateRewardsBN = {
    ...REWARD,
    amount: BigNumber.from(0),
  };

  const recipients = ADDRESSES.reduce((prev, address, idx) => {
    const rewardQty = Math.round(Math.random() * 100_000).toString();
    const bnReward = ethers.utils.parseUnits(rewardQty, REWARD.decimals);

    aggregateRewardsBN.amount = aggregateRewardsBN.amount.add(bnReward);

    const recipient: RecipientData = {
      windowIndex,
      accountIndex: idx,
      rewards: bnReward.toString(),
    };

    return { ...prev, [address]: recipient };
  }, {} as MerkleDistributorInput["recipients"]);

  const aggregateRewards = {
    ...aggregateRewardsBN,
    amount: aggregateRewardsBN.amount.toString(),
    pro_rata: String(
      Number(aggregateRewardsBN.amount) / Object.entries(recipients).length
    ),
  };

  return {
    aggregateRewards,
    recipients,
    windowIndex,
    chainId: 1,
  };
}
