import { content } from "@/lib/config/content";

export function HeroHeadline() {
  const { headlineLead, headlineEmphasis } = content.hero;

  return (
    <>
      {headlineLead} <span className="text-primary">{headlineEmphasis}</span>
    </>
  );
}
