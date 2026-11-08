import { useMemo, useState } from 'react'
import {
  Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Dumbbell, Scale, TrendingDown, Utensils } from 'lucide-react'
import { get, localDate, post } from '../api/client'
import { axisProps, chartTooltipStyle, ErrorNote, Field, Panel, PageHeader, Segmented, Spinner, Stat } from '../components/ui'
import { shortDate } from '../utils/format'
import useApi from '../utils/useApi'

const RANGES = [{ value: 7, label: '7 days' }, { value: 30, label: '30 days' }, { value: 90, label: '3 months' }, { value: 180, label: '6 months' }]

function WeightForm({ onSaved, today }) {
  const empty = { weight_kg: '', waist_cm: '', chest_cm: '', hips_cm: '', arms_cm: '', log_date: today }
  const [f, setF] = useState(empty)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setOk('')
    const w = Number(f.weight_kg)
    if (!(w >= 30 && w <= 300)) return setError('Enter a weight between 30 and 300 kg.')
    if (f.log_date > today) return setError('Date cannot be in the future.')
    const opt = (v) => (v === '' ? null : Number(v))
    setBusy(true)
    try {
      await post('/progress/weight', { weight_kg: w, waist_cm: opt(f.waist_cm), chest_cm: opt(f.chest_cm),
        hips_cm: opt(f.hips_cm), arms_cm: opt(f.arms_cm), log_date: f.log_date })
      setOk(`Saved ${w} kg for ${shortDate(f.log_date)}.`)
      setF({ ...empty })
      onSaved()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  const num = (k, label, unit) => (
    <Field label={label} htmlFor={k}>
      <div className="relative">
        <input id={k} type="number" step="0.1" inputMode="decimal" className="input pr-10" value={f[k]} onChange={set(k)} />
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted">{unit}</span>
      </div>
    </Field>
  )

  return (
    <form onSubmit={submit} noValidate className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        {num('weight_kg', 'Weight', 'kg')}
        <Field label="Date" htmlFor="log_date"><input id="log_date" type="date" max={today} className="input" value={f.log_date} onChange={set('log_date')} /></Field>
      </div>
      <p className="pt-1 text-xs font-semibold text-muted">Body measurements (optional)</p>
      <div className="grid grid-cols-2 gap-3">
        {num('waist_cm', 'Waist', 'cm')}{num('chest_cm', 'Chest', 'cm')}{num('hips_cm', 'Hips', 'cm')}{num('arms_cm', 'Arms', 'cm')}
      </div>
      <ErrorNote message={error} />
      {ok && <p className="text-sm font-semibold text-brand-700" role="status">{ok}</p>}
      <button className="btn-primary w-full" disabled={busy}>{busy ? 'Saving…' : 'Save entry'}</button>
    </form>
  )
}

/** Group daily rows into weeks for longer ranges so bars stay readable. */
function groupWeekly(daily) {
  const weeks = []
  for (let i = 0; i < daily.length; i += 7) {
    const chunk = daily.slice(i, i + 7)
    weeks.push({
      label: shortDate(chunk[0].date),
      done: chunk.filter((d) => d.workout_done).length,
      planned: chunk.filter((d) => d.workout_planned).length,
    })
  }
  return weeks
}

export default function Progress() {
  const today = localDate()
  const [days, setDays] = useState(30)
  const { data, error, loading, reload } = useApi(() => get('/progress/summary', { days, date: today }), [days, today])

  const charts = useMemo(() => {
    if (!data) return null
    const daily = data.daily.map((d) => ({ ...d, label: shortDate(d.date), calories: d.calories || null, protein: d.protein || null }))
    const weights = data.weights.map((w) => ({ ...w, label: shortDate(w.date) }))
    const p = data.prediction
    if (p.available && weights.length) {
      weights.push({ date: p.prediction_date, label: shortDate(p.prediction_date), predicted: p.predicted_weight })
      weights[weights.length - 2].predicted = weights[weights.length - 2].weight
    }
    const consistency = days <= 7
      ? daily.map((d) => ({ label: d.label, done: d.workout_done ? 1 : 0, planned: d.workout_planned ? 1 : 0 }))
      : groupWeekly(data.daily)
    const measures = data.weights.filter((w) => w.waist || w.chest || w.hips || w.arms)
    return { daily, weights, consistency, measures }
  }, [data, days])

  return (
    <>
      <PageHeader title="Progress" subtitle="Your weight, food and training over time."
        actions={<Segmented options={RANGES} value={days} onChange={setDays} ariaLabel="Time range" />} />

      {loading && !data ? <Spinner /> : error ? <ErrorNote message={error} onRetry={reload} /> : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Weight change" icon={Scale} tone="text-ink"
              value={data.totals.weight_change == null ? '—' : `${data.totals.weight_change > 0 ? '+' : ''}${data.totals.weight_change}`} unit="kg"
              sub={`Over the selected ${RANGES.find((r) => r.value === days).label}`} />
            <Stat label="Average calories" icon={Utensils} value={data.totals.avg_calories.toLocaleString('en-IN')} unit="kcal"
              sub={`Goal ${data.targets.daily_calories} kcal, ${data.totals.days_logged} days logged`} />
            <Stat label="Average protein" icon={Utensils} tone="text-protein" value={Math.round(data.totals.avg_protein)} unit="g"
              sub={`Goal ${data.targets.protein_g} g`} />
            <Stat label="Workout consistency" icon={Dumbbell} value={data.totals.consistency_pct} unit="%"
              sub={`${data.totals.workouts_done} of ${data.totals.workouts_planned} planned sessions`} />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <Panel title="Weight over time" className="lg:col-span-2">
              <div className="h-64">
                {charts.weights.length > 1 ? (
                  <ResponsiveContainer>
                    <LineChart data={charts.weights} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke="#EEF1ED" />
                      <XAxis dataKey="label" {...axisProps} minTickGap={24} />
                      <YAxis {...axisProps} width={48} domain={['dataMin - 1', 'dataMax + 1']} />
                      <Tooltip {...chartTooltipStyle} formatter={(v, n) => [`${v} kg`, n === 'predicted' ? 'Trend forecast' : 'Weight']} />
                      <ReferenceLine y={data.targets.target_weight} stroke="#2F7A55" strokeDasharray="4 4"
                        label={{ value: `Target ${data.targets.target_weight} kg`, position: 'insideBottomRight', fontSize: 11, fill: '#2F7A55' }} />
                      <Line dataKey="weight" stroke="#16211C" strokeWidth={2} dot={days <= 30 ? { r: 2.5 } : false} connectNulls />
                      <Line dataKey="predicted" stroke="#16211C" strokeDasharray="5 5" strokeWidth={1.5} dot={{ r: 3 }} connectNulls />
                    </LineChart>
                  </ResponsiveContainer>
                ) : <p className="py-20 text-center text-sm text-muted">Log your weight at least twice in this range to see a chart.</p>}
              </div>
              {data.prediction.available ? (
                <div className="mt-3 flex items-start gap-2 rounded-lg bg-canvas p-3 text-sm">
                  <TrendingDown size={16} className="mt-0.5 shrink-0 text-brand-600" aria-hidden />
                  <p>
                    Trend: <b className="num">{data.prediction.weekly_change_kg > 0 ? '+' : ''}{data.prediction.weekly_change_kg} kg/week</b>.
                    If it continues, about <b className="num">{data.prediction.predicted_weight} kg</b> by {shortDate(data.prediction.prediction_date)}
                    {data.prediction.target_eta && <>, reaching your target around <b>{shortDate(data.prediction.target_eta)}</b></>}.
                    <span className="text-muted"> Linear regression on your last {data.prediction.points_used} entries, {data.prediction.confidence} confidence. A trend, not a promise.</span>
                  </p>
                </div>
              ) : <p className="mt-3 text-sm text-muted">{data.prediction.reason}</p>}
            </Panel>

            <Panel title="Log weight">
              <WeightForm today={today} onSaved={() => reload({ quiet: true })} />
            </Panel>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Panel title="Calories vs goal">
              <div className="h-60">
                <ResponsiveContainer>
                  <ComposedChart data={charts.daily} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#EEF1ED" />
                    <XAxis dataKey="label" {...axisProps} minTickGap={24} />
                    <YAxis {...axisProps} width={48} />
                    <Tooltip {...chartTooltipStyle} formatter={(v, n) => [`${Math.round(v)} kcal`, n === 'calorie_goal' ? 'Goal' : 'Eaten']} />
                    <Bar dataKey="calories" fill="#2F7A55" radius={[3, 3, 0, 0]} maxBarSize={22} />
                    <Line dataKey="calorie_goal" stroke="#16211C" strokeDasharray="4 4" dot={false} strokeWidth={1.5} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel title="Protein vs goal">
              <div className="h-60">
                <ResponsiveContainer>
                  <ComposedChart data={charts.daily} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#EEF1ED" />
                    <XAxis dataKey="label" {...axisProps} minTickGap={24} />
                    <YAxis {...axisProps} width={48} />
                    <Tooltip {...chartTooltipStyle} formatter={(v, n) => [`${Math.round(v)} g`, n === 'protein_goal' ? 'Goal' : 'Eaten']} />
                    <Area dataKey="protein" stroke="#3567B5" fill="#3567B5" fillOpacity={0.12} strokeWidth={2} connectNulls />
                    <Line dataKey="protein_goal" stroke="#16211C" strokeDasharray="4 4" dot={false} strokeWidth={1.5} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel title={days <= 7 ? 'Workouts by day' : 'Workouts per week'}>
              <div className="h-60">
                <ResponsiveContainer>
                  <BarChart data={charts.consistency} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#EEF1ED" />
                    <XAxis dataKey="label" {...axisProps} minTickGap={12} />
                    <YAxis {...axisProps} allowDecimals={false} width={40} />
                    <Tooltip {...chartTooltipStyle} />
                    <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} formatter={(v) => (v === 'done' ? 'Completed' : 'Planned')} />
                    <Bar dataKey="planned" fill="#D6EADF" radius={[3, 3, 0, 0]} maxBarSize={22} />
                    <Bar dataKey="done" fill="#23694A" radius={[3, 3, 0, 0]} maxBarSize={22} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel title="Water intake">
              <div className="h-60">
                <ResponsiveContainer>
                  <BarChart data={charts.daily} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#EEF1ED" />
                    <XAxis dataKey="label" {...axisProps} minTickGap={24} />
                    <YAxis {...axisProps} width={52} tickFormatter={(v) => `${(v / 1000).toFixed(1)} L`} />
                    <Tooltip {...chartTooltipStyle} formatter={(v) => [`${(v / 1000).toFixed(2)} L`, 'Water']} />
                    <ReferenceLine y={data.targets.water_ml} stroke="#16211C" strokeDasharray="4 4" />
                    <Bar dataKey="water_ml" fill="#2C9AB7" radius={[3, 3, 0, 0]} maxBarSize={22} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>

          <Panel title="Body measurements" className="mt-4" bodyClass="p-0">
            {charts.measures.length === 0 ? (
              <p className="p-5 text-sm text-muted">Add waist, chest, hips or arm measurements when you log your weight to track them here.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="num w-full min-w-[520px] text-sm">
                  <thead><tr className="border-b border-line text-left text-muted">
                    {['Date', 'Weight', 'Waist', 'Chest', 'Hips', 'Arms'].map((h) => <th key={h} className="px-5 py-2.5 font-medium">{h}</th>)}
                  </tr></thead>
                  <tbody className="divide-y divide-line">
                    {[...charts.measures].reverse().map((m) => (
                      <tr key={m.date}>
                        <td className="px-5 py-2.5 font-semibold">{shortDate(m.date)}</td>
                        <td className="px-5 py-2.5">{m.weight} kg</td>
                        {['waist', 'chest', 'hips', 'arms'].map((k) => <td key={k} className="px-5 py-2.5">{m[k] ? `${m[k]} cm` : '—'}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </>
      )}
    </>
  )
}
