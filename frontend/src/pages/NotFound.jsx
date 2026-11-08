import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <p className="num text-6xl font-extrabold text-brand-600">404</p>
      <h1 className="mt-3 text-2xl font-extrabold">This page doesn't exist</h1>
      <p className="mt-2 text-muted">The link may be broken or the page may have moved.</p>
      <Link to="/" className="btn-primary mt-6">Go to home page</Link>
    </div>
  )
}
