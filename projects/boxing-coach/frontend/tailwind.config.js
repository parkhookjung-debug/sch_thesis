/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: '#0b0d12',
        canvas: '#13151c',
        accent: '#ff3d57',
      },
      fontFamily: {
        display: ['"Bebas Neue"', 'Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
