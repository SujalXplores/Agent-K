'use client';

import { useReducedMotion } from 'motion/react';
import { useEffect } from 'react';
import type { PropsWithChildren } from 'react';

/**
 * Momentum-based smooth scrolling powered by Lenis, synced with Framer Motion's
 * scroll system. Honors `prefers-reduced-motion` by disabling smoothing entirely
 * (native scroll is used instead) and skips on touch/coarse-pointer devices where
 * the OS already provides momentum scrolling.
 *
 * The active Lenis instance is exposed on `window.__lenis` so anchor links and
 * scroll-to-top buttons can use `lenis.scrollTo()` for buttery-smooth navigation.
 */
export function SmoothScroll({ children }: PropsWithChildren) {
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (reduceMotion) return;

    // Coarse pointers (touch) already have native momentum scroll — layering Lenis
    // on top would fight the OS and hurt performance on mobile.
    const isCoarsePointer = window.matchMedia('(pointer: coarse)').matches;
    if (isCoarsePointer) return;

    let rafId = 0;
    let lenis: import('lenis').default | null = null;

    void import('lenis').then(({ default: Lenis }) => {
      lenis = new Lenis({
        duration: 1.1,
        easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        smoothWheel: true,
        wheelMultiplier: 1,
        touchMultiplier: 1.5,
        lerp: 0.1,
      });

      window.__lenis = lenis;

      const raf = (time: number) => {
        lenis?.raf(time);
        rafId = requestAnimationFrame(raf);
      };
      rafId = requestAnimationFrame(raf);
    });

    return () => {
      cancelAnimationFrame(rafId);
      lenis?.destroy();
      lenis = null;
      delete window.__lenis;
    };
  }, [reduceMotion]);

  return <>{children}</>;
}
