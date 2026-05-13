import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import { openChatSocket } from '../lib/api'

type ChatMessage = {
	author_id: string
	author_name: string
	body: string
	created_at: string
}

type Props = {
	clubId: string
	clubName: string
}

export function ChatPanel({ clubId, clubName }: Props) {
	const [messages, setMessages] = useState<ChatMessage[]>([])
	const [draft, setDraft] = useState('')
	const [connected, setConnected] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const wsRef = useRef<WebSocket | null>(null)
	const scrollRef = useRef<HTMLDivElement | null>(null)

	useEffect(() => {
		setError(null)
		setMessages([])
		const ws = openChatSocket(clubId)
		wsRef.current = ws

		ws.onopen = () => setConnected(true)
		ws.onclose = () => setConnected(false)
		ws.onerror = () => setError('WebSocket connection failed')
		ws.onmessage = ev => {
			try {
				const payload = JSON.parse(ev.data)
				if (payload.type === 'backlog') {
					setMessages(payload.messages ?? [])
				} else if (payload.type === 'message') {
					setMessages(prev => [...prev, payload])
				}
			} catch {
				// ignore malformed frames
			}
		}

		return () => {
			ws.close()
			wsRef.current = null
		}
	}, [clubId])

	useEffect(() => {
		scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
	}, [messages.length])

	const send = (e: React.FormEvent) => {
		e.preventDefault()
		const text = draft.trim()
		if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
			return
		}
		wsRef.current.send(JSON.stringify({ body: text }))
		setDraft('')
	}

	return (
		<div className='flex h-[480px] flex-col rounded-xl border border-gray-200 bg-white shadow-sm'>
			<div className='flex items-center justify-between border-b border-gray-100 px-4 py-3'>
				<div>
					<h3 className='text-gray-900'>#{clubName}</h3>
					<p className='text-xs text-gray-500'>
						{connected ? 'Live' : 'Connecting…'}
					</p>
				</div>
				<span
					className={`h-2 w-2 rounded-full ${
						connected ? 'bg-green-500' : 'bg-gray-300'
					}`}
				/>
			</div>

			{error && (
				<div className='border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700'>
					{error}
				</div>
			)}

			<div ref={scrollRef} className='flex-1 overflow-y-auto px-4 py-3 space-y-2'>
				{messages.length === 0 && (
					<p className='text-center text-sm text-gray-400 py-8'>
						No messages yet. Be the first to say hi.
					</p>
				)}
				{messages.map((m, i) => (
					<div key={i} className='rounded-lg bg-gray-50 px-3 py-2'>
						<p className='text-xs text-gray-500'>
							{m.author_name} ·{' '}
							{new Date(m.created_at).toLocaleTimeString()}
						</p>
						<p className='text-gray-900'>{m.body}</p>
					</div>
				))}
			</div>

			<form onSubmit={send} className='flex gap-2 border-t border-gray-100 p-3'>
				<input
					value={draft}
					onChange={e => setDraft(e.target.value)}
					placeholder='Type a message…'
					className='flex-1 rounded-lg border border-gray-200 px-3 py-2 outline-none focus:border-blue-500'
				/>
				<button
					type='submit'
					disabled={!connected || !draft.trim()}
					className='rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1'
				>
					<Send className='w-4 h-4' />
					Send
				</button>
			</form>
		</div>
	)
}
