import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ArrowRight, Calculator as CalcIcon } from 'lucide-react'
import { get, post } from '../api/client'
import { Disclaimer, ErrorNote, Field, Panel, PageHeader, Spinner } from '../components/ui'
import { ACTIVITY, GOALS } from '../utils/format'
import useApi from '../utils/useApi'

function ResultBlock({ r }) {
  const macros = [
    ['Protein', r.protein_g, r.protein_g * 4, 'bg-protein'],
    ['Carbohydrates', r.carbs_g, r.carbs_g * 4, 'bg-carbs'],
    ['Fat', r.fat_g, r.fat_g * 9, 'bg-fat'],
  ]
  const total = macros.reduce((s, m) => s + m[2], 0)
  return (
    <>
      <p className="text-lg">Your estimated daily calorie requirement is</p>
      <p className="num mt-1 text-5xl font-extrabold text-brand-700">{r.daily_calories.toLocaleString('en-IN')} <span className="text-2xl">kcal</span></p>

      <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
        {[['Current weight', `${r.current_weight} kg`], ['Target weight', `${r.target_weight} kg`],
          ['BMI', `${r.bmi}`, r.bmi_category], ['BMR', `${r.bmr} kcal`], ['TDEE', `${r.tdee} kcal`],
          ['Water', `${(r.water_ml / 1000).toFixed(2)} L`]].map(([k, v, s]) => (
          <div key={k}>
            <dt className="text-sm text-muted">{k}</dt>
            <dd className="num text-lg font-bold">{v} {s && <span className="text-sm font-semibold text-muted">({s})</span>}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-6">
        <p className="mb-2 text-sm font-semibold">Daily macronutrients</p>
        <div className="flex h-3 overflow-hidden rounded-full" aria-hidden>
          {macros.map(([n, , kc, c]) => <div key={n} className={c} style={{ width: `${kc / total * 100}%` }} />)}
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3">
          {macros.map(([n, g, kc, c]) => (
            <div key={n} className="rounded-lg border border-line p-3">
              <div className="flex items-center gap-1.5 text-sm text-muted"><span className={`h-2.5 w-2.5 rounded-sm ${c}`} />{n}</div>
              <p className="num mt-1 text-xl font-extrabold">{g} g</p>
              <p className="num text-xs text-muted">{Math.round(kc / total * 100)}% of calories</p>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

export default function CalculatorPage() {
  const location = useLocation()
  const { data, error, loading, reload } = useApi(() => get('/nutrition/calories'), [])
  const [form, setForm] = useState(null)
  const [whatIf, setWhatIf] = useState(null)
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)

  if (loading) return <Spinner />
  if (error) return <ErrorNote message={error} onRetry={reload} />

  const f = form || { ...data.inputs, target_weight_kg: data.target_weight }
  const set = (k) => (e) => setForm({ ...f, [k]: e.target.value })

  const tryValues = async (ev) => {
    ev.preventDefault()
    setFormError('')
    const age = Number(f.age), h = Number(f.height_cm), w = Number(f.weight_kg)
    if (!(age >= 13 && age <= 100)) return setFormError('Age must be between 13 and 100.')
    if (!(h >= 100 && h <= 250)) return setFormError('Height must be between 100 and 250 cm.')
    if (!(w >= 30 && w <= 300)) return setFormError('Weight must be between 30 and 300 kg.')
    setBusy(true)
    try {
      setWhatIf(await post('/nutrition/calculate', {
        age, gender: f.gender, height_cm: h, weight_kg: w, activity_level: f.activity_level,
        fitness_goal: f.fitness_goal, target_weight_kg: Number(f.target_weight_kg) || null,
      }))
    } catch (err) { setFormError(err.message) } finally { setBusy(false) }
  }

  return (
    <>
      <PageHeader title="Calorie & macro calculator"
        subtitle="Your daily targets, calculated from your profile with standard formulas. Every step is shown below." />

      {location.state?.welcome && (
        <div className="mb-4 flex flex-col gap-3 rounded-panel bg-brand-900 p-5 text-white sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-bold">Your profile is ready.</p>
            <p className="text-sm text-white/75">These targets now drive your food tracker, meal plan and insights.</p>
          </div>
          <Link to="/food" className="btn bg-white text-brand-900 hover:bg-brand-50">Start logging food <ArrowRight size={16} aria-hidden /></Link>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-5">
        <Panel className="lg:col-span-3" title="Your targets">
          <ResultBlock r={data} />
          <div className="mt-6"><Disclaimer>{data.disclaimer}</Disclaimer></div>
        </Panel>

        <Panel className="lg:col-span-2" title="How this was calculated" action={<span className="chip bg-black/5 text-muted">Formula-based</span>}>
          <ol className="space-y-3">
            {data.explanation.map((line, i) => (
              <li key={i} className="flex gap-3 text-sm leading-relaxed">
                <span className="num mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">{i + 1}</span>
                <span>{line}</span>
              </li>
            ))}
          </ol>
          <p className="mt-4 text-xs text-muted">BMR uses the Mifflin-St Jeor equation (1990). Activity factors: 1.2, 1.375, 1.55 and 1.725.
            Goal adjustment: −20% for weight loss, +15% for weight gain, +10% for muscle gain.</p>
        </Panel>
      </div>

      <Panel className="mt-4" title="Try different values" action={<span className="text-xs text-muted">Does not change your profile</span>}>
        <form onSubmit={tryValues} noValidate className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Age" htmlFor="c-age"><input id="c-age" type="number" className="input" value={f.age} onChange={set('age')} /></Field>
          <Field label="Gender" htmlFor="c-gender">
            <select id="c-gender" className="input" value={f.gender} onChange={set('gender')}>
              <option value="male">Male</option><option value="female">Female</option><option value="other">Other</option>
            </select></Field>
          <Field label="Height (cm)" htmlFor="c-h"><input id="c-h" type="number" className="input" value={f.height_cm} onChange={set('height_cm')} /></Field>
          <Field label="Weight (kg)" htmlFor="c-w"><input id="c-w" type="number" className="input" value={f.weight_kg} onChange={set('weight_kg')} /></Field>
          <Field label="Activity level" htmlFor="c-a">
            <select id="c-a" className="input" value={f.activity_level} onChange={set('activity_level')}>
              {Object.entries(ACTIVITY).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select></Field>
          <Field label="Goal" htmlFor="c-g">
            <select id="c-g" className="input" value={f.fitness_goal} onChange={set('fitness_goal')}>
              {Object.entries(GOALS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select></Field>
          <Field label="Target weight (kg)" htmlFor="c-t"><input id="c-t" type="number" className="input" value={f.target_weight_kg ?? ''} onChange={set('target_weight_kg')} /></Field>
          <div className="flex items-end"><button className="btn-primary w-full" disabled={busy}><CalcIcon size={16} aria-hidden />{busy ? 'Calculating…' : 'Calculate'}</button></div>
        </form>
        <div className="mt-4"><ErrorNote message={formError} /></div>
        {whatIf && <div className="mt-6 border-t border-line pt-6"><ResultBlock r={whatIf} /></div>}
      </Panel>
    </>
  )
}
