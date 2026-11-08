import { useEffect, useState } from 'react'
import { Check, Dumbbell, Flame, Moon } from 'lucide-react'
import { get, localDate, post } from '../api/client'
import { EmptyState, ErrorNote, Panel, PageHeader, ProgressBar, Spinner } from '../components/ui'
import { shortDate, weekday } from '../utils/format'
import useApi from '../utils/useApi'

export default function WorkoutTracker() {
  const today = localDate()
  const { data, error, loading, reload } = useApi(() => get('/recommendations/workouts', { date: today }), [today])
  const history = useApi(() => get('/workout-log/history', { days: 30, date: today }), [today])
  const [done, setDone] = useState(new Set())
  const [chosen, setChosen] = useState(null)
  const [saving, setSaving] = useState(null)
  const [saveError, setSaveError] = useState('')

  useEffect(() => { if (data) setDone(new Set(data.today.completed_exercise_ids)) }, [data])

  if (loading && !data) return <Spinner />
  if (error) return <ErrorNote message={error} onRetry={reload} />

  const session = chosen ? data.sessions.find((s) => s.day_number === chosen) : data.today.session
  const total = session?.exercises.length || 0
  const completed = session ? session.exercises.filter((e) => done.has(e.exercise_id)).length : 0

  const toggle = async (ex) => {
    const next = !done.has(ex.exercise_id)
    setSaving(ex.exercise_id)
    setSaveError('')
    try {
      const res = await post('/workout-log', {
        exercise_id: ex.exercise_id, completed: next, sets_completed: next ? ex.sets : 0,
        day_number: session.day_number, log_date: today,
      })
      setDone(new Set(res.completed_exercise_ids))
      history.reload({ quiet: true })
    } catch (e) { setSaveError(e.message) } finally { setSaving(null) }
  }

  // Current streak of days with at least one completed exercise (rest days in the plan don't break it)
  const doneDates = new Set((history.data || []).map((h) => h.date))
  if (completed > 0) doneDates.add(today)

  return (
    <>
      <PageHeader title="Workout tracker" subtitle="Tick off each exercise as you finish it. Your progress is saved straight away." />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {!session ? (
            <Panel>
              <EmptyState icon={Moon} title="Rest day">
                No workout is planned for today. Recovery is part of training. If you feel like moving, choose a session below.
              </EmptyState>
              <div className="flex flex-wrap justify-center gap-2 pb-4">
                {data.sessions.map((s) => (
                  <button key={s.day_number} className="btn-secondary" onClick={() => setChosen(s.day_number)}>
                    Day {s.day_number}: {s.title.split(' (')[0]}
                  </button>
                ))}
              </div>
            </Panel>
          ) : (
            <Panel title={`${chosen ? 'Extra session' : 'Today'}: ${session.title}`}
              action={<span className="num text-sm text-muted">{completed} / {total} done</span>}>
              <ProgressBar value={completed} goal={total} height="h-2.5" />
              {completed === total && total > 0 && (
                <p className="mt-3 rounded-lg bg-brand-50 px-3 py-2 text-sm font-semibold text-brand-800">Session complete. Well done. Remember to stretch and drink water.</p>
              )}
              <ErrorNote message={saveError} />
              <ul className="mt-4 divide-y divide-line">
                {session.exercises.map((e) => {
                  const isDone = done.has(e.exercise_id)
                  return (
                    <li key={e.exercise_id} className="flex items-start gap-3 py-3">
                      <button onClick={() => toggle(e)} disabled={saving === e.exercise_id} aria-pressed={isDone}
                        aria-label={`${isDone ? 'Mark not done' : 'Mark done'}: ${e.name}`}
                        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border-2 transition-colors ${
                          isDone ? 'border-brand-600 bg-brand-600 text-white' : 'border-line bg-white hover:border-brand-400'}`}>
                        {isDone && <Check size={16} strokeWidth={3} />}
                      </button>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                          <p className={`font-bold ${isDone ? 'text-muted line-through' : ''}`}>{e.name}</p>
                          <p className="num text-sm font-semibold">{e.sets} × {e.reps} <span className="font-normal text-muted">rest {e.rest_seconds}s</span></p>
                        </div>
                        <p className="text-xs text-muted">Targets {e.target_muscle.toLowerCase()}, {e.difficulty} level</p>
                        {!isDone && <p className="mt-1 text-sm text-muted">{e.instructions}</p>}
                      </div>
                    </li>
                  )
                })}
              </ul>
              {chosen && <button className="btn-ghost mt-2" onClick={() => setChosen(null)}>Back to today</button>}
            </Panel>
          )}
        </div>

        <div className="space-y-4">
          <Panel title="Last 14 days">
            <div className="grid grid-cols-7 gap-1.5">
              {Array.from({ length: 14 }, (_, i) => {
                const d = new Date(today + 'T00:00:00')
                d.setDate(d.getDate() - (13 - i))
                const iso = localDate(d)
                const has = doneDates.has(iso)
                return (
                  <div key={iso} title={`${shortDate(iso)}${has ? ': workout done' : ''}`}
                    className={`flex aspect-square flex-col items-center justify-center rounded-md text-[10px] font-semibold ${
                      has ? 'bg-brand-600 text-white' : 'bg-black/[0.05] text-muted'}`}>
                    {weekday(iso).slice(0, 2)}
                  </div>
                )
              })}
            </div>
            <p className="mt-3 flex items-center gap-2 text-sm">
              <Flame size={16} className="text-carbs" aria-hidden />
              <span><b className="num">{[...doneDates].filter((d) => d > localDate(new Date(Date.now() - 7 * 864e5))).length}</b> workout days in the last 7 days</span>
            </p>
          </Panel>

          <Panel title="Recent workouts" bodyClass="px-5 py-2">
            {history.loading && !history.data ? <Spinner /> : (history.data || []).length === 0 ? (
              <p className="py-4 text-sm text-muted">Completed workouts will appear here.</p>
            ) : (
              <ul className="divide-y divide-line">
                {history.data.slice(0, 8).map((h) => (
                  <li key={h.date} className="flex items-center gap-3 py-2.5">
                    <Dumbbell size={16} className="shrink-0 text-brand-600" aria-hidden />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold">{weekday(h.date)}, {shortDate(h.date)}</p>
                      <p className="truncate text-xs text-muted">{h.exercises.map((e) => e.name).join(', ')}</p>
                    </div>
                    <span className="num text-xs text-muted">{h.exercises.length} ex.</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>
    </>
  )
}
