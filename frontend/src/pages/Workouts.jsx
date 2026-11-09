import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, Info, LayoutGrid, RefreshCw } from 'lucide-react'
import { get, localDate, put } from '../api/client'
import SplitPicker, { SPLITS } from '../components/SplitPicker'
import { ErrorNote, PageHeader, Spinner } from '../components/ui'
import { CATEGORY_LABELS, GOALS, LEVELS } from '../utils/format'
import useApi from '../utils/useApi'

const WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DIFF_STYLE = {
  beginner: 'bg-brand-50 text-brand-700',
  intermediate: 'bg-amber-50 text-amber-800',
  advanced: 'bg-red-50 text-red-700',
}

export function ExerciseTable({ exercises }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr className="border-b border-line text-left text-muted">
            <th className="py-2 pr-3 font-medium">Exercise</th>
            <th className="py-2 pr-3 font-medium">Target muscle</th>
            <th className="py-2 pr-3 text-right font-medium">Sets</th>
            <th className="py-2 pr-3 text-right font-medium">Reps</th>
            <th className="py-2 pr-3 text-right font-medium">Rest</th>
            <th className="py-2 font-medium">Difficulty</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {exercises.map((e) => (
            <tr key={e.exercise_id} className="align-top">
              <td className="py-2.5 pr-3">
                <p className="font-semibold">{e.name}</p>
                <p className="text-xs text-muted">{CATEGORY_LABELS[e.category]}, {e.equipment}</p>
              </td>
              <td className="py-2.5 pr-3 text-muted">{e.target_muscle}</td>
              <td className="num py-2.5 pr-3 text-right">{e.sets}</td>
              <td className="num py-2.5 pr-3 text-right">{e.reps}</td>
              <td className="num py-2.5 pr-3 text-right">{e.rest_seconds}s</td>
              <td className="py-2.5"><span className={`chip ${DIFF_STYLE[e.difficulty]}`}>{LEVELS[e.difficulty]}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Workouts() {
  const today = localDate()
  const { data, error, loading, reload, setData } = useApi(
    () => get('/recommendations/workouts', { date: today }), [today])
  const [openDay, setOpenDay] = useState(null)
  const [rebuilding, setRebuilding] = useState(false)
  const [toast, setToast] = useState('')
  const [picking, setPicking] = useState(false)
  const [savingSplit, setSavingSplit] = useState(false)
  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(''), 3500); return () => clearTimeout(t) } }, [toast])

  const rebuild = async () => {
    setRebuilding(true)
    try {
      const fresh = await get('/recommendations/workouts', { date: today, regenerate: true })
      setData(fresh)
      setOpenDay(null)
      setToast('Plan rebuilt with a fresh set of exercises.')
    } catch (e) {
      setToast(`Could not rebuild the plan: ${e.message}`)
    } finally {
      setRebuilding(false)
    }
  }

  const applySplit = async (body) => {
    setSavingSplit(true)
    try {
      const fresh = await put(`/recommendations/workouts/split?date=${today}`, body)
      setData(fresh)
      setOpenDay(null)
      setPicking(false)
      setToast(fresh.split === 'auto' ? 'Your plan is back on the recommended split.'
        : `Your plan now uses the ${SPLITS[fresh.split].label} split.`.replace(' split split', ' split'))
    } catch (e) {
      setToast(`Could not change the split: ${e.message}`)
    } finally {
      setSavingSplit(false)
    }
  }

  if (loading && !data) return <Spinner label="Building your plan…" />
  if (error) return <ErrorNote message={error} onRetry={reload} />

  const sessionsByDay = Object.fromEntries(data.sessions.map((s) => [s.weekday, s]))
  const todayIdx = (new Date(today + 'T00:00:00').getDay() + 6) % 7
  const expanded = openDay ?? data.today.session?.weekday ?? data.sessions[0]?.weekday

  return (
    <>
      {toast && <div className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white shadow-lg" role="status">{toast}</div>}
      <PageHeader title="Your workout plan"
        subtitle={`${data.days_per_week} sessions a week for ${GOALS[data.goal].toLowerCase()}, at ${LEVELS[data.level].toLowerCase()} level. Split: ${SPLITS[data.split || 'auto'].label}.`}
        actions={<>
          <button className="btn-secondary" onClick={() => setPicking((v) => !v)} aria-expanded={picking}>
            <LayoutGrid size={15} aria-hidden /> Change split
          </button>
          <button className="btn-secondary" onClick={rebuild} disabled={rebuilding}>
            <RefreshCw size={15} className={rebuilding ? 'animate-spin' : ''} aria-hidden /> {rebuilding ? 'Rebuilding…' : 'Rebuild plan'}
          </button>
          <Link to="/workout-tracker" className="btn-primary">Track today's workout</Link>
        </>} />

      {picking && (
        <div className="mb-5">
          <SplitPicker current={data.split} currentDays={data.days_per_week} currentCustom={data.custom_split}
            saving={savingSplit} onApply={applySplit} onCancel={() => setPicking(false)} />
        </div>
      )}

      {/* Week strip */}
      <div className="grid grid-cols-7 gap-1.5 sm:gap-2" role="list" aria-label="Weekly schedule">
        {WEEK.map((day, i) => {
          const s = sessionsByDay[i]
          const isToday = i === todayIdx
          return (
            <button key={day} role="listitem" disabled={!s} onClick={() => setOpenDay(i)}
              className={`rounded-lg border p-2 text-left transition-colors sm:p-3 ${
                s && expanded === i ? 'border-brand-600 bg-brand-600 text-white'
                  : s ? 'border-line bg-white hover:border-brand-200' : 'border-dashed border-line bg-transparent text-muted'}`}>
              <p className={`text-xs font-semibold ${isToday && !(s && expanded === i) ? 'text-brand-700' : ''}`}>
                {day.slice(0, 3)}{isToday ? ' (today)' : ''}
              </p>
              <p className="mt-1 hidden text-sm font-bold leading-tight sm:block">{s ? s.title.split(' (')[0] : 'Rest'}</p>
              <p className="mt-1 text-xs sm:hidden">{s ? `Day ${s.day_number}` : 'Rest'}</p>
            </button>
          )
        })}
      </div>

      <div className="mt-5 space-y-3">
        {data.sessions.map((s) => {
          const open = expanded === s.weekday
          return (
            <section key={s.day_number} className="panel">
              <button className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left" aria-expanded={open}
                onClick={() => setOpenDay(open ? -1 : s.weekday)}>
                <div>
                  <p className="text-xs font-semibold text-muted">Day {s.day_number}, {s.weekday_name}</p>
                  <h2 className="text-[17px] font-extrabold">{s.title}</h2>
                </div>
                <div className="flex items-center gap-3">
                  <span className="num hidden text-sm text-muted sm:inline">{s.exercises.length} exercises, about {s.estimated_minutes} min</span>
                  <ChevronDown size={18} className={`transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
                </div>
              </button>
              {open && <div className="border-t border-line px-5 pb-4 pt-2"><ExerciseTable exercises={s.exercises} /></div>}
            </section>
          )
        })}
      </div>

      <div className="mt-6 flex items-start gap-3 rounded-panel border border-line bg-white p-5 text-sm leading-relaxed">
        <Info size={18} className="mt-0.5 shrink-0 text-brand-600" aria-hidden />
        <div>
          <p className="font-bold">How this plan was built</p>
          <p className="mt-1 text-muted">
            <b className="text-ink">Rules</b> lay out the weekly split you chose (or, on "Recommended", pick one from your number of days, for example
            4 days gives upper and lower body sessions) and set sets, reps and rest from your goal and level. <b className="text-ink">Machine learning</b> then ranks exercises by cosine similarity
            between your profile and each exercise's features (difficulty, equipment, movement type, goal), and uses Maximal Marginal
            Relevance so a session doesn't repeat the same muscle. Warm up for 5 minutes before each session and stop any exercise that hurts.
          </p>
        </div>
      </div>
    </>
  )
}
