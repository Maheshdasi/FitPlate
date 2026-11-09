import { useState } from 'react'
import { Check, Dumbbell, Plus, Trash2, X } from 'lucide-react'
import { CATEGORY_LABELS } from '../utils/format'

export const SPLITS = {
  auto: { label: 'Recommended for you', desc: 'FitPlate picks the split from your days and level.', days: 'any number of days' },
  full_body: { label: 'Full body', desc: 'Every session trains the whole body. Great for beginners.', days: '2 to 3 days' },
  upper_lower: { label: 'Upper / lower', desc: 'Alternate upper body and lower body days.', days: '4 days' },
  push_pull_legs: { label: 'Push pull legs', desc: 'Push (chest, shoulders, triceps), pull (back, biceps), then legs.', days: '3 or 6 days' },
  bro_split: { label: 'Bro split', desc: 'One muscle group per day: chest, back, shoulders, legs, arms.', days: '5 days' },
  arnold: { label: 'Arnold split', desc: 'Chest and back, shoulders and arms, then legs.', days: '3 or 6 days' },
  custom: { label: 'Custom split', desc: 'Build your own days and pick the muscles for each one.', days: '2 to 6 days' },
}

const GROUPS = Object.keys(CATEGORY_LABELS)
const STARTER_DAYS = [
  { name: 'Chest and triceps', groups: ['chest', 'arms'] },
  { name: 'Back and biceps', groups: ['back', 'arms'] },
  { name: 'Legs and core', groups: ['legs', 'core'] },
]

/** Lets the user pick a named split or build a custom one. Calls onApply({ workout_split, ... }). */
export default function SplitPicker({ current, currentDays, currentCustom, onApply, onCancel, saving }) {
  const [split, setSplit] = useState(current || 'auto')
  const [days, setDays] = useState(currentDays || 3)
  const [custom, setCustom] = useState(currentCustom?.length ? currentCustom : STARTER_DAYS)
  const [error, setError] = useState('')

  const updateDay = (i, change) => setCustom((list) => list.map((d, j) => (j === i ? { ...d, ...change } : d)))
  const toggleGroup = (i, g) => {
    const groups = custom[i].groups
    if (groups.includes(g)) updateDay(i, { groups: groups.filter((x) => x !== g) })
    else if (groups.length < 4) updateDay(i, { groups: [...groups, g] })
  }

  const apply = () => {
    if (split === 'custom') {
      const empty = custom.findIndex((d) => d.groups.length === 0)
      if (empty >= 0) return setError(`Pick at least one muscle group for day ${empty + 1}.`)
      if (custom.some((d) => d.name && !/^[A-Za-z0-9 ,.&()'/+-]+$/.test(d.name)))
        return setError('Day names can only contain letters, numbers and simple punctuation.')
      setError('')
      return onApply({ workout_split: 'custom', custom_split: custom.map((d) => ({ name: d.name.trim(), groups: d.groups })) })
    }
    setError('')
    onApply({ workout_split: split, workout_days_per_week: days })
  }

  return (
    <section className="panel p-5" aria-label="Choose your training split">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[17px] font-extrabold">Choose your training split</h2>
          <p className="mt-0.5 text-sm text-muted">Pick a classic split or build your own. Exercises still match your level and equipment.</p>
        </div>
        <button className="btn-ghost !p-2" onClick={onCancel} aria-label="Close"><X size={18} aria-hidden /></button>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3" role="radiogroup" aria-label="Training split">
        {Object.entries(SPLITS).map(([key, s]) => {
          const active = split === key
          return (
            <button key={key} role="radio" aria-checked={active} onClick={() => setSplit(key)}
              className={`rounded-lg border p-3 text-left transition-colors ${
                active ? 'border-brand-600 bg-brand-50 ring-2 ring-brand-100' : 'border-line bg-white hover:border-brand-200'}`}>
              <div className="flex items-center justify-between gap-2">
                <p className="font-bold">{s.label}</p>
                {active && <Check size={16} className="text-brand-600" aria-hidden />}
              </div>
              <p className="mt-1 text-xs leading-relaxed text-muted">{s.desc}</p>
              <p className="mt-1.5 text-xs font-semibold text-brand-700">Best with {s.days}</p>
            </button>
          )
        })}
      </div>

      {split !== 'custom' && (
        <div className="mt-5 max-w-sm">
          <label htmlFor="split-days" className="text-sm font-semibold">Workout days per week: {days}</label>
          <input id="split-days" type="range" min="2" max="6" step="1" value={days}
            onChange={(e) => setDays(Number(e.target.value))} className="mt-2 w-full accent-brand-600" />
        </div>
      )}

      {split === 'custom' && (
        <div className="mt-5 space-y-3">
          {custom.map((d, i) => (
            <div key={i} className="rounded-lg border border-line p-3">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">{i + 1}</span>
                <input className="input !py-1.5" value={d.name} maxLength={40} aria-label={`Day ${i + 1} name`}
                  placeholder={`Day ${i + 1} name (optional), e.g. Chest and triceps`}
                  onChange={(e) => updateDay(i, { name: e.target.value })} />
                <button className="btn-ghost !p-2" disabled={custom.length <= 2} aria-label={`Remove day ${i + 1}`}
                  title={custom.length <= 2 ? 'A split needs at least 2 days' : 'Remove this day'}
                  onClick={() => setCustom((list) => list.filter((_, j) => j !== i))}>
                  <Trash2 size={16} aria-hidden />
                </button>
              </div>
              <div className="mt-2.5 flex flex-wrap gap-1.5" role="group" aria-label={`Muscle groups for day ${i + 1}`}>
                {GROUPS.map((g) => {
                  const on = d.groups.includes(g)
                  return (
                    <button key={g} aria-pressed={on} onClick={() => toggleGroup(i, g)}
                      disabled={!on && d.groups.length >= 4}
                      className={`chip border transition-colors ${on ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-line bg-white text-ink hover:border-brand-200 disabled:opacity-40'}`}>
                      {on && <Check size={12} aria-hidden />}{CATEGORY_LABELS[g]}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
          <div className="flex flex-wrap items-center gap-3">
            <button className="btn-secondary" disabled={custom.length >= 6}
              onClick={() => setCustom((list) => [...list, { name: '', groups: [] }])}>
              <Plus size={15} aria-hidden /> Add a day
            </button>
            <p className="text-xs text-muted">{custom.length} of 6 days. Up to 4 muscle groups per day.</p>
          </div>
        </div>
      )}

      {error && <p className="mt-3 text-sm font-semibold text-red-600" role="alert">{error}</p>}

      <div className="mt-5 flex flex-wrap gap-2">
        <button className="btn-primary" onClick={apply} disabled={saving}>
          <Dumbbell size={15} aria-hidden /> {saving ? 'Building your plan…' : 'Apply split'}
        </button>
        <button className="btn-secondary" onClick={onCancel} disabled={saving}>Cancel</button>
      </div>
    </section>
  )
}
