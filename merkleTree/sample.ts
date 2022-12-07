const WINDOW_INDEX = 0;

/**
 * A sample file we might see in the python reporter 
 */
export const sampleInput: MerkleDistributorInput = {
  chainId: 1,
  aggregateRewards: [
    { token: "0x999999cf1046e68e36E1aA2E0E07105eDDD1f08E", amount: "1233" },
    { token: "0xc0ffee254729296a45a3885639AC7E10F9d54979", amount: "1234" },
  ],
  windowIndex: WINDOW_INDEX,
  recipients: {
    "0xc0ffee254729296a45a3885639AC7E10F9d54979": {
      windowIndex: WINDOW_INDEX,
      accountIndex: 0,
      rewards: [
        { token: "0x999999cf1046e68e36E1aA2E0E07105eDDD1f08E", amount: "1000" },
        { token: "0xc0ffee254729296a45a3885639AC7E10F9d54979", amount: "1000" },
      ],
    },
    "0x3DD72D85e5c665b7527Dc1F489F8244F09B0b808": {
      windowIndex: WINDOW_INDEX,
      accountIndex: 1,
      rewards: [
        { token: "0x999999cf1046e68e36E1aA2E0E07105eDDD1f08E", amount: "233" },
        { token: "0xc0ffee254729296a45a3885639AC7E10F9d54979", amount: "234" },
      ],
    },
    "0x00C67d9D6D3D13b42a87424E145826c467CcCd84": {
      windowIndex: WINDOW_INDEX,
      accountIndex: 2,
      rewards: [
        { token: "0x999999cf1046e68e36E1aA2E0E07105eDDD1f08E", amount: "233" },
        { token: "0xc0ffee254729296a45a3885639AC7E10F9d54979", amount: "234" },
      ],
    },
    "0x00d5D64dc14C601909aBDe7522e1BBbB7b582732": {
      windowIndex: WINDOW_INDEX,
      accountIndex: 3,
      rewards: [
        { token: "0x999999cf1046e68e36E1aA2E0E07105eDDD1f08E", amount: "233" },
        { token: "0xc0ffee254729296a45a3885639AC7E10F9d54979", amount: "235" },
      ],
    },
  },
};
