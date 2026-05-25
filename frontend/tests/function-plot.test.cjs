const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");
const Module = require("node:module");

const sourcePath = path.join(__dirname, "..", "lib", "function-plot.ts");
const source = fs.readFileSync(sourcePath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    esModuleInterop: true,
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
});
const testModule = new Module(sourcePath, module);
testModule.filename = sourcePath;
testModule.paths = Module._nodeModulePaths(path.dirname(sourcePath));
testModule._compile(compiled.outputText, sourcePath);
const { normalizeFunctionExpression, prepareFunctionPlot } = testModule.exports;

test("normalizes common function labels before parsing", () => {
  assert.equal(normalizeFunctionExpression("y = x²"), "x^2");
  assert.equal(normalizeFunctionExpression("f(x) = sin(x)"), "sin(x)");
});

test("prepares safe function plot data for supported expressions", () => {
  for (const expression of ["y = x", "y = x^2", "y = x^3", "y = 1/x", "y = sin(x)", "y = cos(x)", "y = sqrt(x)"]) {
    const result = prepareFunctionPlot(expression);
    assert.equal(result.ok, true, expression);
    assert.ok(result.ok && result.segments.length >= 1, expression);
  }
});

test("samples a parabola that can be rendered by the graph visual", () => {
  const result = prepareFunctionPlot("y = x^2");
  assert.equal(result.ok, true);
  const points = result.ok ? result.segments.flat() : [];
  const origin = points.find((point) => point.x === 0);
  const xTwo = points.find((point) => point.x === 2);

  assert.equal(origin && origin.y, 0);
  assert.equal(xTwo && xTwo.y, 4);
});

test("rejects unsupported or unsafe expressions", () => {
  for (const expression of ["x.constructor", "evil(x)", "y = import('fs')", "a = x^2"]) {
    const result = prepareFunctionPlot(expression);
    assert.equal(result.ok, false, expression);
  }
});
