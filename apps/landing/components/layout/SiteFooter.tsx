'use client';

import { ArrowUp } from 'lucide-react';

import { Reveal } from '../motion/Reveal';
import { smoothScrollTo } from '../motion/scrollUtils';
import { Brand } from '../ui/Brand';
import styles from './SiteFooter.module.css';

export function SiteFooter() {
  function handleBackToTop(event: React.MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    smoothScrollTo(0, { duration: 1.8 });
  }

  return (
    <Reveal as="footer" className={styles.footer} amount={0.2} variant="fade">
      <Brand compact />
      <p>Evidence-producing incident response for observable AI.</p>
      <div className={styles.meta}>
        <span>Built for controlled proof</span>
        <span>© 2026 Agent K</span>
        <a href="#top" aria-label="Back to top" onClick={handleBackToTop}>
          <ArrowUp aria-hidden="true" />
        </a>
      </div>
    </Reveal>
  );
}
