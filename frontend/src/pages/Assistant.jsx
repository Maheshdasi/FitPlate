import { Fragment, useEffect, useRef, useState } from 'react'
import { Bot, Send } from 'lucide-react'
import { localDate, post } from '../api/client'
import { Disclaimer, PageHeader } from '../components/ui'

const STARTERS = [
  'What should I eat for dinner?',
  'How much protein do I need today?',
  'Suggest a high-protein vegetarian breakfast.',
  'What workout should I do today?',
  'I have 500 calories remaining. What can I eat?',
  'How is my progress?',
]

/** Renders **bold** and line breaks from the assistant's plain-text replies. */
function RichText({ text }) {
  return text.split('\n').map((line, i) => (
    <Fragment key={i}>
      {i > 0 && <br />}
      {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
        part.startsWith('**') ? <strong key={j}>{part.slice(2, -2)}</strong> : <Fragment key={j}>{part}</Fragment>)}
    </Fragment>
  ))
}

export default function Assistant() {
  const [messages, setMessages] = useState([{
    role: 'assistant',
    text: "Hi! I can answer questions about your meals, calories, protein, water and workouts using your profile and today's food log. What would you like to know?",
  }])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [quick, setQuick] = useState(STARTERS)
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, busy])

  const send = async (text) => {
    const message = text.trim()
    if (!message || busy) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: message }])
    setBusy(true)
    try {
      const res = await post('/ai/chat', { message, local_date: localDate(), local_hour: new Date().getHours() })
      setMessages((m) => [...m, { role: 'assistant', text: res.reply, intent: res.intent }])
      if (res.quick_replies) setQuick(res.quick_replies)
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', text: e.message, error: true }])
    } finally { setBusy(false) }
  }

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col lg:h-[calc(100vh-4rem)]">
      <PageHeader title="Fitness assistant" subtitle="Answers use your profile and today's food log. It does not give medical advice." />

      <div className="panel flex min-h-0 flex-1 flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5" aria-live="polite">
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}>
              {m.role === 'assistant' && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white"><Bot size={17} aria-hidden /></div>
              )}
              <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed sm:max-w-[75%] ${
                m.role === 'user' ? 'rounded-br-md bg-brand-600 text-white'
                  : m.error ? 'rounded-bl-md bg-red-50 text-red-800' : 'rounded-bl-md bg-canvas'}`}>
                <RichText text={m.text} />
                {m.intent === 'medical_safety' && <p className="mt-2 text-xs font-semibold text-muted">Safety rule applied</p>}
              </div>
            </div>
          ))}
          {busy && (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white"><Bot size={17} aria-hidden /></div>
              <div className="rounded-2xl rounded-bl-md bg-canvas px-4 py-3 text-sm text-muted">Thinking…</div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <div className="border-t border-line p-3 sm:p-4">
          <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
            {quick.map((q) => (
              <button key={q} onClick={() => send(q)} disabled={busy}
                className="chip shrink-0 border border-line bg-white py-1.5 text-sm font-medium text-ink hover:border-brand-200 hover:bg-brand-50">
                {q}
              </button>
            ))}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); send(input) }} className="flex gap-2">
            <input className="input" placeholder="Ask about meals, protein, calories or workouts" value={input}
              onChange={(e) => setInput(e.target.value)} maxLength={500} aria-label="Your question" />
            <button className="btn-primary px-3.5" disabled={busy || !input.trim()} aria-label="Send"><Send size={18} /></button>
          </form>
        </div>
      </div>
      <div className="mt-3"><Disclaimer>The assistant gives general fitness and nutrition guidance only. It cannot diagnose conditions or recommend treatment. Please consult a doctor for health concerns.</Disclaimer></div>
    </div>
  )
}
