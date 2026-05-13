import { BookOpen, Clock, MapPin, RotateCcw, User, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import {
	dropSubject,
	fetchMySessions,
	listMyDrops,
	undropSubject,
	type DropRecord,
	type TimetableSession,
} from '../lib/api'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'] as const
const PERIOD_TIMES: Record<string, string> = {
	'1': '09:30',
	'2': '10:00',
	'3': '10:30',
	'4': '11:00',
	'5': '11:30',
	'6': '12:00',
	'7': '12:30',
	'8': '13:00',
	'9': '13:30',
}

function dayMaskFor(day: string): string {
	const idx = DAYS.indexOf(day as (typeof DAYS)[number])
	if (idx < 0) return '00000'
	return DAYS.map((_, i) => (i === idx ? '1' : '0')).join('')
}

function compositeKey(dayMask: string, period: string, subject: string): string {
	return `${dayMask}|${period}|${subject}`
}

export function TimetablePage() {
	const [sessions, setSessions] = useState<TimetableSession[]>([])
	const [drops, setDrops] = useState<DropRecord[]>([])
	const [group, setGroup] = useState<string>('')
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [busyKey, setBusyKey] = useState<string | null>(null)
	const [selected, setSelected] = useState<{
		session: TimetableSession
		day: string
	} | null>(null)

	const refresh = useCallback(async () => {
		setLoading(true)
		setError(null)
		try {
			const [s, d] = await Promise.all([fetchMySessions(), listMyDrops()])
			setSessions(s.sessions)
			setGroup(s.group)
			setDrops(d.drops)
		} catch (e) {
			setError(e instanceof Error ? e.message : 'Failed to load timetable')
		} finally {
			setLoading(false)
		}
	}, [])

	useEffect(() => {
		refresh()
	}, [refresh])

	const sessionsByDay = useMemo(() => {
		const map: Record<string, { session: TimetableSession; dayMask: string }[]> =
			{}
		for (const day of DAYS) map[day] = []
		for (const s of sessions) {
			for (const d of s.days) {
				if (!map[d]) continue
				map[d].push({ session: s, dayMask: dayMaskFor(d) })
			}
		}
		for (const day of DAYS) {
			map[day].sort((a, b) =>
				Number(a.session.period) - Number(b.session.period)
			)
		}
		return map
	}, [sessions])

	const handleDrop = async (session: TimetableSession, day: string) => {
		const dayMask = dayMaskFor(day)
		const key = compositeKey(dayMask, session.period, session.subject)
		setBusyKey(key)
		try {
			await dropSubject({
				day_mask: dayMask,
				period: session.period,
				subject: session.subject,
			})
			await refresh()
			setSelected(null)
		} catch (e) {
			setError(e instanceof Error ? e.message : 'Drop failed')
		} finally {
			setBusyKey(null)
		}
	}

	const handleUndrop = async (drop: DropRecord) => {
		const key = compositeKey(drop.day_mask, drop.period, drop.subject)
		setBusyKey(key)
		try {
			await undropSubject({
				day_mask: drop.day_mask,
				period: drop.period,
				subject: drop.subject,
			})
			await refresh()
		} catch (e) {
			setError(e instanceof Error ? e.message : 'Undo failed')
		} finally {
			setBusyKey(null)
		}
	}

	return (
		<div className='space-y-6'>
			<div>
				<h1 className='text-gray-900'>My Timetable</h1>
				<p className='text-muted-foreground mt-1'>
					{group ? `Group ${group}` : 'Your weekly schedule'}
				</p>
			</div>

			{error && (
				<div className='p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg'>
					{error}
				</div>
			)}

			{loading ? (
				<div className='text-center py-12 bg-white rounded-xl border border-gray-200'>
					<p className='text-gray-500'>Loading…</p>
				</div>
			) : (
				<>
					<div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5'>
						{DAYS.map(day => (
							<div
								key={day}
								className='bg-white rounded-xl border border-gray-200 p-4'
							>
								<p className='text-gray-900 mb-3'>{day}</p>
								{sessionsByDay[day].length === 0 ? (
									<p className='text-gray-400 text-sm'>—</p>
								) : (
									<ul className='space-y-2'>
										{sessionsByDay[day].map(({ session }) => (
											<li key={`${day}-${session.period}-${session.subject}`}>
												<button
													onClick={() => setSelected({ session, day })}
													className='w-full text-left p-3 rounded-lg border border-blue-200 bg-blue-50 hover:bg-blue-100 transition'
												>
													<p className='text-blue-900'>{session.subject}</p>
													<p className='text-xs text-blue-700 mt-0.5'>
														Period {session.period} ·{' '}
														{PERIOD_TIMES[session.period] ?? '--:--'}
													</p>
													{session.rooms?.length > 0 && (
														<p className='text-xs text-blue-700'>
															Room {session.rooms.join(', ')}
														</p>
													)}
												</button>
											</li>
										))}
									</ul>
								)}
							</div>
						))}
					</div>

					{drops.length > 0 && (
						<div className='bg-white rounded-xl border border-gray-200 p-4'>
							<p className='text-gray-900 mb-3'>Dropped subjects</p>
							<ul className='space-y-2'>
								{drops.map(d => {
									const key = compositeKey(d.day_mask, d.period, d.subject)
									return (
										<li
											key={key}
											className='flex items-center justify-between gap-2 p-3 bg-gray-50 rounded-lg'
										>
											<div>
												<p className='text-gray-900'>{d.subject}</p>
												<p className='text-xs text-gray-500'>
													Period {d.period} · mask {d.day_mask}
												</p>
											</div>
											<button
												onClick={() => handleUndrop(d)}
												disabled={busyKey === key}
												className='inline-flex items-center gap-1 px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-50 rounded'
											>
												<RotateCcw className='w-4 h-4' />
												Restore
											</button>
										</li>
									)
								})}
							</ul>
						</div>
					)}
				</>
			)}

			{selected && (
				<div
					className='fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50'
					onClick={() => setSelected(null)}
				>
					<div
						className='bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl'
						onClick={e => e.stopPropagation()}
					>
						<div className='flex items-start justify-between mb-4'>
							<div>
								<p className='text-gray-600'>{selected.day}</p>
								<h2 className='text-gray-900 mt-1'>
									{selected.session.subject}
								</h2>
							</div>
							<button
								onClick={() => setSelected(null)}
								className='text-gray-400 hover:text-gray-600 p-1'
							>
								<X className='w-5 h-5' />
							</button>
						</div>

						<div className='space-y-3'>
							<div className='flex items-center gap-3 p-3 bg-gray-50 rounded-lg'>
								<Clock className='w-5 h-5 text-blue-600' />
								<div>
									<p className='text-gray-500'>Period</p>
									<p className='text-gray-900'>
										{selected.session.period} ·{' '}
										{PERIOD_TIMES[selected.session.period] ?? '--:--'}
									</p>
								</div>
							</div>

							{selected.session.rooms?.length > 0 && (
								<div className='flex items-center gap-3 p-3 bg-gray-50 rounded-lg'>
									<MapPin className='w-5 h-5 text-blue-600' />
									<div>
										<p className='text-gray-500'>Room</p>
										<p className='text-gray-900'>
											{selected.session.rooms.join(', ')}
										</p>
									</div>
								</div>
							)}

							{selected.session.professors?.length > 0 && (
								<div className='flex items-center gap-3 p-3 bg-gray-50 rounded-lg'>
									<User className='w-5 h-5 text-blue-600' />
									<div>
										<p className='text-gray-500'>Professor</p>
										<p className='text-gray-900'>
											{selected.session.professors.join(', ')}
										</p>
									</div>
								</div>
							)}

							<div className='flex items-center gap-3 p-3 bg-gray-50 rounded-lg'>
								<BookOpen className='w-5 h-5 text-blue-600' />
								<div>
									<p className='text-gray-500'>Groups</p>
									<p className='text-gray-900'>
										{selected.session.groups.join(', ')}
									</p>
								</div>
							</div>

							<button
								onClick={() => handleDrop(selected.session, selected.day)}
								disabled={
									busyKey ===
									compositeKey(
										dayMaskFor(selected.day),
										selected.session.period,
										selected.session.subject
									)
								}
								className='w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-60 transition'
							>
								Drop this subject
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	)
}
