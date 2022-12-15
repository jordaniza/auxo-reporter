import { readFileSync, writeFileSync } from "fs";
import { createMerkleTree } from "./create";
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
  writeFileSync(`reports/${epoch}/merkle-tree.json`, tree);
  console.log("✨✨ Merkle Tree Created! ✨✨");
}

main()
  .catch(console.error)
  .finally(() => process.exit(0));
