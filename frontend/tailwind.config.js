/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#4A6FFF',
        success: '#34C759',
        warning: '#FF9500',
        danger: '#FF3B30',
        bonus: '#AF52DE',
        bg: '#F5F7FA',
        text: '#1C1C1E',
        subtext: '#6E6E73',
      },
      fontFamily: {
        sans: ['Pretendard', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'soft-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.55' },
        },
      },
      animation: {
        'fade-in-up': 'fade-in-up 0.35s ease-out both',
        'soft-pulse': 'soft-pulse 1.6s ease-in-out infinite',
      },
      boxShadow: {
        card: '0 4px 20px rgba(28, 28, 30, 0.06)',
        ring: '0 0 0 4px rgba(74, 111, 255, 0.15)',
      },
    },
  },
  plugins: [],
};
