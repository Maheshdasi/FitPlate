/**
 * Calorie gauge: the outer ring fills with calories eaten, and the inner
 * ring is split into protein / carbs / fat energy so the user sees both
 * "how much" and "what kind" at a glance.
 */
export default function CalorieRing({ consumed, goal, protein = 0, carbs = 0, fat = 0, size = 200 }) {
  const stroke = size * 0.075
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const ratio = goal > 0 ? Math.min(consumed / goal, 1) : 0
  const over = consumed > goal * 1.05

  const inner = r - stroke * 1.6
  const ic = 2 * Math.PI * inner
  const energy = protein * 4 + carbs * 4 + fat * 9
  const parts = energy > 0
    ? [[protein * 4 / energy, '#3567B5'], [carbs * 4 / energy, '#D99A1E'], [fat * 9 / energy, '#B4537A']]
    : []
  let offset = 0
  const remaining = Math.round(goal - consumed)

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(0,0,0,0.06)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={over ? '#DC2626' : '#2F7A55'}
          strokeWidth={stroke} strokeLinecap="round" strokeDasharray={`${c * ratio} ${c}`}
          style={{ transition: 'stroke-dasharray .6s ease' }} />
        <circle cx={size / 2} cy={size / 2} r={inner} fill="none" stroke="rgba(0,0,0,0.04)" strokeWidth={stroke * 0.45} />
        {parts.map(([share, color], i) => {
          const len = ic * share * ratio
          const el = (
            <circle key={i} cx={size / 2} cy={size / 2} r={inner} fill="none" stroke={color}
              strokeWidth={stroke * 0.45} strokeDasharray={`${Math.max(len - 2, 0)} ${ic}`}
              strokeDashoffset={-offset} />
          )
          offset += len
          return el
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="num text-[32px] font-extrabold leading-none" style={{ fontSize: size * 0.16 }}>
          {Math.abs(remaining).toLocaleString('en-IN')}
        </span>
        <span className="mt-1 text-xs font-semibold text-muted">
          {remaining >= 0 ? 'kcal left' : 'kcal over'}
        </span>
        <span className="num mt-1 text-[11px] text-muted">{Math.round(consumed)} / {goal}</span>
      </div>
      <span className="sr-only">{Math.round(consumed)} of {goal} kcal eaten, {remaining} remaining</span>
    </div>
  )
}
