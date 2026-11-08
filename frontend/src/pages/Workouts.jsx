import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, Info, RefreshCw } from 'lucide-react'
import { get, localDate } from '../api/client'
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
  const [regen, setRegen] = useState(0)
  const { data, error, loading, reload } = useApi(
    () => get('/recommendations/workouts', { date: today, regenerate: regen > 0 || undefined }), [today, regen])
  const [openDay, setOpenDay] = useState(null)

  if (loading && !data) return <Spinner label="Building your plan…" />
  if (error) return <ErrorNote message={error} onRetry={reload} />

  const sessionsByDay = Object.fromEntries(data.sessions.map((s) => [s.weekday, s]))
  const todayIdx = (new Date(today + 'T00:00:00').getDay() + 6) % 7
  const expanded = openDay ?? data.today.session?.weekday ?? data.sessions[0]?.weekday

  return (
    <>
      <PageHeader title="Your workout plan"
        subtitle={`${data.days_per_week} sessions a week for ${GOALS[data.goal].toLowerCase()}, at ${LEVELS[data.level].toLowerCase()} level. Change your goal, level or days in settings and the plan updates automatically.`}
        actions={<>
          <button className="btn-secondary" onClick={() => setRegen((n) => n + 1)} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} aria-hidden /> Rebuild plan
          </button>
          <Link to="/workout-tracker" className="btn-primary">Track today's workout</Link>
        </>} />

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
            <b className="text-ink">Rules</b> choose the weekly split from your number of days (for example, 4 days gives upper and lower body sessions)
            and set sets, reps and rest from your goal and level. <b className="text-ink">Machine learning</b> then ranks exercises by cosine similarity
            between your profile and each exercise's features (difficulty, equipment, movement type, goal), and uses Maximal Marginal
            Relevance so a session doesn't repeat the same muscle. Warm up for 5 minutes before each session and stop any exercise that hurts.
          </p>
        </div>
      </div>
    </>
  )
}
