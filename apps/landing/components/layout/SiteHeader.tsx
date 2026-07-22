'use client';

import {
  AnimatePresence,
  m,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
} from 'motion/react';
import { ArrowUpRight, Menu, Moon, Sun, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { navItems } from '../../data/content';
import { MOTION_TRANSITION } from '../motion/constants';
import { smoothScrollTo } from '../motion/scrollUtils';
import { Brand } from '../ui/Brand';
import styles from './SiteHeader.module.css';

type Theme = 'light' | 'dark';

const themeColors: Record<Theme, string> = {
  light: '#f2f2f7',
  dark: '#0c0c0e',
};

function updateThemeColor(theme: Theme) {
  document
    .getElementById('theme-color')
    ?.setAttribute('content', themeColors[theme]);
}

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [theme, setTheme] = useState<Theme | null>(null);
  const menuTriggerRef = useRef<HTMLButtonElement>(null);
  const reduceMotion = useReducedMotion();
  const { scrollY } = useScroll();

  useMotionValueEvent(scrollY, 'change', (latest) => {
    const nextScrolled = latest > 20;
    setScrolled((current) =>
      current === nextScrolled ? current : nextScrolled,
    );
  });

  useEffect(() => {
    const current: Theme =
      document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
    setTheme(current);
    updateThemeColor(current);
  }, []);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key !== 'Escape' || !menuOpen) return;
      setMenuOpen(false);
      menuTriggerRef.current?.focus();
    }

    function closeAtDesktop() {
      if (window.innerWidth > 860) setMenuOpen(false);
    }

    window.addEventListener('keydown', closeOnEscape);
    window.addEventListener('resize', closeAtDesktop);
    return () => {
      window.removeEventListener('keydown', closeOnEscape);
      window.removeEventListener('resize', closeAtDesktop);
    };
  }, [menuOpen]);

  function toggleTheme() {
    const current: Theme =
      document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
    const nextTheme: Theme = current === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = nextTheme;
    document.documentElement.style.colorScheme = nextTheme;
    updateThemeColor(nextTheme);

    try {
      localStorage.setItem('agent-k-theme', nextTheme);
    } catch {
      // The visible theme still updates when storage is unavailable.
    }

    setTheme(nextTheme);
  }

  function handleNavClick(
    event: React.MouseEvent<HTMLAnchorElement>,
    href: string,
  ) {
    if (!href.startsWith('#')) return;
    event.preventDefault();
    smoothScrollTo(href, { offset: -90, duration: 1.6 });
    setMenuOpen(false);
  }

  const themeLabel =
    theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';

  return (
    <header className={`${styles.header} ${scrolled ? styles.scrolled : ''}`}>
      <nav className={styles.nav} aria-label="Primary navigation">
        <Brand />

        <div className={styles.desktopLinks}>
          {navItems.map((item) => (
            <a
              href={item.href}
              key={item.href}
              onClick={(e) => handleNavClick(e, item.href)}
            >
              {item.label}
            </a>
          ))}
        </div>

        <div className={styles.actions}>
          <button
            className={styles.themeToggle}
            type="button"
            onClick={toggleTheme}
            aria-label={themeLabel}
            title={themeLabel}
          >
            <Sun className={styles.sunIcon} aria-hidden="true" />
            <Moon className={styles.moonIcon} aria-hidden="true" />
          </button>
          <a className={styles.demoLink} href="#live-demo">
            <span>Watch it reason</span>
            <ArrowUpRight aria-hidden="true" />
          </a>
          <button
            className={styles.menuToggle}
            ref={menuTriggerRef}
            type="button"
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}
            onClick={() => setMenuOpen((current) => !current)}
          >
            {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
          </button>
        </div>

        <AnimatePresence initial={false}>
          {menuOpen ? (
            <m.div
              className={styles.mobileMenu}
              id="mobile-navigation"
              initial={
                reduceMotion ? false : { opacity: 0, y: -10, scale: 0.98 }
              }
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={
                reduceMotion
                  ? { opacity: 0 }
                  : { opacity: 0, y: -8, scale: 0.98 }
              }
              transition={
                reduceMotion
                  ? MOTION_TRANSITION.instant
                  : MOTION_TRANSITION.entrance
              }
            >
              {navItems.map((item, index) => (
                <a
                  href={item.href}
                  key={item.href}
                  onClick={(e) => handleNavClick(e, item.href)}
                >
                  <span>0{index + 1}</span>
                  {item.label}
                </a>
              ))}
              <a
                className={styles.mobileDemo}
                href="#live-demo"
                onClick={(e) => handleNavClick(e, '#live-demo')}
              >
                Run the controlled incident
                <ArrowUpRight aria-hidden="true" />
              </a>
            </m.div>
          ) : null}
        </AnimatePresence>

        <noscript>
          <div className={styles.noScriptNav}>
            {navItems.map((item, index) => (
              <a href={item.href} key={item.href}>
                <span>0{index + 1}</span>
                {item.label}
              </a>
            ))}
            <a className={styles.mobileDemo} href="#live-demo">
              Run the controlled incident
              <ArrowUpRight aria-hidden="true" />
            </a>
          </div>
        </noscript>
      </nav>
    </header>
  );
}
