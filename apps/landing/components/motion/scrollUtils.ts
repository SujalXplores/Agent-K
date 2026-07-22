/**
 * Smooth-scroll to a target element or top of page.
 *
 * Prefers the active Lenis instance (exposed on `window.__lenis`) for momentum-based
 * scrolling that matches the rest of the site. Falls back to native
 * `Element.scrollIntoView({ behavior: 'smooth' })` when Lenis isn't running
 * (reduced motion, touch devices, or not yet loaded).
 */

declare global {
  interface Window {
    __lenis?: import('lenis').default;
  }
}

export function smoothScrollTo(
  target: string | number,
  options?: { offset?: number; duration?: number },
) {
  const lenis = typeof window !== 'undefined' ? window.__lenis : undefined;
  const reduceMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (lenis && !reduceMotion) {
    lenis.scrollTo(target, {
      offset: options?.offset ?? 0,
      duration: options?.duration ?? 1.4,
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    });
    return;
  }

  // Native fallback
  if (typeof target === 'number') {
    window.scrollTo({ top: target, behavior: reduceMotion ? 'auto' : 'smooth' });
  } else {
    const el = document.querySelector<HTMLElement>(target);
    el?.scrollIntoView({
      behavior: reduceMotion ? 'auto' : 'smooth',
      block: 'start',
    });
  }
}
