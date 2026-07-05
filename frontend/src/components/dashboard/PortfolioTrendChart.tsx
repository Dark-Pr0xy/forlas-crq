import { useMemo } from "react";
import ReactECharts from "echarts-for-react/lib/core";
import { echarts, baseGrid } from "@/lib/echarts";
import { useChartTheme } from "@/lib/useChartTheme";
import { fmt } from "@/lib/format";
import type { PortfolioSnapshot } from "@/types/api";

export function PortfolioTrendChart({
  snapshots,
  height = 240,
}: {
  snapshots: PortfolioSnapshot[];
  height?: number;
}) {
  const chartTheme = useChartTheme();
  const option = useMemo(() => {
    const sorted = [...snapshots].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );
    const x = sorted.map((s) => new Date(s.created_at).toISOString().slice(0, 10));
    return {
      grid: { ...baseGrid, top: 24, right: 24 },
      tooltip: { trigger: "axis", valueFormatter: (v: number) => fmt.money(v) },
      legend: { top: 0, right: 0, textStyle: { color: "#647085", fontSize: 11 } },
      xAxis: { type: "category", data: x, boundaryGap: false },
      yAxis: {
        type: "value",
        axisLabel: { formatter: (v: number) => fmt.money(v) },
      },
      series: [
        {
          name: "ALE",
          type: "line",
          smooth: true,
          showSymbol: false,
          data: sorted.map((s) => s.total_ale),
          lineStyle: { color: "#7A92F4", width: 2 },
          areaStyle: { color: "rgba(122,146,244,0.12)" },
        },
        {
          name: "P95",
          type: "line",
          smooth: true,
          showSymbol: false,
          data: sorted.map((s) => s.total_p95),
          lineStyle: { color: "#E3C07B", width: 2 },
        },
        {
          name: "P99",
          type: "line",
          smooth: true,
          showSymbol: false,
          data: sorted.map((s) => s.total_p99),
          lineStyle: { color: "#D98DA3", width: 2 },
        },
      ],
    };
  }, [snapshots]);

  if (snapshots.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted">
        No portfolio snapshots yet. Use &quot;Capture snapshot&quot; to start tracking trends.
      </p>
    );
  }

  return (
    <ReactECharts
      echarts={echarts}
      option={option}
      theme={chartTheme}
      style={{ height, width: "100%" }}
      notMerge
      lazyUpdate
    />
  );
}
