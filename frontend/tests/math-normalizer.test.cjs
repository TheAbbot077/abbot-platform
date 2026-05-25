const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");
const vm = require("node:vm");

const sourcePath = path.join(__dirname, "..", "lib", "math-normalizer.ts");
const source = fs.readFileSync(sourcePath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
});
const sandbox = { exports: {}, require };
vm.runInNewContext(compiled.outputText, sandbox, { filename: sourcePath });
const { normalizeTutorMath } = sandbox.exports;

test("normalizes common plaintext math outside LaTeX", () => {
  assert.equal(
    normalizeTutorMath("Use x^2, sqrt(x), 1/2, <=, and >=."),
    "Use $x^2$, $\\sqrt{x}$, $\\frac{1}{2}$, $\\leq$, and $\\geq$."
  );
});

test("keeps existing inline and block LaTeX intact apart from markdown delimiter conversion", () => {
  assert.equal(normalizeTutorMath("Already \\( x^2 \\) is fine."), "Already $x^2$ is fine.");
  assert.equal(normalizeTutorMath("Block:\n\\[\nx^3 = 27\n\\]"), "Block:\n\n$$\nx^3 = 27\n$$\n");
});

test("does not aggressively rewrite prose or unsafe fractions", () => {
  assert.equal(normalizeTutorMath("Read chapter 1/section 2 before quiz 3/10/2026."), "Read chapter 1/section 2 before quiz 3/10/2026.");
});
