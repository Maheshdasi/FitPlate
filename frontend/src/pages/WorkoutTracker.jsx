import { useCallback, useEffect, useRef, useState } from 'react'
import { Check, ChevronDown, Dumbbell, Flame, Minus, Moon, Play, Plus, RotateCcw, Square, Timer, TrendingUp, Trophy } from 'lucide-react'
import { get, localDate, post } from '../api/client'
import { EmptyState, ErrorNote, Panel, PageHeader, ProgressBar, Spinner } from '../components/ui'
import { shortDate, weekday } from '../utils/format'
import useApi from '../utils/useApi'

const blankSet = () => ({ weight_kg: null, reps: null, seconds: null, done: false })
const fmtClock = (s) => `${Math.floor(s / 60)}:${String(Math.max(0, s % 60)).padStart(2, '0')}`
const store = {
  get: (k) => { try { return localStorage.getItem(k) } catch { return null } },
  set: (k, v) => { try { localStorage.setItem(k, v) } catch { /* private mode */ } },
}

/** How one set reads in the "Previous" column and in summaries. */
function describe(kind, s) {
  if (!s) return ''
  if (kind === 'cardio') return `${Math.round((s.seconds || 0) / 60)} min`
  if (kind === 'timed') return `${s.seconds || 0} s`
  if (kind === 'reps') return `${s.weight_kg ? `+${s.weight_kg} kg × ` : ''}${s.reps || 0} reps`
  return `${s.weight_kg ?? 0} kg × ${s.reps || 0}`
}

/** Placeholder for set i: what was done in set i last time, otherwise the progression target. */
function placeholder(kind, info, i) {
  const prev = info?.previous?.sets?.[i] || info?.previous?.sets?.at(-1)
  const sug = info?.suggestion || {}
  if (kind === 'cardio') return { minutes: sug.minutes ?? (prev ? Math.round(prev.seconds / 60) : null) }
  if (kind === 'timed') return { seconds: sug.seconds ?? prev?.seconds ?? null }
  if (kind === 'reps') return { reps: sug.reps ?? prev?.reps ?? null }
  // Weighted: the target weight leads (that's the progression), reps follow last time or the target
  return { weight_kg: sug.weight_kg ?? prev?.weight_kg ?? null, reps: sug.reps ?? prev?.reps ?? null }
}

function beep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const o = ctx.createOscillator(); const g = ctx.createGain()
    o.connect(g); g.connect(ctx.destination); o.frequency.value = 880; g.gain.value = 0.08
    o.start(); o.stop(ctx.currentTime + 0.35)
    navigator.vibrate?.([200, 100, 200])
  } catch { /* sound is optional */ }
}

function NumInput({ value, placeholder: ph, onChange, onBlur, label, step = 1, disabled }) {
  return (
    <input type="number" inputMode="decimal" min="0" step={step} aria-label={label} disabled={disabled}
      className="input num !h-9 !px-2 text-center disabled:opacity-60" value={value ?? ''} placeholder={ph ?? ''}
      onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))} onBlur={onBlur} />
  )
}

