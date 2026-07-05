import { THEME_NAME, THEME_NAME_DARK } from "@/lib/echarts";
import { useTheme } from "@/store/theme";

/** Returns the ECharts theme name matching the active app theme (M5). */
export function useChartTheme(): string {
  return useTheme((s) => s.theme) === "dark" ? THEME_NAME_DARK : THEME_NAME;
}
