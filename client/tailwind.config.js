/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  safelist: [
    "bg-blue-100",
    "bg-green-100",
    "bg-purple-100",
    "bg-orange-100",
    "text-blue-600",
    "text-green-600",
    "text-purple-600",
    "text-orange-600",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
