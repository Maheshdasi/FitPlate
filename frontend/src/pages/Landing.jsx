import { Link } from 'react-router-dom'
import { BarChart3, Brain, Calculator, Dumbbell, Salad, ShieldCheck, Sigma, UtensilsCrossed } from 'lucide-react'
import CalorieRing from '../components/CalorieRing'
import Logo from '../components/Logo'
import { useAuth } from '../context/AuthContext'

const BENEFITS = [
  { icon: Calculator, title: 'Targets from your own numbers',
    text: 'Daily calories, protein, carbs and fat worked out from your age, height, weight, activity and goal, with every step shown.' },
  { icon: UtensilsCrossed, title: 'Food logging that fits Indian meals',
    text: 'Dal, roti, idli, paneer, curd and more, measured in bowls, pieces and cups, the way you actually eat.' },
  { icon: Salad, title: 'Meals picked for what is left today',
    text: 'Suggestions respect your diet type and allergies, and adjust to the calories and protein you still need.' },
  { icon: Dumbbell, title: 'A workout plan for your week',
    text: 'Sessions matched to your level, goal, equipment and number of free days. Tick off exercises as you go.' },
  { icon: BarChart3, title: 'Progress you can read in seconds',
    text: 'Weight trend, calories against goal, protein and workout consistency over 7 days to 6 months.' },
  { icon: Brain, title: 'A weekly review in plain words',
    text: '“You stayed close to your calorie target on 5 out of 7 days.” Followed by one or two practical changes to try.' },
]

const STEPS = [
  ['Create your profile', 'Tell us your height, weight, goal, diet type and how often you can train.'],
  ['Get your targets', 'See your calories and macros, and exactly how they were calculated.'],
  ['Log food and workouts', 'Search foods, add recommended meals and tick off exercises.'],
  ['Review every week', 'Read your weekly insights and adjust one habit at a time.'],
]

const METHODS = [
  { icon: Sigma, kind: 'Formula', items: ['BMI (WHO)', 'BMR (Mifflin-St Jeor)', 'TDEE and macro split'] },
  { icon: ShieldCheck, kind: 'Rules', items: ['Diet and allergy filters', 'Weekly workout split', 'Sets, reps and rest'] },
  { icon: Brain, kind: 'Machine learning', items: ['Content-based meal ranking', 'Exercise similarity (MMR)', 'K-Means habits, regression trend'] },
]

export default function Landing() {
  const { user } = useAuth()
  const start = user ? (user.has_profile ? '/dashboard' : '/setup') : '/register'

  return (
    <div className="min-h-screen bg-canvas">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Logo />
        <nav className="flex items-center gap-2">
          {user ? (
            <Link to={start} className="btn-primary">Open dashboard</Link>
          ) : (
            <>
              <Link to="/login" className="btn-ghost">Log in</Link>
              <Link to="/register" className="btn-primary">Get started</Link>
            </>
          )}
        </nav>
      </header>

      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 pb-16 pt-8 lg:grid-cols-[1.15fr_1fr] lg:pt-16">
        <div>
          <p className="mb-4 text-sm font-semibold text-brand-600">AI Fitness &amp; Nutrition Platform</p>
          <h1 className="text-[40px] font-extrabold leading-[1.05] sm:text-[56px]">
            Know what to eat, how to train, and whether it's working.
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
            FitPlate turns your profile into daily calorie and protein targets, suggests meals and workouts that fit
            them, and explains your week back to you in plain language.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to={start} className="btn-primary px-6 py-3 text-base">Get started for free</Link>
            <Link to="/login" state={{ demo: true }} className="btn-secondary px-6 py-3 text-base">Try the demo account</Link>
          </div>
        </div>

        {/* A real piece of the product, not an illustration */}
        <div className="panel mx-auto w-full max-w-md p-6" aria-label="Example of today's summary">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-muted">Today</p>
              <p className="text-lg font-extrabold">1,450 of 2,000 kcal</p>
            </div>
            <span className="chip bg-brand-50 text-brand-700">On track</span>
          </div>
          <div className="mt-5 flex justify-center"><CalorieRing consumed={1450} goal={2000} protein={95} carbs={160} fat={48} size={190} /></div>
          <div className="mt-6 space-y-3">
            {[['Protein', 95, 130, 'bg-protein'], ['Carbs', 160, 220, 'bg-carbs'], ['Fat', 48, 65, 'bg-fat']].map(([n, v, g, c]) => (
              <div key={n}>
                <div className="mb-1 flex justify-between text-sm"><span className="font-semibold">{n}</span>
                  <span className="num text-muted"><b className="text-ink">{v}</b> / {g} g</span></div>
                <div className="h-2 rounded-full bg-black/[0.06]"><div className={`h-2 rounded-full ${c}`} style={{ width: `${v / g * 100}%` }} /></div>
              </div>
            ))}
          </div>
          <div className="mt-6 rounded-lg bg-brand-50 p-3 text-sm">
            <p className="font-semibold text-brand-900">Suggested snack</p>
            <p className="text-brand-900/80">Sprouts chaat: 130 kcal, 8 g protein. Helps close your 35 g protein gap.</p>
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="border-y border-line bg-white">
        <div className="mx-auto max-w-6xl px-5 py-16">
          <h2 className="max-w-xl text-3xl font-extrabold">Everything for your fitness routine, in one place</h2>
          <div className="mt-10 grid gap-x-10 gap-y-9 sm:grid-cols-2 lg:grid-cols-3">
            {BENEFITS.map(({ icon: Icon, title, text }) => (
              <div key={title}>
                <Icon className="text-brand-600" size={24} aria-hidden />
                <h3 className="mt-3 text-[17px] font-bold">{title}</h3>
                <p className="mt-1.5 leading-relaxed text-muted">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works: a real sequence, so it is numbered */}
      <section className="mx-auto max-w-6xl px-5 py-16">
        <h2 className="text-3xl font-extrabold">How it works</h2>
        <ol className="mt-8 grid gap-6 md:grid-cols-4">
          {STEPS.map(([title, text], i) => (
            <li key={title} className="border-t-2 border-brand-600 pt-4">
              <span className="num text-sm font-bold text-brand-600">Step {i + 1}</span>
              <h3 className="mt-1 text-[17px] font-bold">{title}</h3>
              <p className="mt-1 text-muted">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Transparency */}
      <section className="bg-brand-900 text-white">
        <div className="mx-auto max-w-6xl px-5 py-16">
          <h2 className="max-w-2xl text-3xl font-extrabold">We tell you which numbers come from a formula and which come from a model</h2>
          <p className="mt-3 max-w-2xl text-white/70">Calorie targets use published equations. Recommendations and insights use
            machine learning. Each page labels which is which.</p>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {METHODS.map(({ icon: Icon, kind, items }) => (
              <div key={kind} className="rounded-panel border border-white/15 p-5">
                <Icon size={22} className="text-brand-200" aria-hidden />
                <h3 className="mt-3 text-lg font-bold">{kind}</h3>
                <ul className="mt-2 space-y-1 text-white/75">{items.map((t) => <li key={t}>{t}</li>)}</ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="mx-auto max-w-6xl px-5 py-10 text-sm text-muted">
        <p>FitPlate gives general fitness and nutrition guidance. It is not medical advice and does not diagnose or treat any condition.</p>
        <p className="mt-2">Built with React, FastAPI, PostgreSQL and scikit-learn as a final-year B.Tech capstone project.</p>
      </footer>
    </div>
  )
}
