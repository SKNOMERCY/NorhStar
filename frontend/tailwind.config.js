/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        cinzel: ['Inter', 'sans-serif'], // Remap cinzel to clean sans-serif for backward compat
      },
      colors: {
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
        surface: {
          base: '#080911',
          card: 'rgba(18, 22, 34, 0.65)',
          overlay: 'rgba(255, 255, 255, 0.05)',
          border: 'rgba(255, 255, 255, 0.08)',
        },
        celestial: {
          950: '#080911',
          900: '#0d101d',
          850: '#111526',
          800: '#161b31',
          750: '#1d233f',
          700: '#252d4e',
          600: '#323c65',
          500: '#48558a',
          gold: '#818cf8',       // Modernized to luminous indigo
          goldBright: '#a5b4fc',
          goldMuted: '#6366f1',
          goldDark: '#312e81',
          cyan: '#38bdf8',
          cyanDark: '#0284c7',
          emerald: '#10b981',
          amber: '#f59e0b',
          crimson: '#f43f5e',
        }
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37), inset 0 1px 0 0 rgba(255, 255, 255, 0.06)',
        'glass-hover': '0 12px 40px -4px rgba(0, 0, 0, 0.5), 0 0 24px 0 rgba(99, 102, 241, 0.15)',
        'glow-indigo': '0 0 25px -5px rgba(99, 102, 241, 0.4)',
        'glow-cyan': '0 0 25px -5px rgba(56, 189, 248, 0.4)',
      }
    },
  },
  plugins: [],
}
