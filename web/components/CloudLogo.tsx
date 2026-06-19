// CloudPull brand mark: a cloud with a download arrow. Color is configurable
// so it works on both the light landing and the dark app shell.

export default function CloudLogo({
  size = 26,
  color = "#ff5500",
  className,
}: {
  size?: number;
  color?: string;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      className={className}
      aria-hidden
    >
      <path
        d="M33 60 a14 14 0 0 1 -1 -28 a18 18 0 0 1 34 3 a12 12 0 0 1 1 25"
        stroke={color}
        strokeWidth="9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M50 48 L50 74" stroke={color} strokeWidth="9" strokeLinecap="round" />
      <path
        d="M40 65 L50 76 L60 65"
        stroke={color}
        strokeWidth="9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