function SetTable({ ex, kind, info, sets, onChange, onBlur, onToggleSet, onAdd, onRemove, saving }) {
  const cols = kind === 'weighted' ? 'grid-cols-[2.25rem_minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)_2.25rem]'
    : 'grid-cols-[2.25rem_minmax(0,1.3fr)_minmax(0,1.6fr)_2.25rem]'
  const records = new Set(info?.records || [])
  return (
    <div className="mt-2.5">
      <div className={`grid ${cols} items-center gap-2 px-1 text-[11px] font-semibold uppercase tracking-wide text-muted`}>
        <span>Set</span><span>Previous</span>
        {kind === 'weighted' && <><span className="text-center">kg</span><span className="text-center">Reps</span></>}
        {kind === 'reps' && <span className="text-center">Reps</span>}
        {kind === 'timed' && <span className="text-center">Seconds</span>}
        {kind === 'cardio' && <span className="text-center">Minutes</span>}
        <span className="sr-only">Done</span>
      </div>
      <div className="mt-1 space-y-1">
        {sets.map((s, i) => {
          const ph = placeholder(kind, info, i)
          const prev = info?.previous?.sets?.[i]
          return (
            <div key={i} className={`grid ${cols} items-center gap-2 rounded-lg px-1 py-1 ${s.done ? 'bg-brand-50' : ''}`}>
              <span className="num flex items-center gap-1 text-sm font-bold text-muted">
                {i + 1}
                {records.has(i) && <Trophy size={13} className="text-carbs" aria-label="Personal record" />}
              </span>
              <span className="num truncate text-xs text-muted" title={prev ? describe(kind, prev) : 'No previous set'}>
                {prev ? describe(kind, prev) : '-'}
              </span>
              {kind === 'weighted' && <>
                <NumInput label={`Set ${i + 1} kg`} step={0.5} value={s.weight_kg} placeholder={ph.weight_kg}
                  onChange={(v) => onChange(i, { weight_kg: v })} onBlur={onBlur} />
                <NumInput label={`Set ${i + 1} reps`} value={s.reps} placeholder={ph.reps}
                  onChange={(v) => onChange(i, { reps: v })} onBlur={onBlur} />
              </>}
              {kind === 'reps' && <NumInput label={`Set ${i + 1} reps`} value={s.reps} placeholder={ph.reps}
                onChange={(v) => onChange(i, { reps: v })} onBlur={onBlur} />}
              {kind === 'timed' && <NumInput label={`Set ${i + 1} seconds`} step={5} value={s.seconds} placeholder={ph.seconds}
                onChange={(v) => onChange(i, { seconds: v })} onBlur={onBlur} />}
              {kind === 'cardio' && <NumInput label={`Set ${i + 1} minutes`} value={s.seconds == null ? null : Math.round(s.seconds / 60)}
                placeholder={ph.minutes} onChange={(v) => onChange(i, { seconds: v == null ? null : v * 60 })} onBlur={onBlur} />}
              <button onClick={() => onToggleSet(i)} disabled={saving} aria-pressed={s.done} aria-label={`Set ${i + 1} ${s.done ? 'done' : 'not done'}`}
                className={`flex h-8 w-8 items-center justify-center rounded-lg border-2 transition-colors ${
                  s.done ? 'border-brand-600 bg-brand-600 text-white' : 'border-line bg-white hover:border-brand-400'}`}>
                {s.done && <Check size={15} strokeWidth={3} />}
              </button>
            </div>
          )
        })}
      </div>
      <div className="mt-1.5 flex gap-1">
        <button className="btn-ghost !px-2 !py-1 text-xs" onClick={onAdd} disabled={sets.length >= 10}><Plus size={13} aria-hidden /> Add set</button>
        {sets.length > 1 && <button className="btn-ghost !px-2 !py-1 text-xs" onClick={onRemove}><Minus size={13} aria-hidden /> Remove set</button>}
        <span className="sr-only">{ex.sets} sets planned</span>
      </div>
    </div>
  )
}

