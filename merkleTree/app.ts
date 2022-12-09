// import { readFileSync, writeFileSync } from "fs";
// import { program } from "commander";

// import { createMerkleTree } from "./create";

// function readClaims() {}

// /// Very simple string address validation: 0x prefix and length 42
// function isEthereumAddress(address: string): boolean {
//   const validPrefix = address.substring(0, 2) !== "0x";
//   const validLength = address.length === 42;
//   const isValid = !validLength || !validPrefix;
//   if (!isValid) console.warn(`Invalid Address found ${address}`);
//   return isValid;
// }

// function validateClaimsObject(
//   input: Record<string, unknown>
// ): MerkleDistributorInput {
//   try {
//     if (typeof input !== "object") throw "Not an Object";

//     /// keys
//     const expectedTopLevelKeys = [
//       "chainId",
//       "aggregateRewards",
//       "windowIndex",
//       "recipients",
//     ];

//     const expectedRecipientKeys = ["windowIndex", "accountIndex", "rewards"];

//     const expectedRewardKeys = ["token", "amount"];

//     // all required top level keys are present
//     const allTopLevelKeysPresent = expectedTopLevelKeys.reduce(
//       (_, key) => Object.keys(input).includes(key),
//       false
//     );

//     const recipientsArray = Object.entries(
//       (<MerkleDistributorInput>input).recipients
//     );

//     // all recipients have required keys
//     const allRecipientKeysPresent = recipientsArray.reduce(
//       (_, [address, recipientData]) => {
//         return expectedRewardKeys.reduce(
//           (_, key) =>
//             Object.keys(recipientData).includes(key) &&
//             isEthereumAddress(address),
//           false
//         );
//       },
//       false
//     );

//     /// aggregation
//     // totals === sum of recipients
//     // no unrecognised tokens
//     // all tokens present
//     const topLevelTokens = (<MerkleDistributorInput>input).aggregateRewards.map(
//       (reward) => reward.token
//     );

//     const tokenQuantities: {
//       [token: string]: { amounts: any[]; total: number };
//     } = topLevelTokens.reduce((prev, token) => {
//       const tokensByRecipient = recipientsArray.map(([_, data]) =>
//         data.rewards.find((r) => r.token === token)
//       );
//       return {
//         ...prev,
//         [token]: {
//           amounts: tokensByRecipient,
//           total: tokensByRecipient.reduce((a, b) => a + Number(b), 0),
//         },
//       };
//     }, {});

//     const totalsMatch = (<MerkleDistributorInput>input).aggregateRewards.reduce(
//       (_, a) => {
//         return (
//           Number(a.amount) ===
//           tokenQuantities[a.token as keyof typeof tokenQuantities].total
//         );
//       },
//       false
//     );

//     /// no duplicate accounts
//     // no duplicate keys
//     // no duplicate account indexes

//     // windows
//     // all window indicies are the same
//   } catch (err) {
//     throw new Error("Invalid JSON:" + err);
//   }

//   return input as MerkleDistributorInput;
// }

// async function main() {
//   program
//     .requiredOption(
//       "-i, --input <path>",
//       "input JSON file location containing a recipients payout"
//     )
//     .requiredOption("-o, --output <path>", "output merkle tree file")
//     .parse(process.argv);

//   const options = program.opts();

//   const claims = JSON.parse(readFileSync(options.input, { encoding: "utf8" }));
// }

// main()
//   .catch(console.error)
//   .finally(() => process.exit(1));
