/**
 * Shared ECharts theme aligning with the soft pastel palette.
 *
 * We register a single theme name (`crq`) once at module load so individual
 * chart components can opt into it without duplicating the colour list.
 */

import * as echarts from "echarts/core";
import {
  BarChart,
  LineChart,
} from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  MarkAreaComponent,
  DataZoomComponent,
  TitleComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  MarkAreaComponent,
  DataZoomComponent,
  TitleComponent,
  CanvasRenderer,
]);

export const THEME_NAME = "crq";
export const THEME_NAME_DARK = "crq-dark";

const SERIES_COLORS = [
  "#7A92F4", // accent
  "#78C5B7", // teal
  "#A28AD9", // plum
  "#E3C07B", // amber
  "#D98DA3", // rose
  "#8CC5A0", // success
];

echarts.registerTheme(THEME_NAME, {
  color: SERIES_COLORS,
  backgroundColor: "transparent",
  textStyle: {
    fontFamily:
      "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    color: "#1B2230",
  },
  axisPointer: { lineStyle: { color: "#647085" } },
  categoryAxis: {
    axisLine: { lineStyle: { color: "#E8EBF2" } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { color: "#647085", fontSize: 11 },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: "#EEF1F6" } },
    axisLabel: { color: "#647085", fontSize: 11 },
  },
});

echarts.registerTheme(THEME_NAME_DARK, {
  color: SERIES_COLORS,
  backgroundColor: "transparent",
  textStyle: {
    fontFamily:
      "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    color: "#ECF0FA",
  },
  axisPointer: { lineStyle: { color: "#8A93A6" } },
  categoryAxis: {
    axisLine: { lineStyle: { color: "#232C40" } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { color: "#8A93A6", fontSize: 11 },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: "#1D2538" } },
    axisLabel: { color: "#8A93A6", fontSize: 11 },
  },
});

export { echarts };

/**
 * Chart grid margins. Bumped from the original (left 44 / bottom 30) so that
 * axis names ("loss", "exceedance") don't get clipped against the card border,
 * and the rightmost log-axis tick label has room to render in full.
 */
export const baseGrid = {
  left: 60,
  right: 32,
  top: 20,
  bottom: 50,
  containLabel: true,
} as const;
