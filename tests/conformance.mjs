// Reads {"tables": ..., "words": [...]} on stdin, prints the JS pipeline's
// reading for each word. Used only by tests/test_js_conformance.py.
import { readUnknown, readLetters, splitInto, candidatesFromPhones, alignVowels,
         acronymParts, knownParts, partsPhones }
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
               known: knownParts(word, known, input.tables),
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
// Words built from pieces, with the phones the shards give each known piece.
const parts = {};
for (const [word, said] of input.parts ?? []) {
  const pieces = splitInto(word, known)?.map((p) => [p, true]) ?? knownParts(word, known, input.tables);
  const { phones, letters } = partsPhones(word, pieces, (p) => said[p] ?? null, input.tables);
  parts[word] = { pieces, phones, readings: candidatesFromPhones(phones, input.tables, 3, letters) };
}
process.stdout.write(JSON.stringify({ parts,  spelled: out, real, acronyms }));
