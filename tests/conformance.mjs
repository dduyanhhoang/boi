// Reads {"tables": ..., "words": [...]} on stdin, prints the JS pipeline's
// reading for each word. Used only by tests/test_js_conformance.py.
import { readUnknown, readLetters, splitInto, candidatesFromPhones, alignVowels,
         acronymParts }
  from "../app/scripts/oov.js";

const input = JSON.parse(await new Promise((resolve) => {
  let data = "";
  process.stdin.on("data", (c) => { data += c; });
  process.stdin.on("end", () => resolve(data));
}));

const known = new Set(input.known ?? []);
const out = {};
for (const word of input.words) {
  const { phones, readings } = readUnknown(word, input.tables, 3);
  out[word] = { phones, readings, split: splitInto(word, known),
               letters: readLetters(word, input.tables) };
}
// Real CMUdict phones, given by the caller, so the stress patterns the
// spelling path never produces (AH0, ER0, stress past the first syllable)
// reach the same control flow the Python runs.
const real = {};
for (const [word, phones] of input.pairs ?? []) {
  const letters = alignVowels(word, phones, input.tables);
  real[word] = { letters, readings: candidatesFromPhones(phones, input.tables, 3, letters) };
}
const acronyms = {};
for (const word of input.acronyms ?? []) {
  acronyms[word] = acronymParts(word, input.tables, known);
}
process.stdout.write(JSON.stringify({ spelled: out, real, acronyms }));
