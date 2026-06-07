import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1b2430",
        paper: "#f7f4ee",
        line: "#d8d2c6",
        moss: "#52745f",
        wine: "#7f3348",
        steel: "#3f6173"
      }
    }
  },
  plugins: []
};

export default config;

