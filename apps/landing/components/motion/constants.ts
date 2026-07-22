type CubicBezier = readonly [number, number, number, number];

export const MOTION_DURATION = {
  fast: 0.2,
  base: 0.35,
  reveal: 0.7,
  hero: 0.9,
} as const;

/**
 * Apple HIG easing curves.
 * - `ease`: standard ease, used for general transitions
 * - `out`: ease-out — the signature Apple entrance curve (fast start, slow settle)
 * - `inOut`: symmetric ease for state changes
 * - `spring`: subtle overshoot for delightful micro-interactions
 */
export const MOTION_EASE = {
  ease: [0.25, 0.1, 0.25, 1] as CubicBezier,
  out: [0.16, 1, 0.3, 1] as CubicBezier,
  inOut: [0.4, 0, 0.2, 1] as CubicBezier,
  spring: [0.34, 1.56, 0.64, 1] as CubicBezier,
} as const;

export const MOTION_TRANSITION = {
  default: {
    duration: MOTION_DURATION.base,
    ease: MOTION_EASE.inOut,
  },
  entrance: {
    duration: MOTION_DURATION.base,
    ease: MOTION_EASE.out,
  },
  reveal: {
    duration: MOTION_DURATION.reveal,
    ease: MOTION_EASE.out,
  },
  hero: {
    duration: MOTION_DURATION.hero,
    ease: MOTION_EASE.out,
  },
  movement: {
    type: "spring",
    stiffness: 400,
    damping: 30,
    mass: 1,
  },
  chart: {
    duration: 0.5,
    ease: MOTION_EASE.out,
  },
  status: {
    duration: 0.2,
    ease: MOTION_EASE.out,
  },
  fast: {
    duration: MOTION_DURATION.fast,
    ease: MOTION_EASE.ease,
  },
  instant: {
    duration: 0,
  },
} as const;
