import { Link } from 'react-router-dom'
import Logo from '../components/Logo'

export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <header className="px-5 py-5"><Link to="/" aria-label="Home"><Logo /></Link></header>
      <main className="flex flex-1 items-start justify-center px-4 pb-16 pt-6 sm:pt-12">
        <div className="w-full max-w-md">
          <h1 className="text-[28px] font-extrabold">{title}</h1>
          {subtitle && <p className="mt-1 text-muted">{subtitle}</p>}
          <div className="panel mt-6 p-6">{children}</div>
          {footer && <p className="mt-5 text-center text-sm text-muted">{footer}</p>}
        </div>
      </main>
    </div>
  )
}
