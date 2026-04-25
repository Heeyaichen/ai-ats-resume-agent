/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
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
        label: "#1d1d1f",
        secondary: "#86868b",
        tertiary: "#aeaeb2",
        surface: "#f5f5f7",
        separator: "rgba(60, 60, 67, 0.12)",
        accent: {
          DEFAULT: "#0071e3",
          hover: "#0077ed",
        },
      },
    },
  },
  plugins: [],
};
