/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#e8edf5',
          100: '#c5d0e6',
          200: '#9fb1d5',
          300: '#7891c4',
          400: '#5a7ab7',
          500: '#3c62aa',
          600: '#2e4f8a',
          700: '#1e3a5f',
          800: '#152a47',
          900: '#0c1b2f',
        }
      }
    },
  },
  plugins: [],
}
