# fsg docs

Source of the fsg documentation at [karnesth.github.io/fsg](https://karnesth.github.io/fsg/).

## Built with

- [Astro](https://astro.build) with MDX content
- [Tailwind CSS](https://tailwindcss.com) 4
- kd-ui, the UI library of Karnes Development: a Tailwind CSS plugin (`assets/js/kd-ui.js`) with the components and
  the Karnes theme, plus a CLI that scaffolds blocks and views for Astro, React, Vue, Leptos, Blade, HTML and Qt.
  Every component in `src/components/` started as a kd-ui block. The plugin is committed, so building the site needs
  no kd-ui installation.

## Features

- English and German, falling back to English for missing pages
- Content as one MDX file per page and language
- Changelog generated from the repository's `CHANGELOG.md`
- Full-text search with Pagefind, running in the browser
- No cookies, no tracking, fonts served locally

## Translating

Add the language to `i18n.locales` in `astro.config.mjs`, then add `src/i18n/<locale>.json` and
`src/content/docs/<locale>/`. Run `yarn dev` to preview.