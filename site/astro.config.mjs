import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

import mdx from "@astrojs/mdx";

export default defineConfig({
  site: "https://karnesth.github.io",
  base: "/fsg",
  compressHTML: true,

  i18n: {
      locales: ["en", "de"],
      defaultLocale: "en",
      fallback: {
          de: "en",
      },
      routing: {
          prefixDefaultLocale: false,
          fallbackType: "rewrite",
      },
  },

  vite: {
      plugins: [tailwindcss()],
  },

  integrations: [mdx()],
});