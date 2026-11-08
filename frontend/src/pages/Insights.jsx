import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AlertTriangle, CheckCircle2, Info, Lightbulb, Users } from 'lucide-react'
import { get, localDate } from '../api/client'
import { axisProps, chartTooltipStyle, Disclaimer, ErrorNote, Panel, PageHeader, ProgressBar, Segmented, Spinner, Stat } from '../components/ui'
import { shortDate, weekday } from '../utils/format'
import useApi from '../utils/useApi'

const TONE = {
  good: [CheckCircle2, 'text-brand-600'],
  warn: [AlertTriangle, 'text-amber-600'],
  info: [Info, 'text-protein'],
}

const FEATURE_LABELS = {
  calorie_adherence: 'Days on calorie target',
  protein_ratio: 'Protein vs target',
  workout_ratio: 'Planned workouts done',
  logging_ratio: 'Days with food logged',
}

export default function Insights() {
  const today = localDate()
  const [view, setView] = useState('last')
  const [weekStart, setWeekStart] = useState('')
  const params = weekStart ? { week_start: weekStart, date: today } : { current: view === 'current' || undefined, date: today }
  const { data, error, loading, reload } = useApi(() => get('/insights/weekly', params), [view, weekStart, today])
  const history = useApi(() => get('/insights/history'), [data?.week_start])

  const pickView = (v) => { setWeekStart(''); setView(v) }

  return (
    <>
      <PageHeader title="Weekly insights"
        subtitle="A plain-language review of your week, with practical suggestions. Weeks run Monday to Sunday."
        actions={<>
          <Segmented ariaLabel="Week" value={weekStart ? '' : view} onChange={pickView}
            options={[{ value: 'last', label: 'Last week' }, { value: 'current', label: 'This week so far' }]} />
          {(history.data || []).length > 0 && (
            <select className="input w-auto py-2" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} aria-label="Earlier weeks">
              <option value="">Earlier weeks…</option>
              {history.data.map((h) => <option key={h.week_start} value={h.week_start}>Week of {shortDate(h.week_start)}</option>)}
            </select>
          )}
        </>} />

      {loading && !data ? <Spinner label="Analysing your week…" /> : error ? <ErrorNote message={error} onRetry={reload} /> : (
        <>
          <p className="mb-4 text-sm font-semibold text-muted">
            {shortDate(data.week_start)} to {shortDate(data.week_end)}{!data.is_complete && ' (week in progress)'}
          </p>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="On calorie target" value={data.metrics.days_on_calorie_target} unit="/ 7 days" sub={`${data.metrics.days_logged} days logged`} />
            <Stat label="Average protein" value={Math.round(data.metrics.avg_protein)} unit="g" tone="text-protein"
              sub={`Target met on ${data.metrics.protein_target_days} days`} />
            <Stat label="Workouts" value={data.metrics.workouts_completed} unit={`/ ${data.metrics.workouts_planned} planned`} />
            <Stat label="Weight change" tone="text-ink"
              value={data.metrics.weight_change_kg == null ? '-' : `${data.metrics.weight_change_kg > 0 ? '+' : ''}${data.metrics.weight_change_kg}`}
              unit="kg" sub="Weekly average vs previous week" />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-5">
            <Panel title="What happened" className="lg:col-span-3">
              <ul className="space-y-3">
                {data.insights.map((i) => {
                  const [Icon, color] = TONE[i.tone] || TONE.info
                  return (
                    <li key={i.text} className="flex gap-3">
                      <Icon size={19} className={`mt-0.5 shrink-0 ${color}`} aria-hidden />
                      <span className="leading-relaxed">{i.text}</span>
                    </li>
                  )
                })}
              </ul>
              <div className="mt-5 h-48">
                <ResponsiveContainer>
                  <BarChart data={data.daily.map((d) => ({ ...d, label: weekday(d.date) }))} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#EEF1ED" />
                    <XAxis dataKey="label" {...axisProps} />
                    <YAxis {...axisProps} width={48} />
                    <Tooltip {...chartTooltipStyle} formatter={(v) => [`${Math.round(v)} kcal`, 'Calories']} />
                    <Bar dataKey="calories" fill="#2F7A55" radius={[4, 4, 0, 0]} maxBarSize={32} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <div className="space-y-4 lg:col-span-2">
              <Panel title="Try this next week">
                <ul className="space-y-3">
                  {data.suggestions.map((s) => (
                    <li key={s} className="flex gap-3 text-[15px] leading-relaxed">
                      <Lightbulb size={18} className="mt-0.5 shrink-0 text-carbs" aria-hidden />
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </Panel>

              <Panel title="Your habit pattern" action={<span className="chip bg-black/5 text-muted">K-Means cluster</span>}>
                <div className="flex items-center gap-2">
                  <Users size={18} className="text-brand-600" aria-hidden />
                  <p className="text-lg font-extrabold">{data.behaviour.label}</p>
                </div>
                <p className="mt-1 text-sm text-muted">{data.behaviour.description}</p>
                <div className="mt-4 space-y-3">
                  {Object.entries(data.behaviour.features).map(([k, v]) => (
                    <div key={k}>
                      <div className="mb-1 flex justify-between text-xs"><span className="font-semibold">{FEATURE_LABELS[k]}</span>
                        <span className="num text-muted">{Math.round(Math.min(v, 1.2) * 100)}%</span></div>
                      <ProgressBar value={Math.min(v, 1)} goal={1} height="h-1.5" />
                    </div>
                  ))}
                </div>
              </Panel>
            </div>
          </div>
          <div className="mt-4"><Disclaimer>Insights are based only on what you logged and are general guidance, not medical advice.</Disclaimer></div>
        </>
      )}
    </>
  )
}
