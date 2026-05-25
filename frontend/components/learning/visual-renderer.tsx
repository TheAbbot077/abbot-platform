"use client";

import type { ReactNode } from "react";
import { Shapes } from "lucide-react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { prepareFunctionPlot } from "@/lib/function-plot";
import type { VisualContent } from "@/lib/types";
import { MathMarkdown } from "@/components/learning/math-markdown";
import { ChartRenderer } from "@/components/learning/chart-renderer";
import { GeometryRenderer } from "@/components/learning/geometry-renderer";

export function VisualRenderer({ visualContent }: { visualContent: VisualContent }) {
  if (visualContent.render_mode === "function_plot") {
    return <FunctionPlot visualContent={visualContent} />;
  }

  if (visualContent.render_mode === "geometry_diagram" && visualContent.type === "geometry") {
    return (
      <VisualFrame visualContent={visualContent}>
        <GeometryRenderer visualContent={visualContent} />
      </VisualFrame>
    );
  }

  if (visualContent.render_mode === "statistics_chart" && ["chart", "table"].includes(visualContent.type)) {
    return (
      <VisualFrame visualContent={visualContent}>
        <ChartRenderer visualContent={visualContent} />
      </VisualFrame>
    );
  }

  return <VisualFallback visualContent={visualContent} />;
}

function FunctionPlot({ visualContent }: { visualContent: VisualContent }) {
  const plotResult = prepareFunctionPlot(visualContent.expression);

  if (!plotResult.ok) {
    return (
      <VisualFrame visualContent={visualContent}>
        <p className="rounded-md border border-dashed bg-background p-3 text-sm text-muted-foreground">
          The Abbot suggested a visual, but this expression is not safe to graph yet. Try asking for a simpler function like <span className="font-medium">y = x^2</span>.
        </p>
      </VisualFrame>
    );
  }

  return (
    <VisualFrame visualContent={visualContent}>
      <div className="h-64 w-full overflow-hidden rounded-2xl border bg-background p-2 sm:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart margin={{ top: 12, right: 18, bottom: 12, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="x"
              domain={[-10, 10]}
              tickCount={9}
              type="number"
              allowDataOverflow
              label={{ value: "x", position: "insideBottomRight", offset: -4 }}
            />
            <YAxis
              domain={["auto", "auto"]}
              tickCount={7}
              type="number"
              width={48}
              label={{ value: "y", angle: -90, position: "insideLeft" }}
            />
            <ReferenceLine x={0} stroke="hsl(var(--foreground))" strokeOpacity={0.45} />
            <ReferenceLine y={0} stroke="hsl(var(--foreground))" strokeOpacity={0.45} />
            <Tooltip
              formatter={(value) => [Number(value).toFixed(3), "y"]}
              labelFormatter={(label) => `x = ${Number(label).toFixed(3)}`}
            />
            {plotResult.segments.map((segment, index) => (
              <Line
                key={`${plotResult.expression}-${index}`}
                data={segment}
                dataKey="y"
                dot={false}
                isAnimationActive={false}
                stroke="hsl(var(--primary))"
                strokeWidth={2.5}
                type="monotone"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </VisualFrame>
  );
}

function VisualFallback({ visualContent }: { visualContent: VisualContent }) {
  return (
    <VisualFrame visualContent={visualContent}>
      <p className="rounded-2xl border border-dashed bg-background p-3 text-sm text-muted-foreground">
        The Abbot suggested this visual. Rendering for {visualContent.render_mode.replace("_", " ")} is coming next.
      </p>
    </VisualFrame>
  );
}

function VisualFrame({ visualContent, children }: { visualContent: VisualContent; children: ReactNode }) {
  return (
    <div className="max-w-full overflow-hidden rounded-2xl border bg-muted/40 p-3">
      <div className="space-y-3">
        <div className="flex items-start gap-3">
          <Shapes className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
          <div className="min-w-0 space-y-1">
            <p className="text-sm font-semibold">{visualContent.title}</p>
            <p className="text-sm text-muted-foreground">{visualContent.description}</p>
            {visualContent.expression ? (
              <MathMarkdown className="text-xs" muted>
                {visualContent.expression}
              </MathMarkdown>
            ) : null}
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}
