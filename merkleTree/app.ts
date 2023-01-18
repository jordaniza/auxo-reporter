import { readFileSync, writeFileSync } from "fs";
import { createMerkleTree } from "./create";
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

const destination = (token: string, epoch: unknown) =>
  `reports/${epoch}/merkle-tree-${token}.json`;

const AUXO_TOKENS = ["veAUXO", "xAUXO"];

async function main() {
  const epoch = await prompt("What is the epoch {YYYY}-{MM}? eg: 2022-11\n");

  // create merkle trees for both tokens
  AUXO_TOKENS.forEach((auxo_token) => {
    // fetch the claims database
    const claims = JSON.parse(
      readFileSync(`reports/${epoch}/claims-${auxo_token}.json`, {
        encoding: "utf8",
      })
    );

    // create the tree as a string
    const tree = JSON.stringify(createMerkleTree(claims), null, 4);

    // write the file
    const fileDestination = destination(auxo_token, epoch);
    writeFileSync(fileDestination, tree);
    console.log(
      `✨✨ ${auxo_token} Merkle Tree Created at ${fileDestination} ✨✨`
    );
  });

  let post = (await prompt("Post to IPFS? [Y/n]\n")) as string;

  post = String(post).toLowerCase().trim();

  if (!post || post === "y") {
    for (const auxo_token of AUXO_TOKENS) {
      console.log(`Posting ${auxo_token} Merkle Tree to ipfs...`);
      await postToIPFS(destination(auxo_token, epoch));
    }
  } else {
    console.warn("Did not post to IPFS");
  }
}

main()
  .catch(console.error)
  .finally(() => process.exit(0));
