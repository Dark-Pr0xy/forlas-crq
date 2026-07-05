import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/**
 * Design tokens from the build spec — soft pastel palette, 8px radius, tight
 * spacing scale, no neon, no glassmorphism. Linear/Arc/Mercury direction.
 */
const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--c-background)",
        surface: "var(--c-surface)",
        ink: "var(--c-text)",
        muted: "var(--c-muted)",
        border: "var(--c-border)",
        accent: {
          DEFAULT: "var(--c-accent)",
          soft: "var(--c-accent-soft)",
          foreground: "#ffffff",
        },
        teal: { DEFAULT: "var(--c-teal)", soft: "var(--c-teal-soft)" },
        plum: { DEFAULT: "var(--c-plum)", soft: "var(--c-plum-soft)" },
        amber: { DEFAULT: "var(--c-amber)", soft: "var(--c-amber-soft)" },
        rose: { DEFAULT: "var(--c-rose)", soft: "var(--c-rose-soft)" },
        success: { DEFAULT: "var(--c-success)", soft: "var(--c-success-soft)" },
      },
      borderRadius: {
        DEFAULT: "8px",
        sm: "6px",
        lg: "10px",
      },
      spacing: {
        "1.5": "6px",
        "3.5": "14px",
      },
      fontSize: {
        xs: ["11.5px", { lineHeight: "1.4" }],
        sm: ["12.5px", { lineHeight: "1.45" }],
        base: ["13.5px", { lineHeight: "1.45" }],
        md: ["14px", { lineHeight: "1.45" }],
        lg: ["15px", { lineHeight: "1.4" }],
        xl: ["17px", { lineHeight: "1.35" }],
        "2xl": ["22px", { lineHeight: "1.25" }],
        "3xl": ["28px", { lineHeight: "1.2" }],
      },
      transitionDuration: { DEFAULT: "150ms" },
      boxShadow: {
        card: "0 1px 2px rgba(20,30,50,.04), 0 4px 18px rgba(20,30,50,.05)",
        modal: "0 20px 60px rgba(20,30,50,.18)",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ['"SF Mono"', "Consolas", "Menlo", "monospace"],
      },
    },
  },
  plugins: [animate],
};

export default config;
