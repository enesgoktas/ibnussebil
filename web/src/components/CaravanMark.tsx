export function CaravanMark({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 112 36"
      role="img"
      aria-label="Üç deveden oluşan kervan"
      xmlns="http://www.w3.org/2000/svg"
    >
      <g fill="currentColor">
        <g transform="translate(0 0)">
          <path d="M4 18c0-5 3-8 7-8 3 0 5 2 6 5l2-7 2-1 2 3-2 2-1 4v7h-2v-5H9v5H7v-5H5v-1z" />
          <path d="M8 22v9M10.5 22v9M17 22v9M19.5 22v9" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          <path d="M4 18c-1.5 1.5-1.5 4-.5 5.5" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" />
          <path d="M22 8l1-2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        </g>
        <g transform="translate(40 0)">
          <path d="M4 18c0-5 3-8 7-8 3 0 5 2 6 5l2-7 2-1 2 3-2 2-1 4v7h-2v-5H9v5H7v-5H5v-1z" />
          <path d="M8 22v9M10.5 22v9M17 22v9M19.5 22v9" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          <path d="M4 18c-1.5 1.5-1.5 4-.5 5.5" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" />
          <path d="M22 8l1-2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        </g>
        <g transform="translate(80 0)">
          <path d="M4 18c0-5 3-8 7-8 3 0 5 2 6 5l2-7 2-1 2 3-2 2-1 4v7h-2v-5H9v5H7v-5H5v-1z" />
          <path d="M8 22v9M10.5 22v9M17 22v9M19.5 22v9" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          <path d="M4 18c-1.5 1.5-1.5 4-.5 5.5" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" />
          <path d="M22 8l1-2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        </g>
      </g>
      <g fill="none" stroke="var(--gold, #c79a3b)" strokeWidth="1.5" strokeLinecap="round">
        <path d="M23 16Q33 20 43 16" />
        <path d="M63 16Q73 20 83 16" />
        <circle cx="23" cy="16" r="1.2" fill="var(--gold, #c79a3b)" stroke="none" />
        <circle cx="43" cy="16" r="1.2" fill="var(--gold, #c79a3b)" stroke="none" />
        <circle cx="63" cy="16" r="1.2" fill="var(--gold, #c79a3b)" stroke="none" />
        <circle cx="83" cy="16" r="1.2" fill="var(--gold, #c79a3b)" stroke="none" />
      </g>
    </svg>
  );
}
