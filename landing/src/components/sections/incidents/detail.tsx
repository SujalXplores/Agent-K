export function Detail({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p className="text-muted-foreground font-mono text-[11px] tracking-widest uppercase">
        {label}
      </p>
      <p className="text-foreground/85 mt-0.5 text-sm leading-relaxed">
        {text}
      </p>
    </div>
  );
}
