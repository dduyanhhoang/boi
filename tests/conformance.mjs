// Reads {"tables": ..., "words": [...]} on stdin, prints the JS pipeline's
// reading for each word. Used only by tests/test_js_conformance.py.
import { readUnknown, splitInto } from "../app/scripts/oov.js";

const input = JSON.parse(await new Promise((resolve) => {
  let data = "";
  process.stdin.on("data", (c) => { data += c; });
  process.stdin.on("end", () => resolve(data));
}));

const known = new Set(input.known ?? []);
const out = {};
for (const word of input.words) {
  const { phones, readings } = readUnknown(word, input.tables, 3);
  out[word] = { phones, readings, split: splitInto(word, known) };
}
process.stdout.write(JSON.stringify(out));
