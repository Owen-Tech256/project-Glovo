export function Logo({ className = "h-7 w-7", mono = false }: { className?: string; mono?: boolean }) {
  const stroke = mono ? "currentColor" : "#ff6a39";
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <circle cx="16" cy="16" r="15" stroke="currentColor" strokeOpacity="0.15" />
      <path
        d="M6 22C10 22 10 14 14 14C18 14 18 22 22 22"
        stroke={stroke}
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeDasharray="0.5 5.2"
      />
      <circle cx="6" cy="22" r="2.2" fill="currentColor" />
      <circle cx="22" cy="22" r="2.2" fill={stroke} />
      <path d="M14 6L14 14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="14" cy="6" r="2.4" fill="currentColor" />
    </svg>
  );
}

export function BrandWordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-display font-semibold text-lg tracking-tight ${className}`}>
      <Logo />
      Routeley
    </span>
  );
}
