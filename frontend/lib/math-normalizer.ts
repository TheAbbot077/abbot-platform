const LATEX_SEGMENT_PATTERN = /(\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$\$[\s\S]*?\$\$|\$[^$\n]*?\$)/g;

export function normalizeTutorMath(value: string): string {
  return splitLatexSegments(value)
    .map((segment) => {
      if (segment.isLatex) {
        return normalizeMathDelimiters(segment.text);
      }
      return normalizePlainTextMath(segment.text);
    })
    .join("");
}

function splitLatexSegments(value: string): Array<{ text: string; isLatex: boolean }> {
  const segments: Array<{ text: string; isLatex: boolean }> = [];
  let lastIndex = 0;

  for (const match of value.matchAll(LATEX_SEGMENT_PATTERN)) {
    if (match.index === undefined) {
      continue;
    }

    if (match.index > lastIndex) {
      segments.push({ text: value.slice(lastIndex, match.index), isLatex: false });
    }

    segments.push({ text: match[0], isLatex: true });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < value.length) {
    segments.push({ text: value.slice(lastIndex), isLatex: false });
  }

  return segments;
}

function normalizePlainTextMath(value: string): string {
  let normalized = value;

  normalized = normalized.replace(/\bsqrt\(([A-Za-z0-9+\-*/^ ]{1,40})\)/g, (_, expression: string) =>
    inlineMath(`\\sqrt{${expression.trim()}}`)
  );
  normalized = normalized.replace(/\b([A-Za-z][A-Za-z0-9]*|\d+)\^(-?\d+|[A-Za-z])\b/g, (_, base: string, exponent: string) =>
    inlineMath(`${base}^${exponent}`)
  );
  normalized = normalized.replace(/(?<![A-Za-z0-9/])(\d+|[A-Za-z])\/(\d+|[A-Za-z])(?![A-Za-z0-9/])/g, (_, numerator: string, denominator: string) =>
    inlineMath(`\\frac{${numerator}}{${denominator}}`)
  );
  normalized = normalized.replace(/(?<![<>=])<=/g, inlineMath("\\leq"));
  normalized = normalized.replace(/(?<![<>=])>=/g, inlineMath("\\geq"));

  return normalized;
}

function normalizeMathDelimiters(value: string): string {
  return value
    .replace(/\\\[((?:.|\n)*?)\\\]/g, (_, expression: string) => `\n$$\n${expression.trim()}\n$$\n`)
    .replace(/\\\(((?:.|\n)*?)\\\)/g, (_, expression: string) => `$${expression.trim()}$`);
}

function inlineMath(expression: string): string {
  return `$${expression}$`;
}
