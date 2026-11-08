import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ErrorNote, Field } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import AuthShell from './AuthShell'

const DEMO = { email: 'demo@fitness.app', password: 'Demo@1234' }

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState(location.state?.demo ? DEMO : { email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [busy, setBusy] = useState(false)

  const validate = () => {
    const e = {}
    if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = 'Enter a valid email address.'
    if (!form.password) e.password = 'Enter your password.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const submit = async (ev) => {
    ev.preventDefault()
    setServerError('')
    if (!validate()) return
    setBusy(true)
    try {
      const me = await login(form.email.trim(), form.password)
      navigate(me.has_profile ? (location.state?.from || '/dashboard') : '/setup', { replace: true })
    } catch (err) {
      setServerError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <AuthShell title="Log in" subtitle="Welcome back. Pick up where you left off."
      footer={<>New here? <Link to="/register" className="font-semibold text-brand-700 underline">Create an account</Link></>}>
      <form onSubmit={submit} noValidate className="space-y-4">
        <ErrorNote message={serverError} />
        <Field label="Email" htmlFor="email" error={errors.email}>
          <input id="email" type="email" autoComplete="email" className={`input ${errors.email ? 'input-error' : ''}`}
            value={form.email} onChange={set('email')} />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password}>
          <input id="password" type="password" autoComplete="current-password"
            className={`input ${errors.password ? 'input-error' : ''}`} value={form.password} onChange={set('password')} />
        </Field>
        <button type="submit" className="btn-primary w-full py-3" disabled={busy}>{busy ? 'Logging in…' : 'Log in'}</button>
      </form>
      <div className="mt-5 rounded-lg bg-brand-50 p-3 text-sm text-brand-900">
        <p className="font-semibold">Demo account</p>
        <p className="mt-0.5 text-brand-900/80">Has four months of sample food, workout and weight history.</p>
        <button type="button" onClick={() => setForm(DEMO)} className="mt-2 font-semibold underline">Fill in demo login</button>
      </div>
    </AuthShell>
  )
}
