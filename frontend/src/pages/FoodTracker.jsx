import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ChevronLeft, ChevronRight, Plus, Search, Trash2, UtensilsCrossed, X } from 'lucide-react'
import { del, get, localDate, post } from '../api/client'
import {
  axisProps, chartTooltipStyle, Disclaimer, EmptyState, ErrorNote, MacroRow, Panel, PageHeader, ProgressBar, Spinner,
} from '../components/ui'
import { addDays, longDate, MEAL_LABELS, MEAL_TYPES } from '../utils/format'
import useApi from '../utils/useApi'

function defaultMealType() {
  const h = new Date().getHours()
  return h < 11 ? 'breakfast' : h < 15 ? 'lunch' : h < 18 ? 'snacks' : 'dinner'
}

const FALLBACK_UNITS = (food) => [
  { key: 'serving', label: `serving: ${food.serving_desc}`, grams: food.serving_g, step: 0.25 },
  { key: 'g', label: 'g', grams: 1, step: 5 },
]

/** A sensible starting amount for a unit: about one serving's worth. */
function defaultAmount(unit, food) {
  if (unit.key === 'serving') return '1'
  const n = food.serving_g / unit.grams
  if (unit.key === 'g' || unit.key === 'ml') return String(n > 100 ? Math.round(n / 25) * 25 : Math.round(n / 5) * 5 || 5)
  if (unit.key === 'oz') return String(Math.round(n * 2) / 2 || 0.5)
  return String(Math.max(1, Math.round(n * 4) / 4))
}

