/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Neutral surface scale — warm-cool slate for depth.
        surface: {
          0: "#ffffff",
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e9edf3",
          300: "#d5dce6",
        },
        ink: {
          DEFAULT: "#0e1424",
          soft: "#3b455a",
          muted: "#6b7688",
          faint: "#98a2b3",
        },
        // Indigo → violet brand.
        brand: {
          50: "#eef1ff",
          100: "#e0e6ff",
          200: "#c6d0ff",
          300: "#a3b0ff",
          400: "#7c8cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
        },
        violet: { 500: "#8b5cf6", 600: "#7c3aed" },
        // Sidebar deep space palette.
        night: {
          900: "#0b1020",
          800: "#111834",
          700: "#1b2450",
          accent: "#6d78ff",
        },
        // Risk as a status palette (paired with labels/icons in the UI).
        risk: { low: "#059669", medium: "#d97706", high: "#e1152f" },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ['"Space Grotesk"', '"Plus Jakarta Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(16,24,40,0.04), 0 4px 16px -4px rgba(16,24,40,0.08)",
        lift: "0 8px 30px -6px rgba(16,24,40,0.14)",
        glow: "0 8px 24px -6px rgba(79,70,229,0.45)",
      },
      borderRadius: { xl: "0.9rem", "2xl": "1.15rem" },
      backgroundImage: {
        "brand-grad": "linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%)",
        "night-grad": "linear-gradient(180deg,#0b1020 0%,#141c3a 55%,#1a1147 100%)",
        "app-grad": "radial-gradient(1200px 600px at 100% -10%, rgba(124,58,237,0.06), transparent 60%), radial-gradient(900px 500px at -10% 0%, rgba(79,70,229,0.06), transparent 55%)",
      },
      keyframes: {
        "fade-up": { "0%": { opacity: 0, transform: "translateY(6px)" }, "100%": { opacity: 1, transform: "translateY(0)" } },
      },
      animation: { "fade-up": "fade-up 0.4s ease both" },
    },
  },
  plugins: [],
};
