import { AlertCircle, Info, Loader2 } from 'lucide-react'
import { pct } from '../utils/format'

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-extrabold sm:text-[28px]">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-[15px] text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Panel({ title, action, children, className = '', bodyClass = 'p-5' }) {
  return (
    <section className={`panel ${className}`}>
      {title && (
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
          <h2 className="text-[15px] font-bold">{title}</h2>
          {action}
        </div>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  )
}

export function Stat({ label, value, unit, sub, icon: Icon, tone = 'text-brand-600' }) {
  return (
    <div className="panel p-4">
      <div className="flex items-center gap-2 text-sm font-medium text-muted">
        {Icon && <Icon size={16} className={tone} aria-hidden />}
        {label}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="num text-2xl font-extrabold">{value}</span>
        {unit && <span className="text-sm font-semibold text-muted">{unit}</span>}
      </div>
      {sub && <div className="mt-1 text-xs text-muted">{sub}</div>}
    </div>
  )
}

export function ProgressBar({ value, goal, color = 'bg-brand-500', height = 'h-2', label, showNumbers, unit = 'g' }) {
  const p = pct(value, goal)
  const over = goal > 0 && value > goal * 1.05
  return (
    <div>
      {(label || showNumbers) && (
        <div className="mb-1.5 flex items-baseline justify-between text-sm">
          <span className="font-semibold">{label}</span>
          {showNumbers && (
            <span className="num text-muted">
              <span className={`font-bold ${over ? 'text-red-600' : 'text-ink'}`}>{Math.round(value)}</span>
              {' '}/ {Math.round(goal)} {unit}
            </span>
          )}
        </div>
      )}
      <div className={`${height} w-full overflow-hidden rounded-full bg-black/[0.06]`}
           role="progressbar" aria-valuenow={Math.round(value)} aria-valuemax={Math.round(goal)} aria-label={label}>
        <div className={`${height} rounded-full ${over ? 'bg-red-500' : color} transition-[width] duration-500`}
             style={{ width: `${p}%` }} />
      </div>
    </div>
  )
}

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-muted" role="status">
      <Loader2 className="animate-spin" size={18} aria-hidden /> {label}
    </div>
  )
}

export function ErrorNote({ message, onRetry }) {
  if (!message) return null
  return (
    <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-800" role="alert">
      <AlertCircle size={16} className="mt-0.5 shrink-0" aria-hidden />
      <span className="flex-1">{message}</span>
      {onRetry && <button className="font-semibold underline" onClick={onRetry}>Try again</button>}
    </div>
  )
}

export function Disclaimer({ children }) {
  return (
    <p className="flex items-start gap-2 rounded-lg bg-black/[0.035] px-3 py-2.5 text-xs leading-relaxed text-muted">
      <Info size={14} className="mt-0.5 shrink-0" aria-hidden />
      <span>{children || 'Calorie and nutrition values are estimates, not medical advice. For medical conditions, consult a doctor or registered dietitian.'}</span>
    </p>
  )
}

export function Field({ label, error, hint, children, htmlFor }) {
  return (
    <div>
      {label && <label className="label" htmlFor={htmlFor}>{label}</label>}
      {children}
      {hint && !error && <p className="mt-1 text-xs text-muted">{hint}</p>}
      {error && <p className="mt-1 text-xs font-medium text-red-600">{error}</p>}
    </div>
  )
}

export function Segmented({ options, value, onChange, ariaLabel }) {
  return (
    <div className="inline-flex rounded-lg border border-line bg-white p-1" role="tablist" aria-label={ariaLabel}>
      {options.map((o) => (
        <button key={o.value} role="tab" aria-selected={value === o.value} onClick={() => onChange(o.value)}
          className={`rounded-md px-3 py-1.5 text-sm font-semibold transition-colors ${
            value === o.value ? 'bg-brand-600 text-white' : 'text-muted hover:text-ink'}`}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center">
      {Icon && <div className="mb-3 rounded-full bg-brand-50 p-3 text-brand-600"><Icon size={22} aria-hidden /></div>}
      <p className="font-bold">{title}</p>
      {children && <p className="mt-1 max-w-sm text-sm text-muted">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function MacroLegend({ protein, carbs, fat }) {
  const items = [
    ['Protein', protein, 'bg-protein'], ['Carbs', carbs, 'bg-carbs'], ['Fat', fat, 'bg-fat'],
  ]
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
      {items.map(([name, v, c]) => (
        <span key={name} className="flex items-center gap-1.5">
          <span className={`h-2.5 w-2.5 rounded-sm ${c}`} aria-hidden />
          <span className="text-muted">{name}</span>
          <span className="num font-bold">{Math.round(v)} g</span>
        </span>
      ))}
    </div>
  )
}

/** Small macro summary row used on food and meal cards. */
export function MacroRow({ calories, protein, carbs, fat, compact }) {
  return (
    <div className={`num flex flex-wrap items-center gap-x-3 gap-y-1 ${compact ? 'text-xs' : 'text-sm'} text-muted`}>
      <span><b className="text-ink">{Math.round(calories)}</b> kcal</span>
      <span className="text-protein"><b>{Math.round(protein * 10) / 10}</b> g P</span>
      <span className="text-[#A87412]"><b>{Math.round(carbs * 10) / 10}</b> g C</span>
      <span className="text-fat"><b>{Math.round(fat * 10) / 10}</b> g F</span>
    </div>
  )
}

export const chartTooltipStyle = {
  contentStyle: { borderRadius: 10, border: '1px solid #DDE3DC', fontSize: 13, fontFamily: 'Manrope' },
  labelStyle: { fontWeight: 700, color: '#16211C' },
}
export const axisProps = { tick: { fontSize: 12, fill: '#5E6B64' }, tickLine: false, axisLine: false }
