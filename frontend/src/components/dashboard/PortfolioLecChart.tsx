import { useMemo } from "react";
import ReactECharts from "echarts-for-react/lib/core";
import { echarts, baseGrid } from "@/lib/echarts";
import { useChartTheme } from "@/lib/useChartTheme";
import { fmt } from "@/lib/format";
import { densifyLogX, interpolateY, returnPeriod } from "@/lib/interpolate";

interface PortfolioLecChartProps {
  curve: [number, number][];
  appetite?: number | null;
  height?: number;
}

export function PortfolioLecChart({
  curve,
  appetite,
  height = 280,
}: PortfolioLecChartProps) {
  const chartTheme = useChartTheme();
  const option = useMemo(() => {
    const markLines: Record<string, unknown>[] = [];
    if (appetite != null && appetite > 0) {
      markLines.push({
        xAxis: appetite,
        lineStyle: { color: "#D98DA3", type: "dashed", width: 1.5 },
        label: { formatter: "Appetite", color: "#D98DA3", fontSize: 10 },
      });
    }

    // Resample to a dense log-x grid so the cursor glides (see LecChart.tsx).
    const filtered = curve.filter(([x]) => x > 0);
    const withPlateau: [number, number][] =
      filtered.length > 0
        ? [[filtered[0][0] / 10, filtered[0][1]], ...filtered]
        : filtered;
    const seriesData = densifyLogX(withPlateau, 600);
    const xMin = seriesData.length > 0 ? seriesData[0][0] : undefined;

    return {
      grid: baseGrid,
      tooltip: {
        trigger: "axis",
        confine: true,
        triggerOn: "mousemove",
        throttle: 0,
        axisPointer: {
          type: "cross",
          snap: false,
          animation: false,
          label: { show: false },
          lineStyle: { color: "#647085", type: "dashed", width: 1 },
        },
        formatter: (params: { axisValue?: number | string; value?: [number, number] }[]) => {
          const p = params[0];
          const cursorX = Number(p.axisValue ?? p.value?.[0] ?? 0);
          const exceed = interpolateY(seriesData, cursorX);
          return (
            `<b>${fmt.money(cursorX)}</b>` +
            `<br/>P(Total &gt; x) = ${fmt.pct(exceed, 2)}` +
            `<br/><span style="color:#647085">${returnPeriod(exceed)}</span>`
          );
        },
      },
      xAxis: {
        type: "log",
        name: "Annual portfolio loss",
        nameLocation: "middle",
        nameGap: 30,
        nameTextStyle: { color: "#647085", fontSize: 11 },
        min: xMin,
        axisLabel: { formatter: (v: number) => fmt.money(v), hideOverlap: true },
      },
      yAxis: {
        type: "value",
        name: "Exceedance",
        nameLocation: "middle",
        nameGap: 44,
        nameTextStyle: { color: "#647085", fontSize: 11 },
        min: 0,
        max: 1,
        axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` },
      },
      series: [
        {
          type: "line",
          data: seriesData,
          showSymbol: false,
          smooth: 0.4,
          // No `sampling: "lttb"` — it would collapse the plateau anchors.
          lineStyle: { color: "#A28AD9", width: 2 },
          areaStyle: { color: "rgba(162, 138, 217, 0.12)" },
          animationDurationUpdate: 150,
          markLine: markLines.length
            ? { symbol: "none", data: markLines, animation: false }
            : undefined,
        },
      ],
    };
  }, [curve, appetite]);

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
