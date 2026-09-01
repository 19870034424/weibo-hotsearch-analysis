/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#cc785c",
        "primary-active": "#a9583e",
        "primary-disabled": "#e6dfd8",
        ink: "#141413",
        body: "#3d3d3a",
        "body-strong": "#252523",
        muted: "#6c6a64",
        "muted-soft": "#8e8b82",
        hairline: "#e6dfd8",
        "hairline-soft": "#ebe6df",
        canvas: "#faf9f5",
        "surface-soft": "#f5f0e8",
        "surface-card": "#efe9de",
        "surface-cream-strong": "#e8e0d2",
        "surface-dark": "#181715",
        "surface-dark-elevated": "#252320",
        "surface-dark-soft": "#1f1e1b",
        "on-primary": "#ffffff",
        "on-dark": "#faf9f5",
        "on-dark-soft": "#a09d96",
        "accent-teal": "#5db8a6",
        "accent-amber": "#e8a55a",
        success: "#5db872",
        warning: "#d4a017",
        error: "#c64545"
      },
      spacing: {
        xxs: "4px",
        xs: "8px",
        sm: "12px",
        md: "16px",
        lg: "24px",
        xl: "32px",
        xxl: "48px",
        section: "96px"
      },
      borderRadius: {
        xs: "4px",
        sm: "6px",
        md: "8px",
        lg: "12px",
        xl: "16px",
        pill: "9999px",
        full: "9999px"
      },
      fontFamily: {
        serif: ["Georgia", "Cormorant Garamond", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"]
      },
      fontSize: {
        "display-xl": "4rem",
        "display-lg": "3rem",
        "display-md": "2.25rem",
        "display-sm": "1.75rem",
        "title-lg": "1.375rem",
        "title-md": "1.125rem",
        "title-sm": "1rem",
        "body-md": "1rem",
        "body-sm": "0.875rem",
        caption: "0.8125rem",
        "caption-uppercase": "0.75rem",
        code: "0.875rem",
        button: "0.875rem",
        "nav-link": "0.875rem"
      },
      fontWeight: {
        normal: 400,
        medium: 500
      },
      lineHeight: {
        "display-xl": 1.05,
        "display-lg": 1.1,
        "display-md": 1.15,
        "display-sm": 1.2,
        "title-lg": 1.3,
        "title-md": 1.4,
        "title-sm": 1.4,
        "body-md": 1.55,
        "body-sm": 1.55,
        caption: 1.4,
        "caption-uppercase": 1.4,
        code: 1.6,
        button: 1,
        "nav-link": 1.4
      },
      letterSpacing: {
        "display-xl": "-1.5px",
        "display-lg": "-1px",
        "display-md": "-0.5px",
        "display-sm": "-0.3px",
        "caption-uppercase": "1.5px"
      }
    },
  },
  plugins: [],
}
