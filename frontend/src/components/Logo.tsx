export default function Logo({ size = 42, className = "" }: { size?: number, className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`text-zinc-100 transition-colors duration-200 hover:text-[var(--accent)] ${className}`}
    >
      {/* Starting point circle */}
      <circle cx="18" cy="5" r="1.5" />
      
      {/* S-curve line */}
      <path d="M 15 5 H 8 A 4 4 0 0 0 8 13 H 16 A 4 4 0 0 1 16 21 H 7" />
      
      {/* Outlined arrowhead (pointing left) with a slight gap from the line */}
      <path d="M 8 17 L 4 21 L 8 25" />
    </svg>
  );
}
