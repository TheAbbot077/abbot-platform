"use client";

import type { GeometryAnnotation, GeometryShape, VisualContent } from "@/lib/types";

type SvgLabel = {
  text: string;
  x: number;
  y: number;
};

const SHAPE_LABELS: Record<GeometryShape, SvgLabel[]> = {
  circle: [
    { text: "O", x: 200, y: 150 },
    { text: "r", x: 270, y: 142 },
  ],
  triangle: [
    { text: "A", x: 197, y: 44 },
    { text: "B", x: 72, y: 268 },
    { text: "C", x: 329, y: 268 },
  ],
  rectangle: [
    { text: "A", x: 80, y: 82 },
    { text: "B", x: 320, y: 82 },
    { text: "C", x: 320, y: 242 },
    { text: "D", x: 80, y: 242 },
  ],
  square: [
    { text: "A", x: 110, y: 70 },
    { text: "B", x: 290, y: 70 },
    { text: "C", x: 290, y: 250 },
    { text: "D", x: 110, y: 250 },
  ],
  coordinate_point: [{ text: "P", x: 275, y: 103 }],
  line_segment: [
    { text: "A", x: 62, y: 180 },
    { text: "B", x: 338, y: 180 },
  ],
  angle: [
    { text: "A", x: 300, y: 110 },
    { text: "B", x: 122, y: 228 },
    { text: "C", x: 318, y: 228 },
  ],
  polygon: [
    { text: "A", x: 200, y: 48 },
    { text: "B", x: 314, y: 120 },
    { text: "C", x: 276, y: 252 },
    { text: "D", x: 124, y: 252 },
    { text: "E", x: 86, y: 120 },
  ],
};

const ANNOTATION_POSITIONS: Record<string, { x: number; y: number }> = {
  center: { x: 200, y: 168 },
  radius: { x: 244, y: 132 },
  corner_A: { x: 116, y: 92 },
  corner_B: { x: 284, y: 92 },
  corner_C: { x: 284, y: 228 },
  corner_D: { x: 116, y: 228 },
  side_AB: { x: 200, y: 78 },
  side_BC: { x: 314, y: 170 },
  side_CD: { x: 200, y: 252 },
  side_DA: { x: 86, y: 170 },
  midpoint: { x: 200, y: 168 },
  point: { x: 286, y: 95 },
  angle: { x: 172, y: 205 },
};

export function GeometryRenderer({ visualContent }: { visualContent: VisualContent }) {
  if (!visualContent.shape || !isSupportedShape(visualContent.shape)) {
    return (
      <p className="rounded-2xl border border-dashed bg-background p-3 text-sm text-muted-foreground">
        The Abbot suggested a geometry diagram, but this shape is not supported yet.
      </p>
    );
  }

  const labels = buildLabels(visualContent.shape, visualContent.labels);

  return (
    <div className="overflow-hidden rounded-2xl border bg-background p-2">
      <svg
        className="h-auto w-full"
        role="img"
        aria-label={visualContent.title || `${visualContent.shape} diagram`}
        viewBox="0 0 400 320"
      >
        <rect width="400" height="320" rx="14" fill="hsl(var(--background))" />
        <g stroke="hsl(var(--primary))" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4">
          {renderShape(visualContent.shape)}
        </g>
        <g fill="hsl(var(--foreground))" fontFamily="Arial, sans-serif" fontSize="18" fontWeight="700">
          {labels.map((label) => (
            <text key={`${label.text}-${label.x}-${label.y}`} x={label.x} y={label.y} textAnchor="middle">
              {label.text}
            </text>
          ))}
        </g>
        <g fill="hsl(var(--primary))" fontFamily="Arial, sans-serif" fontSize="15" fontWeight="700">
          {visualContent.annotations?.map((annotation, index) => (
            <Annotation key={`${annotation.label}-${index}`} annotation={annotation} fallbackIndex={index} />
          ))}
        </g>
      </svg>
    </div>
  );
}

function renderShape(shape: GeometryShape) {
  switch (shape) {
    case "circle":
      return (
        <>
          <circle cx="200" cy="160" r="86" fill="hsl(var(--primary) / 0.08)" />
          <line x1="200" y1="160" x2="286" y2="160" />
          <circle cx="200" cy="160" r="4" fill="hsl(var(--primary))" />
        </>
      );
    case "triangle":
      return <polygon points="200,56 82,252 318,252" fill="hsl(var(--primary) / 0.08)" />;
    case "rectangle":
      return <rect x="92" y="92" width="216" height="136" fill="hsl(var(--primary) / 0.08)" />;
    case "square":
      return <rect x="110" y="80" width="180" height="180" fill="hsl(var(--primary) / 0.08)" />;
    case "coordinate_point":
      return (
        <>
          <line x1="54" y1="160" x2="346" y2="160" stroke="hsl(var(--muted-foreground))" strokeWidth="2" />
          <line x1="200" y1="288" x2="200" y2="32" stroke="hsl(var(--muted-foreground))" strokeWidth="2" />
          <circle cx="270" cy="110" r="7" fill="hsl(var(--primary))" />
        </>
      );
    case "line_segment":
      return (
        <>
          <line x1="72" y1="170" x2="328" y2="170" />
          <circle cx="72" cy="170" r="6" fill="hsl(var(--primary))" />
          <circle cx="328" cy="170" r="6" fill="hsl(var(--primary))" />
        </>
      );
    case "angle":
      return (
        <>
          <line x1="130" y1="220" x2="314" y2="220" />
          <line x1="130" y1="220" x2="286" y2="106" />
          <path d="M 170 220 A 40 40 0 0 1 162 196" fill="none" strokeWidth="3" />
        </>
      );
    case "polygon":
      return <polygon points="200,58 306,124 266,246 134,246 94,124" fill="hsl(var(--primary) / 0.08)" />;
    default:
      return null;
  }
}

function Annotation({ annotation, fallbackIndex }: { annotation: GeometryAnnotation; fallbackIndex: number }) {
  const position = ANNOTATION_POSITIONS[annotation.position] ?? {
    x: 112 + fallbackIndex * 58,
    y: 292,
  };

  return (
    <text x={position.x} y={position.y} textAnchor="middle">
      {annotation.label}
    </text>
  );
}

function buildLabels(shape: GeometryShape, labels: string[] | undefined): SvgLabel[] {
  const defaults = SHAPE_LABELS[shape];
  if (!labels?.length) {
    return defaults;
  }

  return defaults.map((defaultLabel, index) => ({
    ...defaultLabel,
    text: labels[index] || defaultLabel.text,
  }));
}

function isSupportedShape(shape: string): shape is GeometryShape {
  return shape in SHAPE_LABELS;
}
