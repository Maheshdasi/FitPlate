import { useState } from 'react'
import { Check } from 'lucide-react'
import {
  ACTIVITY, ACTIVITY_HINT, ALLERGENS, capitalize, DIETS, GOALS, LEVELS, WORKOUT_TYPES,
} from '../utils/format'
import { ErrorNote, Field } from './ui'

export const EMPTY_PROFILE = {
  name: '', age: '', gender: '', height_cm: '', weight_kg: '', target_weight_kg: '',
  activity_level: 'lightly_active', fitness_goal: 'general_fitness', dietary_preference: 'vegetarian',
  allergies: [], food_preferences: '', workout_level: 'beginner', workout_days_per_week: 3,
  preferred_workout_type: 'mixed',
}

const STEPS = [
  { title: 'About you', fields: ['name', 'age', 'gender'] },
  { title: 'Body measurements', fields: ['height_cm', 'weight_kg', 'target_weight_kg'] },
  { title: 'Activity and goal', fields: ['activity_level', 'fitness_goal'] },
  { title: 'Food', fields: ['dietary_preference', 'allergies', 'food_preferences'] },
  { title: 'Training', fields: ['workout_level', 'workout_days_per_week', 'preferred_workout_type'] },
]

export function validateProfile(p, fields) {
  const e = {}
  const has = (f) => !fields || fields.includes(f)
  const num = (v) => (v === '' || v === null ? NaN : Number(v))
  if (has('name') && !/^[A-Za-z][A-Za-z .'-]{1,99}$/.test(String(p.name).trim()))
    e.name = 'Enter your name (letters and spaces only).'
  if (has('age') && !(num(p.age) >= 13 && num(p.age) <= 100 && Number.isInteger(num(p.age))))
    e.age = 'Age must be a whole number between 13 and 100.'
  if (has('gender') && !p.gender) e.gender = 'Select an option.'
  if (has('height_cm') && !(num(p.height_cm) >= 100 && num(p.height_cm) <= 250)) e.height_cm = 'Height must be between 100 and 250 cm.'
  if (has('weight_kg') && !(num(p.weight_kg) >= 30 && num(p.weight_kg) <= 300)) e.weight_kg = 'Weight must be between 30 and 300 kg.'
  if (has('target_weight_kg') && !(num(p.target_weight_kg) >= 30 && num(p.target_weight_kg) <= 300))
    e.target_weight_kg = 'Target weight must be between 30 and 300 kg.'
  if (has('fitness_goal') || has('target_weight_kg')) {
    const diff = num(p.target_weight_kg) - num(p.weight_kg)
    if (p.fitness_goal === 'weight_loss' && diff > 0) e.target_weight_kg = 'For weight loss, your target should be at or below your current weight.'
    if (['weight_gain', 'muscle_gain'].includes(p.fitness_goal) && diff < -2)
      e.target_weight_kg = 'For weight or muscle gain, your target should not be below your current weight.'
  }
  if (has('food_preferences') && String(p.food_preferences || '').length > 500) e.food_preferences = 'Keep this under 500 characters.'
  return e
}

export function toPayload(p) {
  return {
    ...p,
    name: String(p.name).trim(),
    age: Number(p.age), height_cm: Number(p.height_cm), weight_kg: Number(p.weight_kg),
    target_weight_kg: Number(p.target_weight_kg), workout_days_per_week: Number(p.workout_days_per_week),
    food_preferences: p.food_preferences?.trim() || null,
  }
}

function Choice({ options, value, onChange, name, hints, columns = 'sm:grid-cols-2' }) {
  return (
    <div className={`grid gap-2 ${columns}`} role="radiogroup" aria-label={name}>
      {Object.entries(options).map(([key, label]) => {
        const active = value === key
        return (
          <button type="button" key={key} role="radio" aria-checked={active} onClick={() => onChange(key)}
            className={`flex items-start gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors ${
              active ? 'border-brand-500 bg-brand-50' : 'border-line bg-white hover:border-brand-200'}`}>
            <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
              active ? 'border-brand-600 bg-brand-600' : 'border-line'}`}>
              {active && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
            </span>
            <span>
              <span className="block text-sm font-semibold">{label}</span>
              {hints?.[key] && <span className="block text-xs text-muted">{hints[key]}</span>}
            </span>
          </button>
        )
      })}
    </div>
  )
}

function Section({ field, p, set, errors }) {
  const err = errors[field]
  const numberInput = (id, unit, step = '0.1') => (
    <div className="relative">
      <input id={id} type="number" inputMode="decimal" step={step} className={`input pr-12 ${err ? 'input-error' : ''}`}
        value={p[id]} onChange={(e) => set(id, e.target.value)} />
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted">{unit}</span>
    </div>
  )
  switch (field) {
    case 'name':
      return <Field label="Full name" htmlFor="name" error={err}>
        <input id="name" className={`input ${err ? 'input-error' : ''}`} value={p.name} autoComplete="name"
          onChange={(e) => set('name', e.target.value)} /></Field>
    case 'age':
      return <Field label="Age" htmlFor="age" error={err}>{numberInput('age', 'years', '1')}</Field>
    case 'gender':
      return <Field label="Gender" error={err} hint="Used in the BMR formula.">
        <Choice name="Gender" columns="grid-cols-3" options={{ male: 'Male', female: 'Female', other: 'Other' }}
          value={p.gender} onChange={(v) => set('gender', v)} /></Field>
    case 'height_cm':
      return <Field label="Height" htmlFor="height_cm" error={err}>{numberInput('height_cm', 'cm', '0.5')}</Field>
    case 'weight_kg':
      return <Field label="Current weight" htmlFor="weight_kg" error={err}>{numberInput('weight_kg', 'kg')}</Field>
    case 'target_weight_kg':
      return <Field label="Target weight" htmlFor="target_weight_kg" error={err}>{numberInput('target_weight_kg', 'kg')}</Field>
    case 'activity_level':
      return <Field label="How active are you?">
        <Choice name="Activity level" options={ACTIVITY} hints={ACTIVITY_HINT} value={p.activity_level}
          onChange={(v) => set('activity_level', v)} /></Field>
    case 'fitness_goal':
      return <Field label="Main goal" error={err}>
        <Choice name="Fitness goal" options={GOALS} value={p.fitness_goal} onChange={(v) => set('fitness_goal', v)} /></Field>
    case 'dietary_preference':
      return <Field label="Diet type">
        <Choice name="Diet type" options={DIETS} value={p.dietary_preference}
          hints={{ eggetarian: 'Vegetarian plus eggs', vegan: 'No dairy, eggs, meat or fish' }}
          onChange={(v) => set('dietary_preference', v)} /></Field>
    case 'allergies':
      return <Field label="Food allergies" hint="Meals containing these are never recommended.">
        <div className="flex flex-wrap gap-2">
          {ALLERGENS.map((a) => {
            const on = p.allergies.includes(a)
            return (
              <button type="button" key={a} aria-pressed={on}
                onClick={() => set('allergies', on ? p.allergies.filter((x) => x !== a) : [...p.allergies, a])}
                className={`chip border text-sm ${on ? 'border-red-300 bg-red-50 text-red-800' : 'border-line bg-white text-ink hover:border-brand-200'}`}>
                {on && <Check size={13} aria-hidden />} {capitalize(a)}
              </button>
            )
          })}
        </div></Field>
    case 'food_preferences':
      return <Field label="Foods you enjoy (optional)" htmlFor="food_preferences" error={err}
        hint="For example: paneer, dal, oats, South Indian breakfasts. Used to rank meal suggestions.">
        <textarea id="food_preferences" rows={2} className="input" value={p.food_preferences || ''}
          onChange={(e) => set('food_preferences', e.target.value)} /></Field>
    case 'workout_level':
      return <Field label="Workout experience">
        <Choice name="Workout level" columns="grid-cols-1 sm:grid-cols-3" options={LEVELS} value={p.workout_level}
          hints={{ beginner: 'New or returning', intermediate: '6+ months regular', advanced: '2+ years regular' }}
          onChange={(v) => set('workout_level', v)} /></Field>
    case 'workout_days_per_week':
      return <Field label={`Workout days per week: ${p.workout_days_per_week}`} htmlFor="days">
        <input id="days" type="range" min="2" max="6" step="1" value={p.workout_days_per_week}
          onChange={(e) => set('workout_days_per_week', Number(e.target.value))} className="w-full accent-brand-600" />
        <div className="num mt-1 flex justify-between text-xs text-muted">{[2, 3, 4, 5, 6].map((n) => <span key={n}>{n}</span>)}</div>
      </Field>
    case 'preferred_workout_type':
      return <Field label="Where do you train?">
        <Choice name="Workout type" options={WORKOUT_TYPES} value={p.preferred_workout_type}
          onChange={(v) => set('preferred_workout_type', v)} /></Field>
    default:
      return null
  }
}

export default function ProfileForm({ initial, onSubmit, wizard = false, submitLabel = 'Save changes' }) {
  const [p, setP] = useState({ ...EMPTY_PROFILE, ...initial })
  const [errors, setErrors] = useState({})
  const [step, setStep] = useState(0)
  const [busy, setBusy] = useState(false)
  const [serverError, setServerError] = useState('')

  const set = (k, v) => { setP((prev) => ({ ...prev, [k]: v })); setErrors((e) => ({ ...e, [k]: undefined })) }

  const submit = async (ev) => {
    ev?.preventDefault()
    setServerError('')
    const e = validateProfile(p)
    setErrors(e)
    if (Object.keys(e).length) {
      if (wizard) setStep(STEPS.findIndex((s) => s.fields.some((f) => e[f])))
      return
    }
    setBusy(true)
    try { await onSubmit(toPayload(p)) } catch (err) { setServerError(err.message) } finally { setBusy(false) }
  }

  if (!wizard) {
    return (
      <form onSubmit={submit} noValidate className="space-y-8">
        {STEPS.map((s) => (
          <fieldset key={s.title} className="space-y-4">
            <legend className="mb-3 text-[15px] font-bold">{s.title}</legend>
            <div className={s.fields.length === 3 && s.title !== 'Food' && s.title !== 'Training' ? 'grid gap-4 sm:grid-cols-3' : 'space-y-4'}>
              {s.fields.map((f) => <Section key={f} field={f} p={p} set={set} errors={errors} />)}
            </div>
          </fieldset>
        ))}
        <ErrorNote message={serverError} />
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Saving…' : submitLabel}</button>
      </form>
    )
  }

  const current = STEPS[step]
  const next = () => {
    const e = validateProfile(p, current.fields)
    setErrors(e)
    if (Object.keys(e).length === 0) setStep(step + 1)
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); step === STEPS.length - 1 ? submit() : next() }} noValidate>
      <div className="mb-6">
        <div className="mb-2 flex justify-between text-sm">
          <span className="font-semibold">{current.title}</span>
          <span className="num text-muted">Step {step + 1} of {STEPS.length}</span>
        </div>
        <div className="flex gap-1.5" aria-hidden>
          {STEPS.map((s, i) => <div key={s.title} className={`h-1.5 flex-1 rounded-full ${i <= step ? 'bg-brand-600' : 'bg-black/10'}`} />)}
        </div>
      </div>
      <div className="space-y-5">
        {current.fields.map((f) => <Section key={f} field={f} p={p} set={set} errors={errors} />)}
      </div>
      <div className="mt-6"><ErrorNote message={serverError} /></div>
      <div className="mt-6 flex justify-between gap-3">
        <button type="button" className="btn-secondary" onClick={() => setStep(step - 1)} disabled={step === 0}>Back</button>
        <button type="submit" className="btn-primary" disabled={busy}>
          {step === STEPS.length - 1 ? (busy ? 'Saving…' : submitLabel) : 'Continue'}
        </button>
      </div>
    </form>
  )
}
