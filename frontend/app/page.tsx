'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Scale, ThumbsUp, ThumbsDown, Loader2, BookOpen } from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────

interface Citation {
  article: string
  document: string
  relevant_text: string
}

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  confidence?: string
  limitations?: string
  follow_up_suggestions?: string[]
  query_log_id?: number
  latency_ms?: number
  feedback?: 1 | -1
}

// ── Sample questions shown on landing ─────────────────────────────

const SAMPLE_QUESTIONS = [
  "What is the maximum probation period allowed?",
  "How many days of annual leave am I entitled to?",
  "What are notice period requirements when resigning?",
  "How is end-of-service gratuity calculated?",
  "Can my employer change my job without my consent?",
  "What are the rules around working hours and overtime?"
]

// ── Main App ──────────────────────────────────────────────────────

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage(query: string) {
    if (!query.trim() || loading) return

    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: query
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })

      const data = await response.json()

      const assistantMessage: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.answer,
        citations: data.citations || [],
        confidence: data.confidence,
        limitations: data.limitations,
        follow_up_suggestions: data.follow_up_suggestions || [],
        query_log_id: data.query_log_id,
        latency_ms: data.latency_ms
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, there was an error connecting to the server. Please make sure the backend is running.'
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  async function sendFeedback(messageId: number, queryLogId: number, rating: 1 | -1) {
    try {
      await fetch('http://localhost:8000/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query_log_id: queryLogId, rating })
      })
      setMessages(prev => prev.map(m =>
        m.id === messageId ? { ...m, feedback: rating } : m
      ))
    } catch { /* silent fail */ }
  }

  function getConfidenceColor(confidence?: string) {
    if (confidence === 'high') return 'text-green-600 bg-green-50'
    if (confidence === 'medium') return 'text-yellow-600 bg-yellow-50'
    return 'text-red-600 bg-red-50'
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3 shadow-sm">
        <div className="bg-blue-600 p-2 rounded-lg">
          <Scale className="text-white w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-gray-900 text-lg">LaborLens UAE</h1>
          <p className="text-xs text-gray-500">UAE Labor Law Intelligence Assistant</p>
        </div>
        <div className="ml-auto">
          <span className="text-xs bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full font-medium">
            ⚠️ Not legal advice
          </span>
        </div>
      </header>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto w-full">

        {/* Landing state — shown when no messages */}
        {messages.length === 0 && (
          <div className="text-center mt-12">
            <div className="bg-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <BookOpen className="text-white w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Ask about UAE Labor Law
            </h2>
            <p className="text-gray-500 mb-8 max-w-md mx-auto">
              Get answers with citations to specific articles of Federal Decree-Law No. 33 of 2021
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl mx-auto">
              {SAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  className="text-left p-3 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 hover:border-blue-400 hover:bg-blue-50 transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map(message => (
          <div
            key={message.id}
            className={`mb-6 ${message.role === 'user' ? 'flex justify-end' : ''}`}
          >
            {message.role === 'user' ? (
              <div className="bg-blue-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm max-w-lg text-sm">
                {message.content}
              </div>
            ) : (
              <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm p-5 shadow-sm">

                {/* Answer */}
                <p className="text-gray-800 text-sm leading-relaxed">{message.content}</p>

                {/* Citations */}
                {message.citations && message.citations.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Sources</p>
                    {message.citations.map((cite, i) => (
                      <div key={i} className="bg-blue-50 border border-blue-100 rounded-lg p-3">
                        <p className="text-xs font-semibold text-blue-700">{cite.article}</p>
                        <p className="text-xs text-gray-600 mt-1">{cite.relevant_text}</p>
                        <p className="text-xs text-gray-400 mt-1">{cite.document}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Limitations */}
                {message.limitations && (
                  <div className="mt-3 bg-yellow-50 border border-yellow-100 rounded-lg p-3">
                    <p className="text-xs text-yellow-700">⚠️ {message.limitations}</p>
                  </div>
                )}

                {/* Footer row: confidence, latency, feedback */}
                <div className="mt-4 flex items-center gap-3 flex-wrap">
                  {message.confidence && (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getConfidenceColor(message.confidence)}`}>
                      {message.confidence} confidence
                    </span>
                  )}
                  {message.latency_ms && (
                    <span className="text-xs text-gray-400">{message.latency_ms}ms</span>
                  )}
                  {message.query_log_id && !message.feedback && (
                    <div className="ml-auto flex gap-2">
                      <button
                        onClick={() => sendFeedback(message.id, message.query_log_id!, 1)}
                        className="text-gray-400 hover:text-green-500 transition-colors"
                        title="Helpful"
                      >
                        <ThumbsUp className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => sendFeedback(message.id, message.query_log_id!, -1)}
                        className="text-gray-400 hover:text-red-500 transition-colors"
                        title="Not helpful"
                      >
                        <ThumbsDown className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                  {message.feedback && (
                    <span className="ml-auto text-xs text-gray-400">
                      {message.feedback === 1 ? '👍 Marked helpful' : '👎 Feedback recorded'}
                    </span>
                  )}
                </div>

                {/* Follow-up suggestions */}
                {message.follow_up_suggestions && message.follow_up_suggestions.length > 0 && (
                  <div className="mt-4 space-y-1">
                    <p className="text-xs font-semibold text-gray-400">You might also ask:</p>
                    {message.follow_up_suggestions.map((suggestion, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(suggestion)}
                        className="block text-left text-xs text-blue-600 hover:underline"
                      >
                        → {suggestion}
                      </button>
                    ))}
                  </div>
                )}

              </div>
            )}
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm p-4 shadow-sm max-w-xs">
            <div className="flex items-center gap-2 text-gray-500 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              Searching UAE labor law...
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-3xl mx-auto flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                sendMessage(input)
              }
            }}
            placeholder="Ask about UAE labor law... (Enter to send)"
            className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-h-[48px] max-h-32"
            rows={1}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white p-3 rounded-xl transition-colors flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-center text-xs text-gray-400 mt-2">
          This tool surfaces UAE labor law for informational purposes only. Not legal advice.
        </p>
      </div>

    </div>
  )
}