import { parse, type MathNode } from "mathjs";

export type FunctionPlotPoint = {
  x: number;
  y: number;
};

export type FunctionPlotResult =
  | {
      ok: true;
      expression: string;
      segments: FunctionPlotPoint[][];
    }
  | {
      ok: false;
      reason: string;
    };

const ALLOWED_SYMBOLS = new Set(["x", "pi", "e", "sin", "cos", "sqrt"]);
const ALLOWED_FUNCTIONS = new Set(["sin", "cos", "sqrt"]);
const ALLOWED_OPERATORS = new Set(["+", "-", "*", "/", "^", "unaryMinus", "unaryPlus"]);

export function prepareFunctionPlot(expression: string, xMin = -10, xMax = 10, step = 0.1): FunctionPlotResult {
  const normalizedExpression = normalizeFunctionExpression(expression);

  if (!normalizedExpression) {
    return { ok: false, reason: "No graphable expression was provided." };
  }

  let root: MathNode;
  try {
    root = parse(normalizedExpression);
  } catch {
    return { ok: false, reason: "The expression could not be parsed safely." };
  }

  if (!isSafeMathExpression(root)) {
    return { ok: false, reason: "The expression uses syntax that is not supported for safe graphing yet." };
  }

  const compiledExpression = root.compile();
  const segments: FunctionPlotPoint[][] = [];
  let currentSegment: FunctionPlotPoint[] = [];
  let previousPoint: FunctionPlotPoint | null = null;

  for (let x = xMin; x <= xMax + step / 2; x += step) {
    const roundedX = roundForChart(x);
    let y: unknown;

    try {
      y = compiledExpression.evaluate({ x: roundedX });
    } catch {
      pushSegmentIfUseful(segments, currentSegment);
      currentSegment = [];
      previousPoint = null;
      continue;
    }

    if (typeof y !== "number" || !Number.isFinite(y)) {
      pushSegmentIfUseful(segments, currentSegment);
      currentSegment = [];
      previousPoint = null;
      continue;
    }

    const roundedY = roundForChart(y);
    const nextPoint = { x: roundedX, y: roundedY };

    if (previousPoint && Math.abs(nextPoint.y - previousPoint.y) > 50) {
      pushSegmentIfUseful(segments, currentSegment);
      currentSegment = [];
    }

    currentSegment.push(nextPoint);
    previousPoint = nextPoint;
  }

  pushSegmentIfUseful(segments, currentSegment);

  if (segments.length === 0) {
    return { ok: false, reason: "The expression did not produce enough visible points in the default range." };
  }

  return {
    ok: true,
    expression: normalizedExpression,
    segments
  };
}

export function normalizeFunctionExpression(expression: string): string {
  const trimmedExpression = expression.trim();

  if (!trimmedExpression) {
    return "";
  }

  const asciiExpression = trimmedExpression
    .replace(/²/g, "^2")
    .replace(/³/g, "^3")
    .replace(/π/g, "pi")
    .replace(/\by\s*=/i, "")
    .replace(/\bf\s*\(\s*x\s*\)\s*=/i, "");

  return asciiExpression.trim();
}

function isSafeMathExpression(root: MathNode): boolean {
  let isSafe = true;

  // mathjs parses expressions into an AST. We allow only a tiny graphing subset
  // and reject property access, assignments, unknown functions, and anything else.
  root.traverse((node: MathNode) => {
    if (!isSafeNode(node)) {
      isSafe = false;
    }
  });

  return isSafe;
}

function isSafeNode(node: MathNode): boolean {
  const nodeWithFields = node as MathNode & {
    fn?: { name?: string };
    name?: string;
    op?: string;
  };

  if (node.type === "ConstantNode" || node.type === "ParenthesisNode") {
    return true;
  }

  if (node.type === "SymbolNode") {
    return Boolean(nodeWithFields.name && ALLOWED_SYMBOLS.has(nodeWithFields.name));
  }

  if (node.type === "OperatorNode") {
    return Boolean(nodeWithFields.op && ALLOWED_OPERATORS.has(nodeWithFields.op));
  }

  if (node.type === "FunctionNode") {
    return Boolean(nodeWithFields.fn?.name && ALLOWED_FUNCTIONS.has(nodeWithFields.fn.name));
  }

  return false;
}

function pushSegmentIfUseful(segments: FunctionPlotPoint[][], segment: FunctionPlotPoint[]) {
  if (segment.length >= 2) {
    segments.push(segment);
  }
}

function roundForChart(value: number): number {
  return Math.round(value * 1000) / 1000;
}
