import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { test } from "node:test";

const require = createRequire(import.meta.url);
const { calculateFinancialValue } = require("../dist-tests/financial-calculator.js");

test("simple interest uses A = P(1 + rt)", () => {
  const result = calculateFinancialValue({
    financialMode: "simple_interest",
    principal: 1000,
    ratePercent: 5,
    time: 3,
    frequency: 1
  });

  assert.equal(result.formula, "A = P(1 + rt)");
  assert.equal(result.value.toFixed(2), "1150.00");
});

test("compound interest uses A = P(1 + r/n)^(nt)", () => {
  const result = calculateFinancialValue({
    financialMode: "compound_interest",
    principal: 1000,
    ratePercent: 5,
    time: 3,
    frequency: 12
  });

  assert.equal(result.formula, "A = P(1 + r/n)^(nt)");
  assert.equal(result.value.toFixed(2), "1161.47");
});

test("present value discounts future value", () => {
  const result = calculateFinancialValue({
    financialMode: "present_value",
    principal: 1000,
    ratePercent: 5,
    time: 3,
    frequency: 1
  });

  assert.equal(result.formula, "PV = FV / (1 + r)^t");
  assert.equal(result.value.toFixed(2), "863.84");
});

test("future value compounds annually", () => {
  const result = calculateFinancialValue({
    financialMode: "future_value",
    principal: 1000,
    ratePercent: 5,
    time: 3,
    frequency: 1
  });

  assert.equal(result.formula, "FV = PV(1 + r)^t");
  assert.equal(result.value.toFixed(2), "1157.63");
});
