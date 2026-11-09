import { Fragment, useEffect, useRef, useState } from 'react'
import { Bot, ExternalLink, Send, Sparkles } from 'lucide-react'
import { get, localDate, post } from '../api/client'
import { Disclaimer, PageHeader } from '../components/ui'

const STARTERS = [
  'What should I eat for dinner?',
  'How much protein do I need today?',
  'Suggest a high-protein vegetarian breakfast.',
  'What workout should I do today?',
  'I have 500 calories remaining. What can I eat?',
  'How is my progress?',
]
const LLM_STARTERS = [
  'What should I eat for dinner?',
  'Is creatine safe, and how much should I take?',
  'How do I make high-protein paneer bhurji?',
  'Why am I not losing weight?',
  'What workout should I do today?',
  'How much protein do I need today?',
]

/** Inline formatting: **bold** and [links](https://...). */
function Inline({ text }) {
  return text.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\(https?:\/\/[^)\s]+\))/g).map((part, j) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={j}>{part.slice(2, -2)}</strong>
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/)
    if (link) return <a key={j} href={link[2]} target="_blank" rel="noreferrer" className="font-semibold text-brand-700 underline">{link[1]}</a>
    return <Fragment key={j}>{part}</Fragment>
  })
}

/** Renders the assistant's replies: paragraphs, "- " or "1. " lists, **bold** and links. */
function RichText({ text }) {
  const blocks = []
  for (const raw of text.split('\n')) {
    const line = raw.trimEnd()
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/)
    const numbered = line.match(/^\s*(\d+)[.)]\s+(.*)$/)
    const last = blocks[blocks.length - 1]
    if (bullet || numbered) {
      const kind = bullet ? 'ul' : 'ol'
      const item = bullet ? bullet[1] : numbered[2]
      if (last?.kind === kind) last.items.push(item)
      else blocks.push({ kind, items: [item] })
    } else if (!line.trim()) {
      blocks.push({ kind: 'gap' })
    } else if (last?.kind === 'p') {
      last.lines.push(line)
    } else {
      blocks.push({ kind: 'p', lines: [line] })
    }
  }
  return blocks.map((b, i) => {
    if (b.kind === 'gap') return null
    if (b.kind === 'p') {
      return (
        <p key={i} className={i > 0 ? 'mt-2' : ''}>
          {b.lines.map((l, j) => <Fragment key={j}>{j > 0 && <br />}<Inline text={l} /></Fragment>)}
        </p>
      )
    }
    const List = b.kind
    return (
      <List key={i} className={`${i > 0 ? 'mt-2' : ''} space-y-1 pl-5 ${b.kind === 'ul' ? 'list-disc' : 'list-decimal'}`}>
        {b.items.map((it, j) => <li key={j}><Inline text={it} /></li>)}
      </List>
    )
  })
}

export default function Assistant() {
  const [messages, setMessages] = useState([{
    role: 'assistant', greeting: true,
    text: "Hi! Ask me anything about food, fitness or your day. I use your profile and today's food log to answer questions about meals, calories, protein, water and workouts.",
  }])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [engine, setEngine] = useState(null)
  const [quick, setQuick] = useState(STARTERS)
  // Conversation memory for the offline assistant (meal slot, ingredients to avoid, meals already shown)
  const [context, setContext] = useState(null)
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, busy])
  useEffect(() => {
    get('/ai/status').then((s) => {
      setEngine(s)
      if (s.mode === 'llm') setQuick(LLM_STARTERS)
    }).catch(() => setEngine({ mode: 'offline', name: 'Offline assistant' }))
  }, [])

  const send = async (text) => {
    const message = text.trim()
    if (!message || busy) return
    // Earlier turns go with the question so the AI can follow the conversation
    const history = messages.filter((m) => !m.error && !m.greeting).slice(-12).map((m) => ({ role: m.role, text: m.text }))
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: message }])
    setBusy(true)
    try {
      const res = await post('/ai/chat', {
        message, context, history, local_date: localDate(), local_hour: new Date().getHours(),
      })
      setMessages((m) => [...m, {
        role: 'assistant', text: res.reply, intent: res.intent, source: res.source,
        sourceName: res.source_name, links: res.sources || [], llmError: res.llm_error,
      }])
      setContext(res.context || null)
      if (res.source === 'offline' && res.quick_replies) setQuick(res.quick_replies)
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', text: e.message, error: true }])
    } finally { setBusy(false) }
  }

  const llmOn = engine?.mode === 'llm'
  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col lg:h-[calc(100vh-4rem)]">
      <PageHeader title="Fitness assistant"
        subtitle={llmOn
          ? `Powered by ${engine.name}. Ask anything; answers about your day use your profile and food log.`
          : "Answers use your profile and today's food log. It does not give medical advice."}
        actions={engine && (
          <span className={`chip ${llmOn ? 'bg-brand-50 text-brand-700' : 'bg-black/5 text-muted'}`}
            title={llmOn ? `Model: ${engine.model}` : 'Add an AI API key in backend/.env to answer any question'}>
            <Sparkles size={13} aria-hidden /> {llmOn ? engine.name : 'Offline assistant'}
          </span>
        )} />

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
                {m.role === 'user' ? m.text : <RichText text={m.text} />}
                {m.links?.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    {m.links.map((l) => (
                      <a key={l.url} href={l.url} target="_blank" rel="noreferrer"
                        className="chip max-w-[220px] border border-line bg-white text-ink hover:border-brand-200">
                        <ExternalLink size={12} aria-hidden /><span className="truncate">{l.title}</span>
                      </a>
                    ))}
                  </div>
                )}
                {m.intent === 'medical_safety' && <p className="mt-2 text-xs font-semibold text-muted">Safety rule applied</p>}
                {llmOn && m.source === 'offline' && (
                  <p className="mt-2 text-xs text-muted">
                    The AI service didn't answer{m.llmError ? `: ${m.llmError}` : ''}. The offline assistant replied instead.
                  </p>
                )}
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
            <input className="input" placeholder={llmOn ? 'Ask me anything' : 'Ask about meals, protein, calories or workouts'} value={input}
              onChange={(e) => setInput(e.target.value)} maxLength={1000} aria-label="Your question" />
            <button className="btn-primary px-3.5" disabled={busy || !input.trim()} aria-label="Send"><Send size={18} /></button>
          </form>
        </div>
      </div>
      <div className="mt-3"><Disclaimer>The assistant gives general fitness and nutrition guidance only. It cannot diagnose conditions or recommend treatment. Please consult a doctor for health concerns. AI answers can be wrong, so check anything important.</Disclaimer></div>
    </div>
  )
}
