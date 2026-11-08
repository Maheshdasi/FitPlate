import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { get, put } from '../api/client'
import ProfileForm from '../components/ProfileForm'
import { ErrorNote, Panel, PageHeader, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import useApi from '../utils/useApi'

export default function SettingsPage() {
  const { data, error, loading, reload, setData } = useApi(() => get('/profile'), [])
  const { logout, markProfileComplete } = useAuth()
  const navigate = useNavigate()
  const [saved, setSaved] = useState('')

  const save = async (payload) => {
    const profile = await put('/profile', payload)
    setData(profile)
    markProfileComplete(profile.name)
    setSaved('Profile saved. Your calorie targets, meal plan and workout plan have been updated.')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  if (loading) return <Spinner />
  if (error) return <ErrorNote message={error} onRetry={reload} />

  return (
    <>
      <PageHeader title="Profile & settings" subtitle="Update your details at any time. Targets and plans recalculate when you save." />
      {saved && <p className="mb-4 rounded-lg bg-brand-50 px-4 py-3 text-sm font-semibold text-brand-800" role="status">{saved}</p>}
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Your profile" className="lg:col-span-2">
          <ProfileForm key={data.id + (data.updated_at || '')} initial={{ ...data, food_preferences: data.food_preferences || '' }} onSubmit={save} />
        </Panel>
        <div className="space-y-4">
          <Panel title="Account">
            <p className="text-sm text-muted">Signed in as</p>
            <p className="break-all font-semibold">{data.email}</p>
            <button className="btn-secondary mt-4 w-full" onClick={() => { logout(); navigate('/login') }}>
              <LogOut size={16} aria-hidden /> Log out
            </button>
          </Panel>
          <Panel title="About your data">
            <p className="text-sm leading-relaxed text-muted">Your password is stored only as a secure bcrypt hash. Your food, workout and
              weight logs are used only to calculate your targets, recommendations and insights.</p>
          </Panel>
        </div>
      </div>
    </>
  )
}
