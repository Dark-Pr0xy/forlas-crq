import { useMemo } from "react";
import ReactECharts from "echarts-for-react/lib/core";
import { echarts, baseGrid } from "@/lib/echarts";
import { useChartTheme } from "@/lib/useChartTheme";
import { fmt } from "@/lib/format";
import type { HistogramPayload, ReferenceLine } from "@/types/api";

interface HistogramChartProps {
  histogram: HistogramPayload;
  referenceLines?: ReferenceLine[];
  height?: number;
}

export function HistogramChart({
  histogram,
  referenceLines = [],
  height = 280,
}: HistogramChartProps) {
  const chartTheme = useChartTheme();
  const option = useMemo(() => {
    const data: [number, number][] = histogram.counts.map((c, i) => [
      histogram.lo + (i + 0.5) * histogram.w,
      c,
    ]);

    const markLines = referenceLines.map((rl) => ({
      xAxis: rl.value,
      lineStyle: { color: rl.color, type: "dashed", width: 1.5 },
      label: { formatter: rl.label, color: rl.color, fontSize: 10 },
    }));

    return {
      grid: baseGrid,
      tooltip: {
        trigger: "axis",
        confine: true,
        // `shadow` highlights the bucket's full territory band rather than
        // drawing a thin vertical line at the cursor's raw x position. This
        // keeps the indicator and the reported bar perfectly aligned for any
        // cursor position inside the bucket.
        axisPointer: {
          type: "shadow",
          shadowStyle: { color: "rgba(122, 146, 244, 0.12)" },
        },
        formatter: (params: { value: [number, number] }[]) => {
          const p = params[0];
          const center = p.value[0] as number;
          const halfWidth = histogram.w / 2;
          const lo = Math.max(0, center - halfWidth);
          const hi = center + halfWidth;
          return (
            `<b>${fmt.money(lo)} – ${fmt.money(hi)}</b>` +
            `<br/>centre: ${fmt.money(center)}` +
            `<br/>iterations: ${(p.value[1] as number).toLocaleString("en-AU")}`
          );
        },
      },
      xAxis: {
        type: "value",
        name: "Annual loss",
        nameLocation: "middle",
        nameGap: 30,
        nameTextStyle: { color: "#647085", fontSize: 11 },
        axisLabel: { formatter: (v: number) => fmt.money(v), hideOverlap: true },
      },
      yAxis: {
        type: "value",
        name: "Iterations",
        nameLocation: "middle",
        nameGap: 44,
        nameTextStyle: { color: "#647085", fontSize: 11 },
      },
      series: [
        {
          type: "bar",
          data,
          barWidth: "98%",
          itemStyle: { color: "#7A92F4", opacity: 0.85 },
          emphasis: { itemStyle: { color: "#5e7af0" } },
          markLine: markLines.length
            ? { symbol: "none", data: markLines, animation: false }
            : undefined,
        },
        ...(histogram.tail_count > 0
          ? [
              {
                type: "bar",
                data: [[histogram.cap, histogram.tail_count]],
                barWidth: 6,
                itemStyle: { color: "#D98DA3" },
                tooltip: {
                  formatter: () =>
                    `Tail (> ${fmt.money(histogram.cap)})<br/>${histogram.tail_count.toLocaleString()} iters · mean ${fmt.money(
                      histogram.tail_mean,
                    )}`,
                },
              },
            ]
          : []),
      ],
    };
  }, [histogram, referenceLines]);

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
