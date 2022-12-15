import { BigNumber, ethers } from "ethers";

/// This script will generate a fake merkle tree from randomised data

const TOKENS: [Address, number, string][] = [
  ["0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", 6, "USDC"],
  ["0xD533a949740bb3306d119CC777fa900bA034cd52", 18, "CRV"],
  ["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", 18, "WETH"],
];

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
  let aggregateRewardsBN = TOKENS.map(([token, decimals, symbol]) => ({
    token,
    amount: BigNumber.from(0),
    decimals,
    symbol,
  }));

  const recipients = ADDRESSES.reduce((prev, address, idx) => {
    const rewards: BaseReward[] = TOKENS.map(([token, decimals]) => {
      const rewardQty = Math.round(Math.random() * 100_000).toString();
      const bnReward = ethers.utils.parseUnits(rewardQty, decimals);

      aggregateRewardsBN.find((t) => t.token === token)!.amount =
        aggregateRewardsBN.find((t) => t.token === token)!.amount.add(bnReward);

      return {
        token,
        amount: bnReward.toString(),
      };
    });

    const recipient: RecipientData = {
      windowIndex,
      accountIndex: idx,
      rewards,
    };

    return { ...prev, [address]: recipient };
  }, {} as MerkleDistributorInput["recipients"]);

  const aggregateRewards = aggregateRewardsBN.map((reward) => {
    return { ...reward, amount: reward.amount.toString() };
  }, {});

  return {
    aggregateRewards,
    recipients,
    windowIndex,
    chainId: 1,
  };
}
