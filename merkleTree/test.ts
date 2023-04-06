import { makeTreesWithPrompt } from "./app";

async function test() {
  await Promise.all(
    [10, 11].map((m) =>
      makeTreesWithPrompt(`test/2008-${m}`, {
        ipfsPrompt: false,
        latest: true,
      })
    )
  );
}

test()
  .catch(console.error)
  .finally(() => process.exit(0));
