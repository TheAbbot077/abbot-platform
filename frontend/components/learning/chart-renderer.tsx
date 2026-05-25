"use client";

import type { ReactElement } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { prepareChartVisual } from "@/lib/chart-visual";
import type { ChartDataPoint, VisualContent } from "@/lib/types";

const PIE_COLORS = [
  "hsl(var(--primary))",
  "hsl(var(--accent))",
  "hsl(var(--muted-foreground))",
  "hsl(var(--secondary-foreground))",
  "hsl(var(--destructive))",
];

export function ChartRenderer({ visualContent }: { visualContent: VisualContent }) {
  const chart = prepareChartVisual(visualContent);

  if (!chart.ok) {
    return (
      <p className="rounded-2xl border border-dashed bg-background p-3 text-sm text-muted-foreground">
        The Abbot suggested a chart, but the chart data needs a quick cleanup before it can render.
      </p>
    );
  }

  if (chart.chartType === "table") {
    return <SimpleTable data={chart.data} xLabel={chart.xLabel} yLabel={chart.yLabel} />;
  }

  if (chart.chartType === "pie") {
    return (
      <ChartShell title={visualContent.title}>
        <PieChart>
          <Tooltip formatter={(value) => [Number(value).toLocaleString(), chart.yLabel]} />
          <Legend />
          <Pie data={chart.data} dataKey="value" nameKey="label" outerRadius="72%" label>
            {chart.data.map((point, index) => (
              <Cell key={point.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      </ChartShell>
    );
  }

  if (chart.chartType === "line") {
    return (
      <ChartShell title={visualContent.title}>
        <LineChart data={chart.data} margin={{ top: 12, right: 18, bottom: 12, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" label={{ value: chart.xLabel, position: "insideBottom", offset: -6 }} />
          <YAxis width={48} label={{ value: chart.yLabel, angle: -90, position: "insideLeft" }} />
          <Tooltip formatter={(value) => [Number(value).toLocaleString(), chart.yLabel]} />
          <Line dataKey="value" dot stroke="hsl(var(--primary))" strokeWidth={2.5} type="monotone" />
        </LineChart>
      </ChartShell>
    );
  }

  return (
    <ChartShell title={visualContent.title}>
      <BarChart data={chart.data} margin={{ top: 12, right: 18, bottom: 12, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="label" label={{ value: chart.xLabel, position: "insideBottom", offset: -6 }} />
        <YAxis width={48} label={{ value: chart.yLabel, angle: -90, position: "insideLeft" }} />
        <Tooltip formatter={(value) => [Number(value).toLocaleString(), chart.yLabel]} />
        <Bar dataKey="value" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ChartShell>
  );
}

function ChartShell({ title, children }: { title: string; children: ReactElement }) {
  return (
    <div className="h-64 w-full overflow-hidden rounded-2xl border bg-background p-2 sm:h-80" role="img" aria-label={title}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

function SimpleTable({ data, xLabel, yLabel }: { data: ChartDataPoint[]; xLabel: string; yLabel: string }) {
  return (
    <div className="overflow-x-auto rounded-2xl border bg-background">
      <table className="w-full min-w-72 text-left text-sm">
        <caption className="sr-only">
          {xLabel} and {yLabel}
        </caption>
        <thead className="bg-muted/60">
          <tr>
            <th className="px-3 py-2 font-semibold">{xLabel}</th>
            <th className="px-3 py-2 font-semibold">{yLabel}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((point) => (
            <tr key={`${point.label}-${point.value}`} className="border-t">
              <td className="px-3 py-2">{point.label}</td>
              <td className="px-3 py-2">{point.value.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
