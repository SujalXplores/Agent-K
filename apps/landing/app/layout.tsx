import type { Metadata, Viewport } from 'next';
import { Inter, Sora } from 'next/font/google';
import type { ReactNode } from 'react';

import { SiteFooter } from '../components/layout/SiteFooter';
import { SiteHeader } from '../components/layout/SiteHeader';
import { MotionOrchestrator } from '../components/motion/MotionOrchestrator';
import { MotionProvider } from '../components/motion/MotionProvider';
import { ScrollProgress } from '../components/motion/ScrollProgress';
import { SmoothScroll } from '../components/motion/SmoothScroll';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
  weight: ['400', '500', '600', '700', '800', '900'],
  preload: true,
  fallback: [
    '-apple-system',
    'BlinkMacSystemFont',
    'SF Pro Text',
    'Helvetica Neue',
    'system-ui',
    'sans-serif',
  ],
  adjustFontFallback: true,
});

const sora = Sora({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-sora',
  weight: ['400', '500', '600', '700', '800'],
  preload: true,
  fallback: [
    'var(--font-inter)',
    '-apple-system',
    'BlinkMacSystemFont',
    'system-ui',
    'sans-serif',
  ],
  adjustFontFallback: true,
});

const themeScript = `(() => {
  const root = document.documentElement;
  const themeColor = document.getElementById("theme-color");

  try {
    const stored = localStorage.getItem("agent-k-theme");
    const preferred = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    const theme = stored === "dark" || stored === "light" ? stored : preferred;
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    themeColor?.setAttribute("content", theme === "dark" ? "#0c0c0e" : "#f2f2f7");
  } catch {
    root.dataset.theme = "light";
    root.style.colorScheme = "light";
    themeColor?.setAttribute("content", "#f2f2f7");
  }

  // Mark reveal-ready before hydration so the hidden state is applied via CSS
  // (not inline styles) — prevents hydration attribute mismatches.
  try {
    if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
      root.classList.add("reveal-ready");
    }
  } catch {}
})();`;

export const metadata: Metadata = {
  title: 'Agent K — Proof before action',
  description:
    'An incident-response agent that proves every claim with evidence, gates every action with policy, and records every decision as telemetry.',
  applicationName: 'Agent K',
  authors: [{ name: 'Agent K' }],
  keywords: [
    'AI incident response',
    'evidence-first operations',
    'AI observability',
    'policy-gated automation',
  ],
  openGraph: {
    type: 'website',
    title: 'Agent K — Proof before action',
    description: 'The incident agent that has to show its work.',
    siteName: 'Agent K',
  },
  twitter: {
    card: 'summary',
    title: 'Agent K — Proof before action',
    description: 'The incident agent that has to show its work.',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  colorScheme: 'light dark',
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html
      className={`${inter.variable} ${sora.variable}`}
      lang="en"
      suppressHydrationWarning
    >
      <head>
        <meta id="theme-color" name="theme-color" content="#f2f2f7" />
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={inter.className}>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <MotionProvider>
          <SmoothScroll>
            <MotionOrchestrator />
            <ScrollProgress />
            <SiteHeader />
            {children}
            <SiteFooter />
          </SmoothScroll>
        </MotionProvider>
      </body>
    </html>
  );
}
