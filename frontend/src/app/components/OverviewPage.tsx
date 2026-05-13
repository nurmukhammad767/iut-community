import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { Bell, Calendar, Clock } from 'lucide-react'
import {
	ApiError,
	DashboardResponse,
	fetchDashboard,
} from '../lib/api'

function formatDueDate(iso: string): string {
	const d = new Date(iso)
	return d.toLocaleDateString(undefined, {
		month: 'short',
		day: 'numeric',
		year: 'numeric',
	})
}

function isUrgent(iso: string): boolean {
	const due = new Date(iso).getTime()
	const now = Date.now()
	return due - now < 1000 * 60 * 60 * 72 // < 72h
}

export function OverviewPage() {
	const navigate = useNavigate()
	const [data, setData] = useState<DashboardResponse | null>(null)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		fetchDashboard()
			.then(setData)
			.catch(err => {
				if (err instanceof ApiError && err.status === 401) {
					navigate('/')
					return
				}
				setError(err instanceof Error ? err.message : 'Failed to load')
			})
	}, [navigate])

	const upcoming = data?.upcoming_assignments ?? []
	const clubs = data?.my_clubs ?? []

	const nextDeadline = upcoming[0]

	return (
		<div className='space-y-6'>
			<div>
				<h1 className='text-gray-900'>Overview</h1>
				<p className='text-muted-foreground mt-1'>
					{data
						? `Welcome back, ${data.full_name} (${data.group})`
						: 'Your academic command center'}
				</p>
			</div>

			{error && (
				<div className='rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700'>
					{error}
				</div>
			)}

			<div className='bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl p-6 lg:p-8 text-white shadow-xl'>
				<div className='flex items-start justify-between'>
					<div className='space-y-1'>
						<p className='text-blue-100'>Next Deadline</p>
						<h2 className='text-white mt-2'>
							{nextDeadline
								? `${nextDeadline.title} — ${nextDeadline.course_code}`
								: 'No upcoming deadlines 🎉'}
						</h2>
					</div>
					<div className='bg-white/20 backdrop-blur p-3 rounded-xl'>
						<Clock className='w-6 h-6' />
					</div>
				</div>
				{nextDeadline && (
					<div className='flex flex-wrap gap-4 mt-6'>
						<div className='flex items-center gap-2'>
							<Calendar className='w-5 h-5 text-blue-200' />
							<span>Due {formatDueDate(nextDeadline.due_date)}</span>
						</div>
					</div>
				)}
			</div>

			<div className='grid lg:grid-cols-2 gap-6'>
				<div className='bg-white rounded-xl border border-gray-200 p-6 shadow-sm'>
					<div className='flex items-center justify-between mb-4'>
						<h3 className='text-gray-900'>Upcoming Deadlines</h3>
						<Bell className='w-5 h-5 text-gray-400' />
					</div>
					<div className='space-y-3'>
						{upcoming.map(a => (
							<div
								key={a.id}
								className='flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition border border-gray-100'
							>
								<div
									className={`w-2 h-2 rounded-full mt-2 ${
										isUrgent(a.due_date) ? 'bg-red-500' : 'bg-blue-500'
									}`}
								/>
								<div className='flex-1 min-w-0'>
									<p className='text-gray-900'>{a.title}</p>
									<p className='text-gray-500 mt-0.5'>
										{a.course_code} — {a.course_name}
									</p>
									<p
										className={`mt-1 ${
											isUrgent(a.due_date) ? 'text-red-600' : 'text-gray-600'
										}`}
									>
										Due: {formatDueDate(a.due_date)}
									</p>
								</div>
							</div>
						))}
					</div>
					{upcoming.length === 0 && (
						<div className='text-center py-8 text-gray-500'>
							<Calendar className='w-12 h-12 mx-auto mb-2 text-gray-300' />
							<p>No upcoming deadlines 🎉</p>
						</div>
					)}
				</div>

				<div className='bg-white rounded-xl border border-gray-200 p-6 shadow-sm'>
					<div className='flex items-center justify-between mb-4'>
						<h3 className='text-gray-900'>My Clubs</h3>
						<Bell className='w-5 h-5 text-gray-400' />
					</div>
					<div className='space-y-3'>
						{clubs.map(c => (
							<div
								key={c.id}
								className='p-3 rounded-lg hover:bg-gray-50 transition border border-gray-100'
							>
								<p className='text-gray-900'>{c.name}</p>
								<p className='text-gray-500 mt-1 line-clamp-2'>
									{c.description}
								</p>
							</div>
						))}
						{clubs.length === 0 && (
							<p className='text-gray-500 py-4 text-center'>
								You haven&apos;t joined any clubs yet.
							</p>
						)}
					</div>
				</div>
			</div>
		</div>
	)
}
