/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sigma: {
          50:  "#fcfaf7",
          100: "#f8efe2",
          200: "#F3E3D0",
          300: "#D2C4B4",
          400: "#AACDDC",
          500: "#81A6C6",
          600: "#6788A5",
          700: "#526E88",
          800: "#374A5C",
          900: "#24313C",
          950: "#161D23",
        },
        neon: {
          cyan:   "#AACDDC",
          violet: "#81A6C6",
          green:  "#D2C4B4",
          amber:  "#F3E3D0",
        },
      },
      fontFamily: {
        display: ["'Syne'", "sans-serif"],
        mono:    ["'JetBrains Mono'", "monospace"],
        body:    ["'DM Sans'", "sans-serif"],
      },
      backgroundImage: {
        "grid-pattern": "linear-gradient(rgba(129,166,198,.08) 1px, transparent 1px), linear-gradient(90deg, rgba(170,205,220,.08) 1px, transparent 1px)",
        "hero-gradient": "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(129,166,198,0.24), transparent), radial-gradient(circle at 82% 8%, rgba(243,227,208,0.14), transparent 26%)",
        "card-gradient": "linear-gradient(135deg, rgba(129,166,198,0.08) 0%, rgba(170,205,220,0.06) 58%, rgba(243,227,208,0.05) 100%)",
      },
      backgroundSize: {
        "grid-size": "40px 40px",
      },
      animation: {
        "float": "float 6s ease-in-out infinite",
        "pulse-slow": "pulse 4s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
        "spin-slow": "spin 8s linear infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};
