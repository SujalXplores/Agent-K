import dynamic from 'next/dynamic';

import { Hero } from '../components/sections/Hero';

// Below-the-fold sections are code-split to keep the initial bundle lean and
// protect LCP / First Contentful Paint. Each loads on demand as the user
// scrolls toward it, with a lightweight skeleton fallback.
const Problem = dynamic(
  () => import('../components/sections/Problem').then((m) => m.Problem),
  {
    loading: () => <SectionSkeleton />,
  },
);
const Laws = dynamic(
  () => import('../components/sections/Laws').then((m) => m.Laws),
  {
    loading: () => <SectionSkeleton />,
  },
);
const Protocol = dynamic(
  () => import('../components/sections/Protocol').then((m) => m.Protocol),
  {
    loading: () => <SectionSkeleton />,
  },
);
const Proof = dynamic(
  () => import('../components/sections/Proof').then((m) => m.Proof),
  {
    loading: () => <SectionSkeleton />,
  },
);
const SelfTelemetry = dynamic(
  () =>
    import('../components/sections/SelfTelemetry').then((m) => m.SelfTelemetry),
  { loading: () => <SectionSkeleton /> },
);
const FinalCta = dynamic(
  () => import('../components/sections/FinalCta').then((m) => m.FinalCta),
  {
    loading: () => <SectionSkeleton />,
  },
);

function SectionSkeleton() {
  return (
    <section
      aria-hidden="true"
      style={{
        minHeight: '60vh',
        width: 'var(--page)',
        marginInline: 'auto',
      }}
    />
  );
}

export default function HomePage() {
  return (
    <main id="main-content">
      <Hero />
      <Problem />
      <Laws />
      <Protocol />
      <Proof />
      <SelfTelemetry />
      <FinalCta />
    </main>
  );
}
