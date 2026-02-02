/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      keyframes: {
        ellipsis: {
          '0%, 20%': { opacity: '0' },
          '40%, 100%': { opacity: '1' },
        },
        indeterminate: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(400%)' },
        },
      },
      animation: {
        ellipsis: 'ellipsis 1.5s infinite',
        indeterminate: 'indeterminate 1.5s infinite ease-in-out',
      },
      colors: {
        // PER Brand Color Palette
        primary: {
          50: '#f0f4f8',
          100: '#d9e2ed',
          200: '#b3c5db',
          300: '#8da8c9',
          400: '#5a7ba8',
          500: '#1d3d6f',  // PER Blue
          600: '#1a3763',
          700: '#162e54',
          800: '#122545',
          900: '#0e1c36',
          950: '#091221',
        },
        accent: {
          50: '#eefbfb',
          100: '#d4f4f5',
          200: '#afe9eb',
          300: '#7ddcdf',
          400: '#51bcbf',  // PER Teal
          500: '#3aa8ab',
          600: '#2d8a8d',
          700: '#276f71',
          800: '#245a5c',
          900: '#224b4d',
          950: '#112e2f',
        },
        gray: {
          50: '#f9f9f9',
          100: '#f2f2f2',
          200: '#e6e6e6',
          300: '#cccccc',  // PER Gray
          400: '#a6a6a6',
          500: '#808080',
          600: '#666666',
          700: '#4d4d4d',
          800: '#333333',
          900: '#1a1a1a',
          950: '#0d0d0d',
        },
        success: {
          500: '#22c55e',
          600: '#16a34a',
        },
        warning: {
          500: '#eab308',
          600: '#ca8a04',
        }
      },
      fontFamily: {
        sans: ['Proxima Nova', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}

