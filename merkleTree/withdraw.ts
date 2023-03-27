import { readFileSync, writeFileSync } from "fs";
import { createMerkleTree, createWithdrawalsTree } from "./create";
import { postToIPFS } from "./ipfs";
import * as dotenv from "dotenv";

dotenv.config();

const { stdin, stdout } = process;

function prompt(question: string) {
  return new Promise((resolve, reject) => {
    stdin.resume();
    stdout.write(question);

    stdin.on("data", (data) => resolve(data.toString().trim()));
    stdin.on("error", (err) => reject(err));
  });
}

const destination = (epoch: unknown) => `reports/${epoch}/merkle-verifier-prv.json`;

export const makeTreeWithPrompt = async (epoch: unknown) => {
  // create merkle trees for both tokens
  // fetch the claims database
  const claims = JSON.parse(
    readFileSync(`reports/${epoch}/withdrawals-prv.json`, {
      encoding: "utf8",
    })
  );

  // create the tree as a string
  const tree = JSON.stringify(createWithdrawalsTree(claims), null, 4);

  // write the file
  const fileDestination = destination(epoch);
  writeFileSync(fileDestination, tree);
  console.log(`✨✨ Withdrawal Merkle Verifier Created at ${fileDestination} ✨✨`);
};

async function main() {
  const epoch = await prompt("What is the epoch {YYYY}-{MM}? eg: 2022-11\n");
  await makeTreeWithPrompt(epoch);
}

// only run if called directly
if (require.main === module)
  main()
    .catch(console.error)
    .finally(() => process.exit(0));
