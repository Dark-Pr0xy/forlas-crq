import { useMemo } from "react";
import ReactECharts from "echarts-for-react/lib/core";
import { echarts, baseGrid } from "@/lib/echarts";
import { useChartTheme } from "@/lib/useChartTheme";
import { fmt } from "@/lib/format";
import { densifyLogX, interpolateY, returnPeriod } from "@/lib/interpolate";
import type { ReferenceLine } from "@/types/api";

interface LecChartProps {
  curve: [number, number][];
  referenceLines?: ReferenceLine[];
  height?: number;
}

export function LecChart({ curve, referenceLines = [], height = 280 }: LecChartProps) {
  const chartTheme = useChartTheme();
  const option = useMemo(() => {
    const markLines = referenceLines.map((rl) => ({
      xAxis: rl.value,
      lineStyle: { color: rl.color, type: "dashed", width: 1.5 },
      label: { formatter: rl.label, color: rl.color, fontSize: 10 },
    }));

    // The engine samples the LEC evenly by rank, leaving the high-loss tail
    // (e.g. 500k–1M) sparse in x — the cursor jumps between distant points.
    // Prepend a flat plateau one decade left of the first point (so the curve
    // fills to the wall), then resample everything to a dense uniform log-x
    // grid so the cursor always has a nearby point and glides smoothly.
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
        // Zero throttle so the tooltip updates on every mouse frame; combined
        // with the dense plateau anchors below, this gives continuous tracking.
        throttle: 0,
        axisPointer: {
          type: "cross",
          snap: false,
          animation: false,
          label: { show: false },
          lineStyle: { color: "#647085", type: "dashed", width: 1 },
        },
        formatter: (params: any[]) => {
          const p = params[0];
          // params[0].value[0] gives the nearest sample's x; we use the
          // axisPointer's actual x (axisValue) and interpolate so the readout
          // tracks the cursor sub-sample-smoothly.
          const cursorX = Number(p.axisValue ?? p.value?.[0] ?? 0);
          const exceed = interpolateY(seriesData, cursorX);
          return (
            `<b>${fmt.money(cursorX)}</b>` +
            `<br/>P(L &gt; x) = ${fmt.pct(exceed, 2)}` +
            `<br/><span style="color:#647085">${returnPeriod(exceed)}</span>`
          );
        },
      },
      xAxis: {
        type: "log",
        name: "Annual loss",
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
          // No `sampling: "lttb"` — it collapses runs of identical y values
          // (i.e. the entire plateau anchor fan) back down to 2 points, which
          // is exactly what made the cursor snap. ~860 raw points is well
          // inside ECharts' native render budget.
          lineStyle: { color: "#7A92F4", width: 2 },
          areaStyle: { color: "rgba(122, 146, 244, 0.10)" },
          animationDurationUpdate: 150,
          markLine: markLines.length
            ? { symbol: "none", data: markLines, animation: false }
            : undefined,
        },
      ],
    };
  }, [curve, referenceLines]);

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