export default function WorkoutTracker() {
  const today = localDate()
  const { data, error, loading, reload } = useApi(() => get('/recommendations/workouts', { date: today }), [today])
  const history = useApi(() => get('/workout-log/history', { days: 30, date: today }), [today])
  const day = useApi(() => get('/workout-log/day', { date: today }), [today])
  const [done, setDone] = useState(new Set())
  const [sets, setSets] = useState({})        // exercise_id -> editable sets
  const [open, setOpen] = useState({})        // exercise_id -> table shown
  const [chosen, setChosen] = useState(null)
  const [saving, setSaving] = useState(null)
  const [saveError, setSaveError] = useState('')
  const [rest, setRest] = useState(null)      // { end, total, name }
  const [now, setNow] = useState(Date.now())
  const setsRef = useRef(sets)
  setsRef.current = sets

  useEffect(() => { if (data) setDone(new Set(data.today.completed_exercise_ids)) }, [data])

  const session = data ? (chosen ? data.sessions.find((s) => s.day_number === chosen) : data.today.session) : null

  // Fill the editable sets once per exercise: today's saved sets, otherwise empty rows for the planned sets
  useEffect(() => {
    if (!session || !day.data) return
    setSets((cur) => {
      const next = { ...cur }
      for (const ex of session.exercises) {
        if (next[ex.exercise_id]) continue
        const saved = day.data.logs[ex.exercise_id]?.sets
        next[ex.exercise_id] = saved?.length ? saved.map((s) => ({ ...blankSet(), ...s }))
          : Array.from({ length: ex.sets }, blankSet)
      }
      return next
    })
  }, [session, day.data])

  // One clock for the rest timer and the session duration
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])
  const restLeft = rest ? Math.round((rest.end - now) / 1000) : 0
  useEffect(() => {
    if (rest && restLeft <= 0) { beep(); setRest(null) }
  }, [rest, restLeft])

  // Session clock { start, end } in ms, kept per day in the browser. It starts with the first ticked set (or
  // the Start button), can be stopped, resumed or reset, and stops by itself when the session is complete.
  const clockKey = `fitplate-workout-clock-${today}`
  const [clock, setClockState] = useState(() => {
    try { return JSON.parse(store.get(clockKey)) || {} } catch { return {} }
  })
  const setClock = (c) => { setClockState(c); store.set(clockKey, JSON.stringify(c)) }
  const allDone = !!session && session.exercises.length > 0 && session.exercises.every((e) => done.has(e.exercise_id))
  useEffect(() => {
    if (allDone && clock.start && !clock.end) {
      const c = { ...clock, end: Date.now() }
      setClockState(c); store.set(clockKey, JSON.stringify(c))
    }
  }, [allDone, clock, clockKey])

  const save = useCallback(async (ex, list, completed) => {
    setSaving(ex.exercise_id)
    setSaveError('')
    try {
      const res = await post('/workout-log', {
        exercise_id: ex.exercise_id, completed, sets: list,
        day_number: session.day_number, log_date: today,
      })
      setDone(new Set(res.completed_exercise_ids))
      day.reload({ quiet: true })
      history.reload({ quiet: true })
    } catch (e) { setSaveError(e.message) } finally { setSaving(null) }
  }, [session, today, day, history])

  if ((loading && !data) || (day.loading && !day.data)) return <Spinner />
  if (error) return <ErrorNote message={error} onRetry={reload} />
  if (day.error) return <ErrorNote message={day.error} onRetry={day.reload} />

  const info = (id) => day.data.exercises[id]
  const total = session?.exercises.length || 0
  const completed = session ? session.exercises.filter((e) => done.has(e.exercise_id)).length : 0
  const summary = day.data.summary

  const fillFromPlaceholder = (kind, inf, s, i) => {
    const ph = placeholder(kind, inf, i)
    if (kind === 'cardio') return { ...s, seconds: s.seconds ?? (ph.minutes != null ? ph.minutes * 60 : null) }
    if (kind === 'timed') return { ...s, seconds: s.seconds ?? ph.seconds }
    if (kind === 'reps') return { ...s, reps: s.reps ?? ph.reps }
    return { ...s, weight_kg: s.weight_kg ?? ph.weight_kg, reps: s.reps ?? ph.reps }
  }

  const markStarted = () => { if (!clock.start) setClock({ start: Date.now() }) }
  const clockButtons = !clock.start ? [['Start', Play, () => setClock({ start: Date.now() })]]
    : !clock.end ? [['Stop', Square, () => setClock({ ...clock, end: Date.now() })]]
      : [['Resume', Play, () => setClock({ start: clock.start + (Date.now() - clock.end) })],
        ['Reset', RotateCcw, () => setClock({})]]

  const toggleSet = (ex, i) => {
    const inf = info(ex.exercise_id)
    const kind = inf?.kind || 'weighted'
    const list = [...(setsRef.current[ex.exercise_id] || [])]
    const turningOn = !list[i].done
    list[i] = turningOn ? { ...fillFromPlaceholder(kind, inf, list[i], i), done: true } : { ...list[i], done: false }
    setSets((cur) => ({ ...cur, [ex.exercise_id]: list }))
    const allDone = list.every((s) => s.done)
    save(ex, list, allDone)
    if (turningOn) {
      markStarted()
      const last = list.filter((s) => s.done).length === list.length
      if (!last && ex.rest_seconds) setRest({ end: Date.now() + ex.rest_seconds * 1000, total: ex.rest_seconds, name: ex.name })
      else setRest(null)
    }
  }

  const toggleExercise = (ex) => {
    const inf = info(ex.exercise_id)
    const kind = inf?.kind || 'weighted'
    const isDone = done.has(ex.exercise_id)
    const list = (setsRef.current[ex.exercise_id] || []).map((s, i) =>
      isDone ? { ...s, done: false } : { ...fillFromPlaceholder(kind, inf, s, i), done: true })
    setSets((cur) => ({ ...cur, [ex.exercise_id]: list }))
    if (!isDone) markStarted()
    save(ex, list, !isDone)
  }

  const editSet = (ex, i, change) => setSets((cur) => ({
    ...cur, [ex.exercise_id]: cur[ex.exercise_id].map((s, j) => (j === i ? { ...s, ...change } : s)),
  }))
  const saveIfLogged = (ex) => {
    const list = setsRef.current[ex.exercise_id] || []
    if (list.some((s) => s.done)) save(ex, list, list.every((s) => s.done))
  }
  const resize = (ex, delta) => {
    const list = [...(setsRef.current[ex.exercise_id] || [])]
    if (delta > 0) list.push(blankSet()); else list.pop()
    setSets((cur) => ({ ...cur, [ex.exercise_id]: list }))
    if (list.some((s) => s.done)) save(ex, list, list.every((s) => s.done))
  }

  // Current streak of days with at least one completed exercise (rest days in the plan don't break it)
  const doneDates = new Set((history.data || []).map((h) => h.date))
  if (completed > 0) doneDates.add(today)
  const elapsed = clock.start ? Math.floor(((clock.end || now) - clock.start) / 1000) : 0

  return (
    <>
      <PageHeader title="Workout tracker" subtitle="Log each set with its weight and reps. Your previous numbers and next targets are filled in, and everything saves straight away." />

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
              <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {[
                  ['Duration', fmtClock(elapsed), Timer, clockButtons],
                  ['Volume', `${Math.round(summary.volume_kg).toLocaleString()} kg`, Dumbbell],
                  ['Sets', summary.sets_done, Check],
                  ['Records', summary.records, Trophy],
                ].map(([label, value, Icon, buttons]) => (
                  <div key={label} className="rounded-lg bg-canvas px-3 py-2">
                    <p className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-muted">
                      <Icon size={12} aria-hidden />{label}
                      {label === 'Duration' && clock.start && !clock.end && <span className="ml-auto h-1.5 w-1.5 animate-pulse rounded-full bg-brand-600" title="Running" />}
                      {label === 'Duration' && clock.end && <span className="ml-auto normal-case tracking-normal">stopped</span>}
                    </p>
                    <div className="flex items-center justify-between gap-1">
                      <p className="num text-[17px] font-extrabold">{value}</p>
                      {buttons && (
                        <div className="flex gap-1">
                          {buttons.map(([text, BtnIcon, onClick]) => (
                            <button key={text} onClick={onClick} aria-label={`${text} workout timer`} title={`${text} timer`}
                              className="flex h-7 w-7 items-center justify-center rounded-md border border-line bg-white text-ink hover:border-brand-200 hover:bg-brand-50">
                              <BtnIcon size={13} fill={text === 'Reset' ? 'none' : 'currentColor'} aria-hidden />
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {completed === total && total > 0 && (
                <p className="mt-3 rounded-lg bg-brand-50 px-3 py-2 text-sm font-semibold text-brand-800">
                  Session complete{summary.records ? ` with ${summary.records} personal record${summary.records > 1 ? 's' : ''}` : ''}. Well done. Remember to stretch and drink water.
                </p>
              )}
              <ErrorNote message={saveError} />
              <ul className="mt-4 divide-y divide-line">
                {session.exercises.map((e) => {
                  const isDone = done.has(e.exercise_id)
                  const inf = info(e.exercise_id)
                  const kind = inf?.kind || 'weighted'
                  const list = sets[e.exercise_id] || []
                  const shown = open[e.exercise_id] ?? !isDone
                  const doneSets = list.filter((s) => s.done)
                  return (
                    <li key={e.exercise_id} className="flex items-start gap-3 py-3">
                      <button onClick={() => toggleExercise(e)} disabled={saving === e.exercise_id} aria-pressed={isDone}
                        aria-label={`${isDone ? 'Mark not done' : 'Mark done'}: ${e.name}`}
                        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border-2 transition-colors ${
                          isDone ? 'border-brand-600 bg-brand-600 text-white' : 'border-line bg-white hover:border-brand-400'}`}>
                        {isDone && <Check size={16} strokeWidth={3} />}
                      </button>
                      <div className="min-w-0 flex-1">
                        <button className="flex w-full flex-wrap items-baseline justify-between gap-x-3 text-left"
                          onClick={() => setOpen((o) => ({ ...o, [e.exercise_id]: !shown }))} aria-expanded={shown}>
                          <p className={`flex items-center gap-1.5 font-bold ${isDone ? 'text-muted line-through' : ''}`}>
                            {e.name}
                            {inf?.records?.length > 0 && <Trophy size={14} className="text-carbs" aria-label="Personal record today" />}
                          </p>
                          <p className="num flex items-center gap-1 text-sm font-semibold">
                            {e.sets} × {e.reps} <span className="font-normal text-muted">rest {e.rest_seconds}s</span>
                            <ChevronDown size={15} className={`text-muted transition-transform ${shown ? 'rotate-180' : ''}`} aria-hidden />
                          </p>
                        </button>
                        <p className="text-xs text-muted">
                          Targets {e.target_muscle.toLowerCase()}, {e.difficulty} level
                          {inf?.best?.set && <>. Best: {describe(kind, inf.best.set)} on {shortDate(inf.best.set.date)}</>}
                        </p>
                        {!shown && doneSets.length > 0 && (
                          <p className="num mt-1 text-xs text-muted">{doneSets.map((s) => describe(kind, s)).join(', ')}</p>
                        )}
                        {shown && (
                          <>
                            {inf?.suggestion?.text && (
                              <p className="mt-1.5 flex items-start gap-1.5 text-sm font-medium text-brand-700">
                                <TrendingUp size={15} className="mt-0.5 shrink-0" aria-hidden />{inf.suggestion.text}
                              </p>
                            )}
                            {doneSets.length === 0 && <p className="mt-1 text-sm text-muted">{e.instructions}</p>}
                            <SetTable ex={e} kind={kind} info={inf} sets={list} saving={saving === e.exercise_id}
                              onChange={(i, ch) => editSet(e, i, ch)} onBlur={() => saveIfLogged(e)}
                              onToggleSet={(i) => toggleSet(e, i)} onAdd={() => resize(e, 1)} onRemove={() => resize(e, -1)} />
                          </>
                        )}
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
                    <span className="num text-right text-xs text-muted">
                      {h.sets} sets{h.volume_kg > 0 && <><br />{Math.round(h.volume_kg).toLocaleString()} kg</>}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>

      {rest && restLeft > 0 && (
        <div className="fixed bottom-5 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-full bg-ink py-2 pl-4 pr-2 text-white shadow-lg" role="timer" aria-live="polite">
          <Timer size={16} aria-hidden />
          <span className="text-sm">Rest</span>
          <span className="num w-12 text-lg font-extrabold">{fmtClock(restLeft)}</span>
          <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/20">
            <div className="h-full bg-brand-400" style={{ width: `${(restLeft / rest.total) * 100}%` }} />
          </div>
          <button className="rounded-full px-2 py-1 text-xs font-semibold hover:bg-white/10" onClick={() => setRest((r) => ({ ...r, end: r.end - 15000 }))}>-15s</button>
          <button className="rounded-full px-2 py-1 text-xs font-semibold hover:bg-white/10" onClick={() => setRest((r) => ({ ...r, end: r.end + 15000, total: r.total + 15 }))}>+15s</button>
          <button className="rounded-full bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25" onClick={() => setRest(null)}>Skip</button>
        </div>
      )}
    </>
  )
}
