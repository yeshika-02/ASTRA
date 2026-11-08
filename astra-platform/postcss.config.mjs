// Required for Tailwind CSS v4: without it `@import "tailwindcss"` generates no utility classes.
const config = {
  plugins: {
    '@tailwindcss/postcss': {},
  },
};

export default config;
