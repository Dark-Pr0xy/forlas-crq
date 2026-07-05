import { useMemo } from "react";
import ReactECharts from "echarts-for-react/lib/core";
import { echarts, baseGrid } from "@/lib/echarts";
import { useChartTheme } from "@/lib/useChartTheme";
import type { SensitivityEntry } from "@/types/api";

interface SensitivityTornadoProps {
  data: SensitivityEntry[];
  height?: number;
}

export function SensitivityTornado({ data, height = 220 }: SensitivityTornadoProps) {
  const chartTheme = useChartTheme();
  const option = useMemo(() => {
    const sorted = [...data].sort((a, b) => Math.abs(a.corr) - Math.abs(b.corr));
    return {
      grid: { ...baseGrid, left: 160 },
      tooltip: {
        trigger: "axis",
        formatter: (params: any[]) => {
          const p = params[0];
          return `<b>${p.name}</b><br/>rank corr: ${p.value.toFixed(3)}`;
        },
      },
      xAxis: {
        type: "value",
        min: -1,
        max: 1,
        axisLabel: { formatter: (v: number) => v.toFixed(1) },
      },
      yAxis: {
        type: "category",
        data: sorted.map((d) => d.label),
      },
      series: [
        {
          type: "bar",
          data: sorted.map((d) => ({
            value: d.corr,
            itemStyle: { color: d.corr >= 0 ? "#7A92F4" : "#D98DA3" },
          })),
          barWidth: 14,
          label: {
            show: true,
            position: "right",
            formatter: (p: any) => p.value.toFixed(2),
            fontSize: 11,
            color: "#647085",
          },
        },
      ],
    };
  }, [data]);

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
