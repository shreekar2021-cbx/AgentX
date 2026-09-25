/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#1d3028',
        muted: '#77877e',
        canvas: '#f5f7f2',
        leaf: { 50: '#eef6e9', 100: '#e2efd8', 500: '#68a348', 600: '#4f8737', 700: '#3c6e2c' },
        lime: '#d6ee8d',
        amber: '#e5a43b',
      },
      boxShadow: { card: '0 8px 30px rgba(36, 61, 45, .055)' },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}
