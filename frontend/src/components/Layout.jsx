import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Calculator, CalendarCheck, ChartLine, Dumbbell, LayoutDashboard, Lightbulb, LogOut, Menu,
  MessageCircle, Salad, Settings, UtensilsCrossed, X,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import Logo from './Logo'

const NAV = [
  { group: null, items: [{ to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard }] },
  { group: 'Nutrition', items: [
    { to: '/calculator', label: 'Calorie calculator', icon: Calculator },
    { to: '/food', label: 'Food tracker', icon: UtensilsCrossed },
    { to: '/meals', label: 'Meal plan', icon: Salad },
  ] },
  { group: 'Training', items: [
    { to: '/workouts', label: 'Workout plan', icon: Dumbbell },
    { to: '/workout-tracker', label: 'Workout tracker', icon: CalendarCheck },
  ] },
  { group: 'Progress', items: [
    { to: '/progress', label: 'Progress', icon: ChartLine },
    { to: '/insights', label: 'Weekly insights', icon: Lightbulb },
    { to: '/assistant', label: 'Fitness assistant', icon: MessageCircle },
  ] },
]

function NavItems({ onNavigate }) {
  return (
    <nav className="flex flex-col gap-5" aria-label="Main">
      {NAV.map(({ group, items }) => (
        <div key={group || 'top'}>
          {group && <p className="mb-1.5 px-3 text-xs font-semibold text-white/45">{group}</p>}
          <ul className="flex flex-col gap-0.5">
            {items.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink to={to} onClick={onNavigate}
                  className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-[14px] font-semibold transition-colors ${
                    isActive ? 'bg-white text-brand-900' : 'text-white/75 hover:bg-white/10 hover:text-white'}`}>
                  <Icon size={18} aria-hidden /> {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  )
}

function SidebarFooter({ onNavigate }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="border-t border-white/10 pt-4">
      <NavLink to="/settings" onClick={onNavigate}
        className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-[14px] font-semibold ${
          isActive ? 'bg-white text-brand-900' : 'text-white/75 hover:bg-white/10 hover:text-white'}`}>
        <Settings size={18} aria-hidden /> Profile & settings
      </NavLink>
      <div className="mt-3 flex items-center justify-between gap-2 px-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">{user?.name || 'Your account'}</p>
          <p className="truncate text-xs text-white/50">{user?.email}</p>
        </div>
        <button onClick={() => { logout(); navigate('/login') }} className="rounded-lg p-2 text-white/60 hover:bg-white/10 hover:text-white"
          aria-label="Log out" title="Log out">
          <LogOut size={18} />
        </button>
      </div>
    </div>
  )
}

export default function Layout() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  useEffect(() => { setOpen(false); window.scrollTo(0, 0) }, [location.pathname])

  return (
    <div className="min-h-screen lg:pl-64">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col justify-between bg-brand-900 px-3 py-5 lg:flex">
        <div>
          <div className="mb-7 px-3"><Logo light /></div>
          <NavItems />
        </div>
        <SidebarFooter />
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-line bg-canvas/95 px-4 py-3 backdrop-blur lg:hidden">
        <Logo />
        <button onClick={() => setOpen(true)} className="rounded-lg p-2 hover:bg-black/5" aria-label="Open menu">
          <Menu size={22} />
        </button>
      </header>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-72 max-w-[85%] flex-col justify-between overflow-y-auto bg-brand-900 px-3 py-5">
            <div>
              <div className="mb-6 flex items-center justify-between px-3">
                <Logo light />
                <button onClick={() => setOpen(false)} className="rounded-lg p-1.5 text-white/70 hover:bg-white/10" aria-label="Close menu">
                  <X size={20} />
                </button>
              </div>
              <NavItems onNavigate={() => setOpen(false)} />
            </div>
            <SidebarFooter onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <Outlet />
      </main>
    </div>
  )
}
