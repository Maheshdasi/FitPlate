import { Link } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { CheckCircle2, Circle, Droplets, Dumbbell, Minus, Plus, Scale, Target, Utensils } from 'lucide-react'
import { del, get, localDate, post } from '../api/client'
import CalorieRing from '../components/CalorieRing'
import {
  axisProps, chartTooltipStyle, ErrorNote, MacroRow, Panel, PageHeader, ProgressBar, Spinner, Stat,
} from '../components/ui'
import { longDate, MEAL_LABELS, shortDate, weekday } from '../utils/format'
import useApi from '../utils/useApi'

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

const STATUS = {
  done: ['Completed', 'bg-brand-50 text-brand-700'],
  in_progress: ['In progress', 'bg-amber-50 text-amber-800'],
  pending: ['Not started', 'bg-black/5 text-muted'],
  rest: ['Rest day', 'bg-black/5 text-muted'],
}

export default function Dashboard() {
  const today = localDate()
  const { data, error, loading, reload, setData } = useApi(() => get('/dashboard', { date: today }), [today])

  const changeWater = async (add) => {
    try {
      const res = add ? await post('/progress/water', { amount_ml: 250, log_date: today })
        : await del('/progress/water/last', { date: today })
      setData((d) => ({ ...d, water: { ...d.water, total_ml: res.total_ml } }))
    } catch { /* nothing to undo */ }
  }

  if (loading && !data) return <Spinner />
  if (error) return <ErrorNote message={error} onRetry={reload} />

  const { targets: t, consumed: c, remaining: r, workout: w, weight } = data
  const first = data.name.split(' ')[0]
  const macroPie = [
    { name: 'Protein', value: Math.round(c.protein * 4), grams: c.protein, color: '#3567B5' },
    { name: 'Carbs', value: Math.round(c.carbs * 4), grams: c.carbs, color: '#D99A1E' },
    { name: 'Fat', value: Math.round(c.fat * 9), grams: c.fat, color: '#B4537A' },
  ]
  const weekCalories = data.week.map((d) => ({ ...d, label: weekday(d.date) }))
  const weightData = weight.history.map((h) => ({ ...h, label: shortDate(h.date) }))
  const toGo = Math.round((weight.current - weight.target) * 10) / 10
  const [statusLabel, statusClass] = STATUS[w.status]
  const meal = data.next_meal?.recommended

  return (
    <>
      <PageHeader title={`${greeting()}, ${first}`} subtitle={longDate(data.date)}
        actions={<><Link to="/food" className="btn-primary"><Plus size={16} aria-hidden /> Log food</Link>
          <Link to="/workout-tracker" className="btn-secondary">Start workout</Link></>} />

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Calories eaten" value={Math.round(c.calories).toLocaleString('en-IN')} unit="kcal" icon={Utensils}
          sub={r.calories >= 0 ? `${r.calories.toLocaleString('en-IN')} kcal remaining` : `${Math.abs(r.calories)} kcal over goal`} />
        <Stat label="Protein" value={Math.round(c.protein)} unit={`/ ${t.protein_g} g`} icon={Target} tone="text-protein"
          sub={r.protein > 0 ? `${Math.round(r.protein)} g to go` : 'Target reached'} />
        <div className="panel p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-muted"><Droplets size={16} className="text-water" aria-hidden /> Water</div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="num text-2xl font-extrabold">{(data.water.total_ml / 1000).toFixed(2)}</span>
            <span className="text-sm font-semibold text-muted">/ {(data.water.goal_ml / 1000).toFixed(1)} L</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <button onClick={() => changeWater(false)} className="rounded-md border border-line p-1 hover:bg-black/5" aria-label="Remove last glass"><Minus size={14} /></button>
            <button onClick={() => changeWater(true)} className="flex items-center gap-1 rounded-md border border-water/40 bg-water/10 px-2 py-1 text-xs font-semibold text-[#1d6f85] hover:bg-water/20">
              <Plus size={13} aria-hidden /> 250 ml
            </button>
          </div>
        </div>
        <Stat label="Weight" value={weight.current} unit="kg" icon={Scale} tone="text-ink"
          sub={toGo === 0 ? 'At your target' : `Target ${weight.target} kg (${Math.abs(toGo)} kg to ${toGo > 0 ? 'lose' : 'gain'})`} />
      </div>

      {/* Calories + macros */}
      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <Panel title="Today's calories" className="lg:col-span-3"
          action={<Link to="/food" className="text-sm font-semibold text-brand-700 hover:underline">Open food tracker</Link>}>
          <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center">
            <CalorieRing consumed={c.calories} goal={t.daily_calories} protein={c.protein} carbs={c.carbs} fat={c.fat} size={184} />
            <div className="w-full flex-1 space-y-4">
              <ProgressBar label="Protein" value={c.protein} goal={t.protein_g} color="bg-protein" showNumbers />
              <ProgressBar label="Carbohydrates" value={c.carbs} goal={t.carbs_g} color="bg-carbs" showNumbers />
              <ProgressBar label="Fat" value={c.fat} goal={t.fat_g} color="bg-fat" showNumbers />
              <div className="grid grid-cols-4 gap-2 border-t border-line pt-3 text-center">
                {Object.entries(data.by_meal).map(([m, v]) => (
                  <div key={m}>
                    <p className="text-xs text-muted">{MEAL_LABELS[m]}</p>
                    <p className="num text-sm font-bold">{v.calories ? Math.round(v.calories) : '-'}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Panel>

        <Panel title="Macronutrients today" className="lg:col-span-2">
          {c.calories > 0 ? (
            <div className="flex items-center gap-4">
              <div className="h-40 w-40 shrink-0">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={macroPie} dataKey="value" innerRadius={44} outerRadius={70} paddingAngle={2} stroke="none">
                      {macroPie.map((m) => <Cell key={m.name} fill={m.color} />)}
                    </Pie>
                    <Tooltip {...chartTooltipStyle} formatter={(v, n, p) => [`${Math.round(p.payload.grams)} g (${v} kcal)`, n]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="space-y-2 text-sm">
                {macroPie.map((m) => {
                  const total = macroPie.reduce((s, x) => s + x.value, 0)
                  return (
                    <li key={m.name} className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-sm" style={{ background: m.color }} aria-hidden />
                      <span className="w-16 text-muted">{m.name}</span>
                      <span className="num font-bold">{Math.round(m.value / total * 100)}%</span>
                    </li>
                  )
                })}
                <li className="pt-1 text-xs text-muted">Share of today's calories</li>
              </ul>
            </div>
          ) : <p className="py-10 text-center text-sm text-muted">Log a meal to see your macro split.</p>}
        </Panel>
      </div>

      {/* Charts */}
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="Calories this week">
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={weekCalories} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="#EEF1ED" />
                <XAxis dataKey="label" {...axisProps} />
                <YAxis {...axisProps} width={48} />
                <Tooltip {...chartTooltipStyle} formatter={(v) => [`${v} kcal`, 'Eaten']} labelFormatter={(l, p) => p?.[0] ? shortDate(p[0].payload.date) : l} />
                <ReferenceLine y={t.daily_calories} stroke="#16211C" strokeDasharray="4 4"
                  label={{ value: `Goal ${t.daily_calories}`, position: 'insideTopRight', fontSize: 11, fill: '#5E6B64' }} />
                <Bar dataKey="calories" radius={[5, 5, 0, 0]} maxBarSize={36}>
                  {weekCalories.map((d) => <Cell key={d.date}
                    fill={d.calories > t.daily_calories * 1.1 ? '#DC6B4A' : d.date === today ? '#4F9A73' : '#2F7A55'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Weight progress (90 days)" action={<Link to="/progress" className="text-sm font-semibold text-brand-700 hover:underline">View progress</Link>}>
          <div className="h-56">
            {weightData.length > 1 ? (
              <ResponsiveContainer>
                <LineChart data={weightData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="#EEF1ED" />
                  <XAxis dataKey="label" {...axisProps} minTickGap={28} />
                  <YAxis {...axisProps} width={48} domain={['dataMin - 1', 'dataMax + 1']} />
                  <Tooltip {...chartTooltipStyle} formatter={(v) => [`${v} kg`, 'Weight']} />
                  <ReferenceLine y={weight.target} stroke="#2F7A55" strokeDasharray="4 4"
                    label={{ value: `Target ${weight.target}`, position: 'insideBottomRight', fontSize: 11, fill: '#2F7A55' }} />
                  <Line dataKey="weight" stroke="#16211C" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : <p className="py-16 text-center text-sm text-muted">Log your weight a few times to see the trend.</p>}
          </div>
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {/* Today's workout */}
        <Panel title="Today's workout" action={<span className={`chip ${statusClass}`}>{statusLabel}</span>}>
          {w.is_rest_day ? (
            <p className="text-sm text-muted">No session planned today. A 20 to 30 minute walk or light stretching helps recovery.</p>
          ) : (
            <>
              <p className="font-bold">{w.session.title}</p>
              <p className="text-sm text-muted">About {w.session.estimated_minutes} min, {w.completed} of {w.total} exercises done</p>
              <ul className="mt-3 space-y-1.5">
                {w.session.exercises.slice(0, 5).map((e) => (
                  <li key={e.exercise_id} className="flex items-center gap-2 text-sm">
                    <Dumbbell size={14} className="text-muted" aria-hidden />
                    <span className="flex-1 truncate">{e.name}</span>
                    <span className="num text-muted">{e.sets} × {e.reps}</span>
                  </li>
                ))}
              </ul>
              <Link to="/workout-tracker" className="btn-secondary mt-4 w-full">Open workout tracker</Link>
            </>
          )}
        </Panel>

        {/* Workout consistency */}
        <Panel title="Workout consistency">
          <div className="grid grid-cols-7 gap-1.5 text-center">
            {data.week.map((d) => (
              <div key={d.date}>
                <p className="text-[11px] text-muted">{weekday(d.date).slice(0, 2)}</p>
                <div className="mt-1 flex justify-center">
                  {d.workout_done ? <CheckCircle2 className="text-brand-600" size={24} aria-label="Workout done" />
                    : d.workout_planned ? <Circle className={d.date < today ? 'text-red-300' : 'text-line'} size={24} aria-label="Planned" />
                      : <span className="flex h-6 w-6 items-center justify-center text-xs text-muted" aria-label="Rest day">-</span>}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-sm">
            <b className="num">{data.week_totals.workouts_done}</b> of <b className="num">{data.week_totals.workouts_planned}</b> planned workouts done in the last 7 days.
          </p>
          <div className="mt-3"><ProgressBar value={data.week_totals.workouts_done} goal={Math.max(data.week_totals.workouts_planned, 1)} /></div>
        </Panel>

        {/* Recommended meal */}
        <Panel title={`Suggested ${MEAL_LABELS[data.next_meal.meal_type]?.toLowerCase()}`}
          action={<Link to="/meals" className="text-sm font-semibold text-brand-700 hover:underline">Meal plan</Link>}>
          {meal ? (
            <>
              <p className="font-bold">{meal.name}</p>
              <div className="mt-1"><MacroRow {...meal} compact /></div>
              <p className="mt-3 text-sm text-muted">{meal.ingredients.slice(0, 4).join(', ')}</p>
              <p className="mt-3 text-sm"><span className="font-semibold">Why: </span>{meal.reasons[0]}.</p>
            </>
          ) : <p className="text-sm text-muted">No suitable meal found for your settings.</p>}
        </Panel>
      </div>
    </>
  )
}
