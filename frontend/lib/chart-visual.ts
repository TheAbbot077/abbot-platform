import type { ChartDataPoint, ChartType, VisualContent } from "@/lib/types";

export type ChartVisualResult =
  | {
      ok: true;
      chartType: ChartType;
      xLabel: string;
      yLabel: string;
      data: ChartDataPoint[];
    }
  | {
      ok: false;
      reason: string;
    };

const CHART_TYPES = new Set<ChartType>(["bar", "line", "pie", "table"]);

export function prepareChartVisual(visualContent: VisualContent): ChartVisualResult {
  if (!["chart", "table"].includes(visualContent.type) || visualContent.render_mode !== "statistics_chart") {
    return { ok: false, reason: "This visual is not a supported chart." };
  }

  const chartType = visualContent.type === "table" && !visualContent.chart_type ? "table" : visualContent.chart_type;
  if (!chartType || !CHART_TYPES.has(chartType)) {
    return { ok: false, reason: "This chart type is not supported yet." };
  }

  if (!Array.isArray(visualContent.data)) {
    return { ok: false, reason: "This chart does not include readable data." };
  }

  const data = visualContent.data
    .slice(0, 12)
    .map((point) => ({
      label: sanitizeChartLabel(point.label),
      value: Number(point.value),
    }))
    .filter((point) => point.label && Number.isFinite(point.value));

  if (data.length === 0) {
    return { ok: false, reason: "This chart does not include enough valid data to render." };
  }

  return {
    ok: true,
    chartType,
    xLabel: sanitizeChartLabel(visualContent.x_label || "Label"),
    yLabel: sanitizeChartLabel(visualContent.y_label || "Value"),
    data,
  };
}

function sanitizeChartLabel(value: string): string {
  return String(value || "").trim().slice(0, 40);
}
