import { readFileSync, writeFileSync } from "fs";
import { createMerkleTree } from "./create";
import { postToIPFS } from "./ipfs";
import * as dotenv from "dotenv";
import { validateTree } from "./validate";
import { treePath } from "./utils";
import { combineTrees } from "./combine";

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

const AUXO_TOKENS: AuxoTokenSymbol[] = ["ARV", "PRV"];

interface TestOptions {
  ipfsPrompt?: boolean;
  latest?: boolean;
}

export const makeTreesWithPrompt = async (
  epoch: string,
  options: TestOptions = {
    ipfsPrompt: true,
    latest: true,
  }
) => {
  // create merkle trees for both tokens
  AUXO_TOKENS.forEach((auxo_token) => {
    // fetch the claims database
    const claims = JSON.parse(
      readFileSync(`reports/${epoch}/claims-${auxo_token}.json`, {
        encoding: "utf8",
      })
    );

    // create the tree as a string
    const tree = createMerkleTree(claims);
    if (!validateTree(tree)) throw new Error("Invalid tree");
    const strTree = JSON.stringify(tree, null, 4);

    // write the file
    const fileDestination = treePath(auxo_token, epoch);
    writeFileSync(fileDestination, strTree);
    if (options.latest) {
      writeFileSync(`reports/latest/merkle-tree${auxo_token}.json`, strTree);
    }
    console.log(`✨✨ ${auxo_token} Merkle Tree Created at ${fileDestination} ✨✨`);
  });
  // combine the trees

  const combined = await combineTrees(epoch);
  if (options.latest) {
    writeFileSync(`reports/latest/merkle-tree-combined.json`, JSON.stringify(combined, null, 4));
  }
  console.log(`✨✨ Combined Merkle Tree Created at reports/${epoch}/combined-trees.json ✨✨`);

  if (options.ipfsPrompt) {
    let post = String(await prompt("Post to IPFS? [Y/n]\n"));
    post = post.toLowerCase().trim();

    if (!post || post === "y") {
      for (const auxo_token of AUXO_TOKENS) {
        console.log(`Posting ${auxo_token} Merkle Tree to ipfs...`);
        await postToIPFS(treePath(auxo_token, epoch));
      }
    } else {
      console.warn("Did not post to IPFS");
    }
  }
};

async function main() {
  const epoch = await prompt("What is the epoch {YYYY}-{MM}? eg: 2022-11\n");
  await makeTreesWithPrompt(String(epoch));
}

// only run if called directly
if (require.main === module)
  main()
    .catch(console.error)
    .finally(() => process.exit(0));
