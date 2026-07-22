'use client';

import { useReducedMotion } from 'motion/react';
import { useEffect } from 'react';

/**
 * Reveal orchestrator — drives scroll-triggered entrance animations.
 *
 * The hidden initial state is applied via CSS (see `globals.css` `.content-reveal`
 * rules) using the `reveal-ready` class set by the inline theme script before
 * hydration. This avoids hydration mismatches because React never sets inline
 * styles for the initial state.
 *
 * When an element enters the viewport, we simply remove the `pending` state and
 * add a `revealed` state. The CSS transition handles the actual animation,
 * keeping the JS lightweight and avoiding motion's transform-string parser.
 */
export function MotionOrchestrator() {
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const elements = Array.from(
      document.querySelectorAll<HTMLElement>('.content-reveal'),
    );
    if (elements.length === 0) return;

    // When reduced motion is on, reveal everything immediately.
    if (reduceMotion) {
      elements.forEach((element) => {
        element.dataset.revealState = 'revealed';
      });
      return;
    }

    const intro = elements.filter((element) => {
      const rect = element.getBoundingClientRect();
      return rect.top < window.innerHeight && rect.bottom > 0;
    });
    const introSet = new Set(intro);

    // Reveal above-the-fold elements on the next frame with a gentle stagger.
    const introTimers: ReturnType<typeof setTimeout>[] = [];
    const introFrame = requestAnimationFrame(() => {
      intro.forEach((element, index) => {
        introTimers.push(
          setTimeout(() => {
            element.dataset.revealState = 'revealed';
          }, 60 + index * 55),
        );
      });
    });

    // Watch below-the-fold elements and reveal them when they enter the viewport.
    const observers: IntersectionObserver[] = [];
    elements
      .filter((element) => !introSet.has(element))
      .forEach((element) => {
        const requestedAmount = Number(element.dataset.revealThreshold) || 0.18;
        const amount = Math.max(0.16, Math.min(requestedAmount, 0.5));

        const observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                element.dataset.revealState = 'revealed';
                observer.disconnect();
              }
            });
          },
          {
            threshold: amount,
            rootMargin: '0px 0px -6% 0px',
          },
        );
        observer.observe(element);
        observers.push(observer);
      });

    return () => {
      cancelAnimationFrame(introFrame);
      introTimers.forEach(clearTimeout);
      observers.forEach((obs) => obs.disconnect());
      elements.forEach((element) => {
        delete element.dataset.revealState;
      });
    };
  }, [reduceMotion]);

  return null;
}
