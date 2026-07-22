import type { ReactNode } from "react";

import styles from "./SectionIntro.module.css";

type SectionIntroProps = {
  number: string;
  label: string;
  title: ReactNode;
  description: ReactNode;
  inverse?: boolean;
  className?: string;
};

export function SectionIntro({
  number,
  label,
  title,
  description,
  inverse = false,
  className,
}: SectionIntroProps) {
  return (
    <header
      className={[styles.intro, inverse ? styles.inverse : "", className]
        .filter(Boolean)
        .join(" ")}
    >
      <div className={styles.kicker}>
        <span>{number}</span>
        {label}
      </div>
      <h2 className={styles.title}>{title}</h2>
      <p className={styles.description}>{description}</p>
    </header>
  );
}
