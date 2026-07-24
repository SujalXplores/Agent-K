"use client";

import { useEffect, useState } from "react";

export function useActiveSection(
  ids: readonly string[],
  rootMargin = "-45% 0px -50% 0px"
): string {
  const [activeId, setActiveId] = useState<string>(ids[0] ?? "");
  const key = ids.join("|");

  useEffect(() => {
    const sectionIds = key.length > 0 ? key.split("|") : [];
    const elements = sectionIds
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);

    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (visible.length > 0) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin, threshold: [0, 0.25, 0.5, 0.75, 1] }
    );

    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [key, rootMargin]);

  return activeId;
}
