const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");
const Module = require("node:module");

const sourcePath = path.join(__dirname, "..", "lib", "chart-visual.ts");
const source = fs.readFileSync(sourcePath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
});
const testModule = new Module(sourcePath, module);
testModule.filename = sourcePath;
testModule.paths = Module._nodeModulePaths(path.dirname(sourcePath));
testModule._compile(compiled.outputText, sourcePath);
const { prepareChartVisual } = testModule.exports;

test("accepts valid structured chart data", () => {
  const result = prepareChartVisual({
    type: "chart",
    render_mode: "statistics_chart",
    chart_type: "bar",
    title: "Study time by day",
    description: "Hours by day",
    expression: "",
    x_label: "Day",
    y_label: "Hours",
    data: [
      { label: "Mon", value: 2 },
      { label: "Tue", value: 3 },
    ],
  });

  assert.equal(result.ok, true);
  assert.equal(result.ok && result.chartType, "bar");
  assert.equal(result.ok && result.data.length, 2);
});

test("rejects unsupported chart types and invalid data", () => {
  assert.equal(
    prepareChartVisual({
      type: "chart",
      render_mode: "statistics_chart",
      chart_type: "scatter",
      title: "Bad chart",
      description: "",
      expression: "",
      data: [{ label: "A", value: 1 }],
    }).ok,
    false
  );

  assert.equal(
    prepareChartVisual({
      type: "chart",
      render_mode: "statistics_chart",
      chart_type: "line",
      title: "Bad data",
      description: "",
      expression: "",
      data: [{ label: "A", value: Number.NaN }],
    }).ok,
    false
  );
});

test("accepts table visual type as a simple table chart", () => {
  const result = prepareChartVisual({
    type: "table",
    render_mode: "statistics_chart",
    title: "Study table",
    description: "",
    expression: "",
    data: [{ label: "Mon", value: 2 }],
  });

  assert.equal(result.ok, true);
  assert.equal(result.ok && result.chartType, "table");
});
