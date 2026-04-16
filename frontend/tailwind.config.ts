import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#050816",
        surface: "#0b1220",
        panel: "#101a2f",
        border: "#1e293b",
        copy: "#d8e1f0",
        muted: "#7f8da3",
        success: "#16c784",
        warning: "#f59e0b",
        danger: "#ef4444",
        accent: "#38bdf8",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(56, 189, 248, 0.12), 0 8px 32px rgba(15, 23, 42, 0.4)",
      },
    },
  },
  plugins: [],
};

export default config;
