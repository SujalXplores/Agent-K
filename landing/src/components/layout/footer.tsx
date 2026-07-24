import { ArrowUpRight } from "lucide-react";

import { FooterFlicker } from "@/components/layout/footer-flicker";
import { Logo } from "@/components/layout/logo";
import { content } from "@/lib/config/content";
import { siteConfig } from "@/lib/config/site";

const lawDots = [
  { key: "law-1", label: "Evidence", className: "bg-law-1" },
  { key: "law-2", label: "Action", className: "bg-law-2" },
  { key: "law-3", label: "Telemetry", className: "bg-law-3" },
];

function isExternal(href: string) {
  return href.startsWith("http");
}

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="relative overflow-hidden">
      <div className="border-border/60 mx-auto w-full max-w-(--container-max) border-t">
        <div className="flex flex-col gap-12 px-6 py-14 md:flex-row md:justify-between">
          <div className="flex max-w-xs flex-col gap-5">
            <Logo />
            <p className="text-muted-foreground text-sm leading-relaxed">
              {content.footer.tagline}
            </p>
            <div className="flex items-center gap-4">
              {lawDots.map((dot) => (
                <span
                  key={dot.key}
                  className="text-muted-foreground inline-flex items-center gap-1.5 text-xs"
                >
                  <span className={`size-2 rounded-full ${dot.className}`} />
                  {dot.label}
                </span>
              ))}
            </div>
          </div>

          <nav
            aria-label="Footer"
            className="grid grid-cols-2 gap-8 sm:grid-cols-3 lg:gap-16 lg:pl-10"
          >
            {content.footer.columns.map((column) => (
              <div key={column.title} className="flex flex-col gap-3">
                <h3 className="text-foreground mb-1 text-sm font-semibold">
                  {column.title}
                </h3>
                {column.links
                  .filter((link) => link.href.length > 0)
                  .map((link) => (
                    <a
                      key={link.label}
                      href={link.href}
                      {...(isExternal(link.href)
                        ? { target: "_blank", rel: "noopener noreferrer" }
                        : {})}
                      className="group text-muted-foreground hover:text-foreground inline-flex w-fit items-center gap-1 text-[15px] leading-snug transition-colors"
                    >
                      {link.label}
                      <span className="border-border flex size-4 items-center justify-center rounded border opacity-0 transition-all duration-300 ease-out group-hover:translate-x-0.5 group-hover:opacity-100">
                        <ArrowUpRight className="size-3" />
                      </span>
                    </a>
                  ))}
              </div>
            ))}
          </nav>
        </div>

        <div className="border-border/60 text-muted-foreground flex flex-col gap-4 border-t px-6 py-6 text-xs sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-2xl leading-relaxed">
            {content.footer.disclosure}
          </p>
          <p className="shrink-0">
            &copy; {year} {siteConfig.name}
          </p>
        </div>
      </div>

      <FooterFlicker />
    </footer>
  );
}
