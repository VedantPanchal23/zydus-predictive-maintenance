/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        zydus: {
          50: '#f4f6f8',
          100: '#e1e7ec',
          500: '#3b82f6',
          900: '#1e3a8a',
          950: '#172554',
          darkBg: '#0f172a',
          darkCard: '#1e293b'
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
