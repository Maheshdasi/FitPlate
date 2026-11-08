import { useState } from 'react'
import { Check, ChevronDown, Clock, Plus, RefreshCw, Sparkles } from 'lucide-react'
import { get, localDate, post } from '../api/client'
import { Disclaimer, ErrorNote, MacroRow, PageHeader, Spinner } from '../components/ui'
import { DIETS, MEAL_LABELS, MEAL_TYPES } from '../utils/format'
import useApi from '../utils/useApi'

function MealCard({ slot, data, onReplace, onLog, busy }) {
  const [open, setOpen] = useState(false)
  const meal = data.recommended
  const logged = data.status === 'logged'

  return (
    <article className="panel flex flex-col">
      <header className="flex items-center justify-between border-b border-line px-5 py-3.5">
        <h2 className="text-[15px] font-bold">{MEAL_LABELS[slot]}</h2>
        <span className="num text-xs text-muted">
          Target {data.target.calories} kcal, {data.target.protein} g protein
          {data.target.already_eaten && ' (already eaten today)'}
        </span>
      </header>

      {!meal ? (
        <p className="p-5 text-sm text-muted">No meal matches your diet and allergy settings for this slot.</p>
      ) : (
        <div className="flex flex-1 flex-col p-5">
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-lg font-extrabold leading-snug">{meal.name}</h3>
            <span className="chip shrink-0 bg-brand-50 text-brand-700" title="How well this meal fits your targets and preferences">
              {meal.match_score}% match
            </span>
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
            <span>{DIETS[meal.diet_type]}</span>
            <span className="flex items-center gap-1"><Clock size={12} aria-hidden />{meal.prep_time_min} min</span>
            {meal.portion !== 1 && <span className="font-semibold text-ink">{meal.portion}× portion</span>}
          </div>

          <div className="mt-3 grid grid-cols-4 gap-2 rounded-lg bg-canvas p-3 text-center">
            {[['Calories', meal.calories, 'kcal', 'text-ink'], ['Protein', meal.protein, 'g', 'text-protein'],
              ['Carbs', meal.carbs, 'g', 'text-[#A87412]'], ['Fat', meal.fat, 'g', 'text-fat']].map(([n, v, u, c]) => (
              <div key={n}>
                <p className="text-[11px] text-muted">{n}</p>
                <p className={`num font-extrabold ${c}`}>{Math.round(v)}<span className="text-xs font-semibold"> {u}</span></p>
              </div>
            ))}
          </div>

          <ul className="mt-3 flex flex-wrap gap-1.5">
            {meal.reasons.map((r) => (
              <li key={r} className="chip bg-black/[0.04] font-medium text-muted"><Sparkles size={12} className="text-brand-600" aria-hidden />{r}</li>
            ))}
          </ul>

          <div className="mt-4">
            <p className="text-sm font-semibold">Ingredients{meal.portion !== 1 ? ` (for 1 portion, scale by ${meal.portion})` : ''}</p>
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-muted">
              {meal.ingredients.map((i) => <li key={i}>{i}</li>)}
            </ul>
          </div>

          <button onClick={() => setOpen(!open)} aria-expanded={open}
            className="mt-3 flex items-center gap-1 self-start text-sm font-semibold text-brand-700 hover:underline">
            How to prepare <ChevronDown size={16} className={`transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
          </button>
          {open && <p className="mt-1.5 text-sm leading-relaxed">{meal.instructions}</p>}

          {data.alternatives.length > 0 && (
            <div className="mt-4 border-t border-line pt-3">
              <p className="text-xs font-semibold text-muted">Other good options</p>
              <ul className="mt-1.5 space-y-1">
                {data.alternatives.map((a) => (
                  <li key={a.id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate">{a.name}</span>
                    <span className="num shrink-0 text-xs text-muted">{a.calories} kcal, {a.protein} g P</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-auto flex gap-2 pt-5">
            <button className="btn-secondary flex-1" onClick={() => onReplace(slot)} disabled={busy}>
              <RefreshCw size={15} className={busy === `replace-${slot}` ? 'animate-spin' : ''} aria-hidden /> Show another
            </button>
            <button className="btn-primary flex-1" onClick={() => onLog(slot)} disabled={busy || logged}>
              {logged ? <><Check size={16} aria-hidden /> Added</> : <><Plus size={16} aria-hidden /> Add to food log</>}
            </button>
          </div>
        </div>
      )}
    </article>
  )
}

export default function Meals() {
  const today = localDate()
  const { data, error, loading, reload } = useApi(() => get('/recommendations/meals', { date: today }), [today])
  const [busy, setBusy] = useState('')
  const [actionError, setActionError] = useState('')

  const replace = async (slot) => {
    setBusy(`replace-${slot}`)
    setActionError('')
    try {
      await post('/recommendations/meals/replace', { meal_type: slot, rec_date: today })
      await reload({ quiet: true })
    } catch (e) { setActionError(e.message) } finally { setBusy('') }
  }

  const log = async (slot) => {
    setBusy(`log-${slot}`)
    setActionError('')
    try {
      await post('/recommendations/meals/log', { meal_type: slot, rec_date: today })
      await reload({ quiet: true })
    } catch (e) { setActionError(e.message) } finally { setBusy('') }
  }

  if (loading && !data) return <Spinner label="Finding meals for you…" />
  if (error) return <ErrorNote message={error} onRetry={reload} />

  const left = data.targets.daily_calories - data.consumed.calories

  return (
    <>
      <PageHeader title="Meal plan"
        subtitle={`Suggestions for today based on your goal, diet type and allergies. You have ${Math.max(Math.round(left), 0)} kcal left today, so portions are adjusted to fit.`}
        actions={<span className="chip bg-white text-muted ring-1 ring-line"><Sparkles size={13} className="text-brand-600" aria-hidden /> Machine-learning recommendations</span>} />
      <ErrorNote message={actionError} />
      <div className="mt-2 grid gap-4 md:grid-cols-2">
        {MEAL_TYPES.map((slot) => (
          <MealCard key={slot} slot={slot} data={data.slots[slot]} onReplace={replace} onLog={log} busy={busy} />
        ))}
      </div>
      <div className="mt-6 grid items-start gap-4 lg:grid-cols-2">
        <div className="panel p-5 text-sm leading-relaxed">
          <p className="font-bold">How meals are chosen</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-muted">
            <li><b className="text-ink">Rules:</b> meals that don't match your diet type or contain your allergens are removed.</li>
            <li><b className="text-ink">Targets:</b> the calories and protein left today are split across the meals you haven't eaten yet.</li>
            <li><b className="text-ink">Machine learning:</b> each meal is scored by cosine similarity of its macros to your target, closeness
              to the calorie target, and TF-IDF similarity of its ingredients to foods you like and log often.</li>
            <li><b className="text-ink">Portion:</b> the serving is scaled between 0.75× and 1.5× to land near your target.</li>
          </ol>
        </div>
        <Disclaimer>Meal suggestions are general guidance for healthy adults, not a medical diet plan. If you have a medical
          condition, follow the advice of your doctor or dietitian. Always check ingredients if you have a severe allergy.</Disclaimer>
      </div>
    </>
  )
}
