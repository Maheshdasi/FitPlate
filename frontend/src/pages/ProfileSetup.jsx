import { useNavigate } from 'react-router-dom'
import { put } from '../api/client'
import Logo from '../components/Logo'
import ProfileForm from '../components/ProfileForm'
import { useAuth } from '../context/AuthContext'

export default function ProfileSetup() {
  const navigate = useNavigate()
  const { markProfileComplete, logout } = useAuth()

  const save = async (payload) => {
    const profile = await put('/profile', payload)
    markProfileComplete(profile.name)
    navigate('/calculator', { replace: true, state: { welcome: true } })
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="flex items-center justify-between px-5 py-5">
        <Logo />
        <button className="btn-ghost" onClick={() => { logout(); navigate('/') }}>Log out</button>
      </header>
      <main className="mx-auto max-w-xl px-4 pb-16 pt-4">
        <h1 className="text-[28px] font-extrabold">Set up your profile</h1>
        <p className="mt-1 text-muted">This takes about two minutes. You can change anything later in settings.</p>
        <div className="panel mt-6 p-6">
          <ProfileForm wizard onSubmit={save} submitLabel="Calculate my targets" />
        </div>
      </main>
    </div>
  )
}
