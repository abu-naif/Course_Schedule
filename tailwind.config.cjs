module.exports = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: {
              50: '#eff6ff',
              100: '#dbeafe',
              200: '#bfdbfe',
              300: '#93c5fd',
              400: '#60a5fa',
              500: '#3b82f6',
              600: '#2563eb',
              700: '#1d4ed8',
              800: '#1e40af',
              900: '#1e3a8a',
            },
            dark: {
              bg: '#0f172a',
              card: '#1e293b',
              border: '#334155',
              hover: '#2d3b4f'
            }
          }
        }
      }
    };
module.exports.content = ["./templates/**/*.html", "./static/js/**/*.js"];
