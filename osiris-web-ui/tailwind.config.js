/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        osiris: {
          bg: "#0b0f14",
          panel: "#131a22",
          accent: "#22d3ee",
        },
      },
    },
  },
  plugins: [],
};
