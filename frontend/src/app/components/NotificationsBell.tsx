import { Bell, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import {
	ackNotification,
	clearNotifications,
	getToken,
	listNotifications,
	openNotificationsSocket,
	type Notification,
} from '../lib/api'

const POLL_INTERVAL_MS = 30_000

export function NotificationsBell() {
	const [notifications, setNotifications] = useState<Notification[]>([])
	const [open, setOpen] = useState(false)
	const socketRef = useRef<WebSocket | null>(null)

	const refresh = useCallback(async () => {
		try {
			const res = await listNotifications()
			setNotifications(res.notifications)
		} catch {
			// 401 already clears auth in api.ts; silent fail otherwise
		}
	}, [])

	useEffect(() => {
		if (!getToken()) return
		refresh()
		const interval = setInterval(refresh, POLL_INTERVAL_MS)
		return () => clearInterval(interval)
	}, [refresh])

	useEffect(() => {
		if (!getToken()) return
		const ws = openNotificationsSocket()
		socketRef.current = ws
		ws.onmessage = ev => {
			try {
				const data = JSON.parse(ev.data)
				if (data.type === 'backlog' && Array.isArray(data.notifications)) {
					setNotifications(prev => mergeUnique(prev, data.notifications))
				} else if (data.type === 'lesson_reminder') {
					setNotifications(prev => mergeUnique(prev, [data]))
				}
			} catch {
				// ignore malformed payloads
			}
		}
		ws.onclose = () => {
			socketRef.current = null
		}
		return () => {
			ws.close()
			socketRef.current = null
		}
	}, [])

	const handleAck = async (id: string) => {
		try {
			await ackNotification(id)
		} catch {
			// ignore: still drop locally so UI matches
		}
		setNotifications(prev => prev.filter(n => n.id !== id))
	}

	const handleClear = async () => {
		try {
			await clearNotifications()
		} catch {
			// ignore
		}
		setNotifications([])
	}

	const unread = notifications.length

	return (
		<div className='relative'>
			<button
				onClick={() => setOpen(o => !o)}
				className='relative p-2 rounded-lg hover:bg-gray-100 transition'
				aria-label='Notifications'
			>
				<Bell className='w-5 h-5 text-gray-700' />
				{unread > 0 && (
					<span className='absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center'>
						{unread}
					</span>
				)}
			</button>

			{open && (
				<div className='absolute right-0 mt-2 w-80 max-h-96 overflow-auto bg-white border border-gray-200 rounded-lg shadow-lg z-50'>
					<div className='flex items-center justify-between p-3 border-b border-gray-200'>
						<span className='text-gray-900'>Lesson reminders</span>
						{unread > 0 && (
							<button
								onClick={handleClear}
								className='text-xs text-gray-500 hover:text-red-600'
							>
								Clear all
							</button>
						)}
					</div>
					{unread === 0 ? (
						<p className='p-4 text-center text-gray-500 text-sm'>
							You're all caught up.
						</p>
					) : (
						<ul className='divide-y divide-gray-100'>
							{notifications.map(n => (
								<li key={n.id} className='p-3 flex gap-2'>
									<div className='flex-1 min-w-0'>
										<p className='text-gray-900 truncate'>{n.subject}</p>
										<p className='text-xs text-gray-500 mt-0.5'>
											Period {n.period} · starts in {n.minutes_until} min
										</p>
										{n.rooms?.length > 0 && (
											<p className='text-xs text-gray-500'>
												Room {n.rooms.join(', ')}
											</p>
										)}
									</div>
									<button
										onClick={() => handleAck(n.id)}
										className='text-gray-400 hover:text-red-500'
										aria-label='Dismiss'
									>
										<X className='w-4 h-4' />
									</button>
								</li>
							))}
						</ul>
					)}
				</div>
			)}
		</div>
	)
}

function mergeUnique(prev: Notification[], incoming: Notification[]): Notification[] {
	const seen = new Set(prev.map(n => n.id))
	const merged = [...prev]
	for (const n of incoming) {
		if (!n?.id || seen.has(n.id)) continue
		merged.unshift(n)
		seen.add(n.id)
	}
	return merged
}
