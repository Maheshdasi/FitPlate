import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import { useAuth } from './context/AuthContext'
import Assistant from './pages/Assistant'
import CalculatorPage from './pages/Calculator'
import Dashboard from './pages/Dashboard'
import FoodTracker from './pages/FoodTracker'
import Insights from './pages/Insights'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Meals from './pages/Meals'
import NotFound from './pages/NotFound'
import ProfileSetup from './pages/ProfileSetup'
import Progress from './pages/Progress'
import Register from './pages/Register'
import SettingsPage from './pages/Settings'
import WorkoutTracker from './pages/WorkoutTracker'
import Workouts from './pages/Workouts'

/** Requires login; also sends users without a profile to the setup page. */
function Protected({ children, needsProfile = true }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (needsProfile && !user.has_profile) return <Navigate to="/setup" replace />
  return children
}

function GuestOnly({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (user) return <Navigate to={user.has_profile ? '/dashboard' : '/setup'} replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
      <Route path="/setup" element={<Protected needsProfile={false}><ProfileSetup /></Protected>} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/calculator" element={<CalculatorPage />} />
        <Route path="/food" element={<FoodTracker />} />
        <Route path="/meals" element={<Meals />} />
        <Route path="/workouts" element={<Workouts />} />
        <Route path="/workout-tracker" element={<WorkoutTracker />} />
        <Route path="/progress" element={<Progress />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
