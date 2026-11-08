import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ErrorNote, Field } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import AuthShell from './AuthShell'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [busy, setBusy] = useState(false)

  const validate = () => {
    const e = {}
    if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = 'Enter a valid email address.'
    if (form.password.length < 8) e.password = 'Use at least 8 characters.'
    else if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) e.password = 'Include at least one letter and one number.'
    if (form.confirm !== form.password) e.confirm = 'Passwords do not match.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const submit = async (ev) => {
    ev.preventDefault()
    setServerError('')
    if (!validate()) return
    setBusy(true)
    try {
      await register(form.email.trim(), form.password)
      navigate('/setup', { replace: true })
    } catch (err) {
      setServerError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <AuthShell title="Create your account" subtitle="Next, we'll ask a few questions to set your targets."
      footer={<>Already have an account? <Link to="/login" className="font-semibold text-brand-700 underline">Log in</Link></>}>
      <form onSubmit={submit} noValidate className="space-y-4">
        <ErrorNote message={serverError} />
        <Field label="Email" htmlFor="email" error={errors.email}>
          <input id="email" type="email" autoComplete="email" className={`input ${errors.email ? 'input-error' : ''}`}
            value={form.email} onChange={set('email')} />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password} hint="At least 8 characters, with a letter and a number.">
          <input id="password" type="password" autoComplete="new-password"
            className={`input ${errors.password ? 'input-error' : ''}`} value={form.password} onChange={set('password')} />
        </Field>
        <Field label="Confirm password" htmlFor="confirm" error={errors.confirm}>
          <input id="confirm" type="password" autoComplete="new-password"
            className={`input ${errors.confirm ? 'input-error' : ''}`} value={form.confirm} onChange={set('confirm')} />
        </Field>
        <button type="submit" className="btn-primary w-full py-3" disabled={busy}>{busy ? 'Creating account…' : 'Create account'}</button>
      </form>
    </AuthShell>
  )
}
