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

async function main() {
  const epoch = await prompt("What is the epoch {YYYY}-{MM}? eg: 2022-11\n");

  const claims = JSON.parse(
    readFileSync(`reports/${epoch}/claims.json`, { encoding: "utf8" })
  );
  const tree = JSON.stringify(createMerkleTree(claims), null, 4);
  const destination = `reports/${epoch}/merkle-tree.json`;
  writeFileSync(destination, tree);
  console.log(`✨✨ Merkle Tree Created at ${destination} ✨✨`);

  let post = (await prompt("Post to IPFS? [Y/n]\n")) as string;
  post = String(post).toLowerCase().trim();
  if (!post || post === "y") {
    console.log("Posting to ipfs...");
    await postToIPFS(destination);
  } else {
    console.warn("Did not post to IPFS");
  }
}

main()
  .catch(console.error)
  .finally(() => process.exit(0));
