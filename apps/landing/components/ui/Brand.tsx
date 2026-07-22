import styles from "./Brand.module.css";

type BrandProps = {
  className?: string;
  compact?: boolean;
};

export function Brand({ className, compact = false }: BrandProps) {
  return (
    <a
      className={[styles.brand, compact ? styles.compact : "", className]
        .filter(Boolean)
        .join(" ")}
      href="#top"
      aria-label="Agent K home"
    >
      <span className={styles.mark} aria-hidden="true">
        <span>K</span>
        <i />
      </span>
      <span className={styles.name}>Agent K</span>
    </a>
  );
}
