export default function Logo({ light = false }) {
  return (
    <span className="flex items-center gap-2.5">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="8" fill={light ? '#FFFFFF' : '#23694A'} />
        <circle cx="16" cy="16" r="8.5" fill="none" stroke={light ? '#23694A' : '#FFFFFF'} strokeWidth="3"
          strokeDasharray="40 14" strokeLinecap="round" transform="rotate(-90 16 16)" />
      </svg>
      <span className={`text-[17px] font-extrabold ${light ? 'text-white' : 'text-ink'}`}>FitPlate</span>
    </span>
  )
}
