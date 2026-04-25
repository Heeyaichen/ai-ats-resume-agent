/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          '"Helvetica Neue"',
          "Arial",
          "sans-serif",
        ],
      },
      colors: {
        base: "#08090d",
        "glass-panel": "rgba(255, 255, 255, 0.03)",
        "glass-border": "rgba(255, 255, 255, 0.08)",
        "glass-hover": "rgba(255, 255, 255, 0.05)",
        label: "#e4e4e9",
        secondary: "#8b8b9e",
        tertiary: "#5a5a6e",
        separator: "rgba(255, 255, 255, 0.06)",
        accent: {
          DEFAULT: "#22d3ee",
          hover: "#06b6d4",
          muted: "rgba(34, 211, 238, 0.12)",
        },
        success: "#34d399",
        warning: "#fbbf24",
        danger: "#f87171",
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
