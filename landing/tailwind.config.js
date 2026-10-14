/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: '1.5rem',
      screens: { '2xl': '1200px' },
    },
    extend: {
      colors: {
        // Azul de marca Soldigem (#2B5EA7) — misma escala que el ERP.
        brand: {
          50: '#ecf2fa',
          100: '#d6e3f3',
          200: '#aec6e5',
          300: '#7da0d3',
          400: '#4a79bb',
          500: '#2B5EA7',
          600: '#234e8d',
          700: '#1d4175',
          800: '#193761',
          900: '#142c4e',
        },
        // Semánticos (mismos que el ERP)
        success: { DEFAULT: '#16a34a', 500: '#22c55e' },
        warning: { DEFAULT: '#d97706', 500: '#f59e0b' },
        danger: { DEFAULT: '#e11d48', 500: '#f43f5e' },
        // Neutros fríos para el tema oscuro
        ink: {
          950: '#0a0d14',
          900: '#0f131c',
          800: '#161b26',
          700: '#1f2633',
          600: '#2b3341',
          500: '#3a4454',
          400: '#5b6678',
          300: '#8b96a8',
          200: '#b9c2d0',
          100: '#dde3ec',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        lg: '0.75rem',
        md: '0.5rem',
        sm: '0.375rem',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.6s cubic-bezier(0.23,1,0.32,1) forwards',
        'fade-in': 'fade-in 0.6s ease forwards',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
