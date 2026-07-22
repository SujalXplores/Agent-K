"use client";

import { domAnimation, LazyMotion, MotionConfig } from "motion/react";
import type { PropsWithChildren } from "react";

import { MOTION_TRANSITION } from "./constants";

export function MotionProvider({ children }: PropsWithChildren) {
  return (
    <LazyMotion features={domAnimation} strict>
      <MotionConfig
        reducedMotion="user"
        transition={MOTION_TRANSITION.default}
      >
        {children}
      </MotionConfig>
    </LazyMotion>
  );
}