function AddFoodForm({ food, date, onAdded, onCancel }) {
  const units = food.units?.length ? food.units : FALLBACK_UNITS(food)
  const [unitKey, setUnitKey] = useState(units[0].key)
  const unit = units.find((u) => u.key === unitKey) || units[0]
  const [amount, setAmount] = useState('1')
  const [mealType, setMealType] = useState(defaultMealType())
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const a = Number(amount)
  const q = a * unit.grams / food.serving_g  // servings
  const valid = a > 0 && q > 0 && q <= 20

  const changeUnit = (key) => {
    const next = units.find((u) => u.key === key)
    setUnitKey(key)
    setAmount(defaultAmount(next, food))
    setError('')
  }

  const add = async (e) => {
    e.preventDefault()
    if (!valid) return setError(a > 0 ? 'That is more than 20 servings. Please enter a smaller amount.' : 'Enter an amount above 0.')
    setBusy(true)
    setError('')
    try {
      await post('/food-log', { food_item_id: food.id, amount: a, unit: unit.key, meal_type: mealType, log_date: date })
      onAdded(`${food.name} added to ${MEAL_LABELS[mealType].toLowerCase()}.`)
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  const grams = Math.round(a * unit.grams)
  return (
    <form onSubmit={add} className="rounded-lg border border-brand-200 bg-brand-50/60 p-4" noValidate>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-bold">{food.name}</p>
          <p className="text-sm text-muted">1 serving = {food.serving_desc} ({food.serving_g} g)</p>
        </div>
        <button type="button" onClick={onCancel} className="rounded p-1 text-muted hover:bg-black/5" aria-label="Cancel"><X size={18} /></button>
      </div>
      <div className="mt-3 grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-3">
        <div>
          <label className="label" htmlFor="qty">Amount</label>
          <input id="qty" type="number" inputMode="decimal" min="0" step={unit.step} className={`input ${!valid ? 'input-error' : ''}`}
            value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="unit">Unit</label>
          <select id="unit" className="input" value={unit.key} onChange={(e) => changeUnit(e.target.value)}>
            {units.map((u) => <option key={u.key} value={u.key}>{u.label}</option>)}
          </select>
        </div>
      </div>
      <div className="mt-3">
        <label className="label" htmlFor="meal">Meal</label>
        <select id="meal" className="input" value={mealType} onChange={(e) => setMealType(e.target.value)}>
          {MEAL_TYPES.map((m) => <option key={m} value={m}>{MEAL_LABELS[m]}</option>)}
        </select>
      </div>
      {valid && (
        <div className="mt-3">
          {unit.key !== 'serving' && (
            <p className="num mb-1 text-xs text-muted">
              {unit.key === 'g' ? '' : `About ${grams} g, which is `}{Math.round(q * 100) / 100} {q === 1 ? 'serving' : 'servings'}
            </p>
          )}
          <MacroRow calories={food.calories * q} protein={food.protein * q} carbs={food.carbs * q} fat={food.fat * q} />
        </div>
      )}
      <ErrorNote message={error} />
      <button className="btn-primary mt-3 w-full" disabled={busy}><Plus size={16} aria-hidden />{busy ? 'Adding…' : 'Add to log'}</button>
    </form>
  )
}

export default function FoodTracker() {
  const today = localDate()
  const [date, setDate] = useState(today)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [selected, setSelected] = useState(null)
  const [toast, setToast] = useState('')
  const { data: log, error, loading, reload } = useApi(() => get('/food-log/today', { date }), [date])
  const { data: categories } = useApi(() => get('/foods/categories'), [])

  useEffect(() => {
    const timer = setTimeout(async () => {
      setSearching(true)
      try { setResults(await get('/foods', { search: query.trim(), category, limit: 40 })) } catch { setResults([]) }
      setSearching(false)
    }, 250)
    return () => clearTimeout(timer)
  }, [query, category])

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(''), 3000); return () => clearTimeout(t) } }, [toast])

  const remove = async (id) => {
    await del(`/food-log/${id}`)
    reload({ quiet: true })
  }

  const byMealChart = useMemo(() => log ? MEAL_TYPES.map((m) => ({ meal: MEAL_LABELS[m], calories: Math.round(log.by_meal[m].calories) })) : [], [log])

  return (
    <>
      <PageHeader title="Food tracker" subtitle="Search for a food, choose how much you had, and add it to a meal."
        actions={
          <div className="flex items-center gap-1 rounded-lg border border-line bg-white p-1">
            <button className="rounded-md p-1.5 hover:bg-black/5" onClick={() => setDate(addDays(date, -1))} aria-label="Previous day"><ChevronLeft size={18} /></button>
            <span className="min-w-[150px] px-2 text-center text-sm font-semibold">{date === today ? 'Today' : longDate(date)}</span>
            <button className="rounded-md p-1.5 hover:bg-black/5 disabled:opacity-30" disabled={date >= today}
              onClick={() => setDate(addDays(date, 1))} aria-label="Next day"><ChevronRight size={18} /></button>
          </div>
        } />

      {toast && <div className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white shadow-lg" role="status">{toast}</div>}

      <div className="grid gap-4 lg:grid-cols-5">
        {/* Search + add */}
        <Panel title="Add food" className="lg:col-span-2" bodyClass="p-4">
          <div className="relative">
            <Search size={17} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
            <input className="input pl-9" placeholder="Search foods, e.g. dal, paneer, banana" value={query}
              onChange={(e) => setQuery(e.target.value)} aria-label="Search foods" maxLength={60} />
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {['', ...(categories || [])].map((c) => (
              <button key={c || 'all'} onClick={() => setCategory(c)}
                className={`chip border ${category === c ? 'border-brand-600 bg-brand-600 text-white' : 'border-line bg-white text-muted hover:text-ink'}`}>
                {c || 'All'}
              </button>
            ))}
          </div>
          {selected && <div className="mt-4"><AddFoodForm key={selected.id} food={selected} date={date}
            onCancel={() => setSelected(null)}
            onAdded={(msg) => { setSelected(null); setToast(msg); reload({ quiet: true }) }} /></div>}
          <ul className="mt-3 max-h-[440px] lg:max-h-[720px] divide-y divide-line overflow-y-auto" aria-busy={searching}>
            {results.map((f) => (
              <li key={f.id}>
                <button onClick={() => setSelected(f)}
                  className={`flex w-full items-center gap-3 px-1 py-2.5 text-left hover:bg-brand-50/60 ${selected?.id === f.id ? 'bg-brand-50' : ''}`}>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{f.name}</p>
                    <p className="text-xs text-muted">{f.serving_desc}, {Math.round(f.calories)} kcal, {f.protein} g protein</p>
                  </div>
                  <Plus size={18} className="shrink-0 text-brand-600" aria-hidden />
                </button>
              </li>
            ))}
            {!searching && results.length === 0 && <li className="py-6 text-center text-sm text-muted">No foods match “{query}”.</li>}
          </ul>
        </Panel>

        {/* Daily summary + log */}
        <div className="space-y-4 lg:col-span-3">
          {loading && !log ? <Spinner /> : error ? <ErrorNote message={error} onRetry={reload} /> : (
            <>
              <Panel title="Daily totals">
                <div className="overflow-x-auto">
                  <table className="num w-full text-sm">
                    <thead><tr className="text-left text-muted">
                      <th className="pb-2 font-medium" />
                      <th className="pb-2 text-right font-medium">Calories</th><th className="pb-2 text-right font-medium">Protein</th>
                      <th className="pb-2 text-right font-medium">Carbs</th><th className="pb-2 text-right font-medium">Fat</th>
                    </tr></thead>
                    <tbody>
                      {[['Daily goal', log.goal], ['Consumed', log.consumed], ['Remaining', log.remaining]].map(([label, v], i) => (
                        <tr key={label} className={i === 2 ? 'border-t border-line font-bold' : ''}>
                          <td className="py-1.5 font-semibold">{label}</td>
                          <td className={`py-1.5 text-right ${v.calories < 0 ? 'text-red-600' : ''}`}>{Math.round(v.calories)} kcal</td>
                          <td className={`py-1.5 text-right ${v.protein < 0 ? 'text-red-600' : ''}`}>{Math.round(v.protein)} g</td>
                          <td className="py-1.5 text-right">{Math.round(v.carbs)} g</td>
                          <td className="py-1.5 text-right">{Math.round(v.fat)} g</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <ProgressBar label="Calories" value={log.consumed.calories} goal={log.goal.calories} unit="kcal" showNumbers />
                  <ProgressBar label="Protein" value={log.consumed.protein} goal={log.goal.protein} color="bg-protein" showNumbers />
                  <ProgressBar label="Carbs" value={log.consumed.carbs} goal={log.goal.carbs} color="bg-carbs" showNumbers />
                  <ProgressBar label="Fat" value={log.consumed.fat} goal={log.goal.fat} color="bg-fat" showNumbers />
                </div>
                {log.consumed.calories > 0 && (
                  <div className="mt-5 h-36">
                    <ResponsiveContainer>
                      <BarChart data={byMealChart} layout="vertical" margin={{ left: 8, right: 16 }}>
                        <XAxis type="number" hide />
                        <YAxis type="category" dataKey="meal" {...axisProps} width={72} />
                        <Tooltip {...chartTooltipStyle} formatter={(v) => [`${v} kcal`, 'Calories']} />
                        <Bar dataKey="calories" radius={[0, 5, 5, 0]} maxBarSize={18}>
                          {byMealChart.map((d) => <Cell key={d.meal} fill="#2F7A55" />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Panel>

              {MEAL_TYPES.map((m) => {
                const entries = log.entries[m]
                return (
                  <Panel key={m} title={MEAL_LABELS[m]} bodyClass="px-5 py-2"
                    action={<span className="num text-sm font-semibold text-muted">{Math.round(log.by_meal[m].calories)} kcal</span>}>
                    {entries.length === 0 ? (
                      <p className="py-2 text-sm text-muted">Nothing logged for {m} yet.</p>
                    ) : (
                      <ul className="divide-y divide-line">
                        {entries.map((e) => (
                          <li key={e.id} className="flex items-center gap-3 py-2.5">
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-sm font-semibold">{e.name}</p>
                              <p className="text-xs text-muted">{e.amount_text || `${e.quantity} × ${e.serving_desc}`}</p>
                              <div className="mt-0.5"><MacroRow {...e} compact /></div>
                            </div>
                            <button onClick={() => remove(e.id)} className="rounded-lg p-2 text-muted hover:bg-red-50 hover:text-red-600"
                              aria-label={`Remove ${e.name}`}><Trash2 size={16} /></button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Panel>
                )
              })}
              {Object.values(log.entries).every((e) => e.length === 0) && (
                <EmptyState icon={UtensilsCrossed} title={`No food logged ${date === today ? 'today' : 'on this day'}`}>
                  Search for a food on the left, or add a suggested meal from the meal plan.
                </EmptyState>
              )}
              <Disclaimer>Nutrition values are average estimates. Household units (katori, cup, tbsp) are converted to grams using typical sizes, so actual values vary with recipe and portion size.</Disclaimer>
            </>
          )}
        </div>
      </div>
    </>
  )
}
