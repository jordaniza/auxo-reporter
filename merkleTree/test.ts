import { makeTreeWithPrompt } from "./app";

async function test() {
  await makeTreeWithPrompt("test-5");
}

test()
  .catch(console.error)
  .finally(() => process.exit(0));
