import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'DZ Wissensbase',
  tagline: 'Alle Publikationen von Dezernat Zukunft – durchsuchbar und interaktiv',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://philippasigl.github.io',
  baseUrl: '/dz-wiki/',

  organizationName: 'philippasigl',
  projectName: 'dz-wiki',

  onBrokenLinks: 'warn',

  i18n: {
    defaultLocale: 'de',
    locales: ['de'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: 'wiki',
          editUrl: undefined, // Disable "edit this page"
        },
        blog: false, // Disable blog
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/dz-social-card.jpg',
    colorMode: {
      defaultMode: 'light',
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'DZ Wissensbase',
      items: [
        {
          to: '/wiki/',
          label: 'Wiki',
          position: 'left',
        },
        {
          href: '/dz-wiki/',
          label: 'Publikationsgraph',
          position: 'left',
        },
        {
          href: 'https://dezernatzukunft.org',
          label: 'dezernatzukunft.org',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Wissensbase',
          items: [
            {
              label: 'Wiki',
              to: '/wiki',
            },
            {
              label: 'Themen',
              to: '/wiki/themen/bundeshaushalt',
            },
          ],
        },
        {
          title: 'Dezernat Zukunft',
          items: [
            {
              label: 'Website',
              href: 'https://dezernatzukunft.org',
            },
            {
              label: 'Twitter',
              href: 'https://twitter.com/dezernatz',
            },
            {
              label: 'LinkedIn',
              href: 'https://linkedin.com/company/dezernat-zukunft',
            },
          ],
        },
        {
          title: 'Rechtliches',
          items: [
            {
              label: 'Impressum',
              href: 'https://philippa-sigl-gloeckner.de/impressum',
            },
            {
              label: 'Datenschutz',
              href: 'https://philippa-sigl-gloeckner.de/datenschutz',
            },
            {
              label: 'Lizenz (CC BY-NC 4.0)',
              href: 'https://creativecommons.org/licenses/by-nc/4.0/deed.de',
            },
          ],
        },
      ],
      copyright: `Beta-Deployment © ${new Date().getFullYear()} Philippa Sigl-Glöckner · Inhalte: Dezernat Zukunft e.V., lizenziert unter <a href="https://creativecommons.org/licenses/by-nc/4.0/deed.de" target="_blank" rel="noopener">CC BY-NC 4.0</a>`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
