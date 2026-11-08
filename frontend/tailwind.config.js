/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Manrope', 'system-ui', 'sans-serif'] },
      colors: {
        canvas: '#F3F5F2',
        ink: '#16211C',
        muted: '#5E6B64',
        line: '#DDE3DC',
        brand: {
          50: '#EEF6F1', 100: '#D6EADF', 200: '#AFD4BF', 400: '#4F9A73',
          500: '#2F7A55', 600: '#23694A', 700: '#1C523A', 900: '#12352A',
        },
        protein: '#3567B5',
        carbs: '#D99A1E',
        fat: '#B4537A',
        water: '#2C9AB7',
      },
      borderRadius: { panel: '14px' },
    },
  },
  plugins: [],
}
