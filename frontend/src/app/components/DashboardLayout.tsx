import {
	Calendar,
	ChevronDown,
	DoorOpen,
	GraduationCap,
	Home,
	LogOut,
	Menu,
	Settings,
	Users,
	X,
} from 'lucide-react'
import { useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router'

import { clearAuth, getCurrentUser } from '../lib/api'
import { NotificationsBell } from './NotificationsBell'

export function DashboardLayout() {
	const navigate = useNavigate()
	const location = useLocation()
	const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
	const [communityExpanded, setCommunityExpanded] = useState(false)
	const user = getCurrentUser()

	const navItems = [
		{ path: '/dashboard', label: 'Overview', icon: Home },
		{ path: '/dashboard/timetable', label: 'Timetable', icon: Calendar },
		{ path: '/dashboard/rooms', label: 'Rooms & Facilities', icon: DoorOpen },
	]

	const handleLogout = () => {
		clearAuth()
		navigate('/')
	}

	const isActive = (path: string) => {
		if (path === '/dashboard') {
			return location.pathname === path
		}
		return location.pathname.startsWith(path)
	}

	return (
		<div className='flex h-screen bg-gray-50'>
			{/* Mobile Overlay */}
			{mobileMenuOpen && (
				<div
					className='fixed inset-0 bg-black/50 z-40 lg:hidden'
					onClick={() => setMobileMenuOpen(false)}
				/>
			)}

			{/* Sidebar */}
			<aside
				className={`fixed lg:static inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out ${
					mobileMenuOpen
						? 'translate-x-0'
						: '-translate-x-full lg:translate-x-0'
				}`}
			>
				<div className='flex flex-col h-full'>
					{/* Logo */}
					<div className='p-6 border-b border-gray-200 flex items-center justify-between'>
						<div className='flex items-center gap-3'>
							<div className='w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center'>
								<GraduationCap className='w-6 h-6 text-white' />
							</div>
							<span className='text-gray-900'>Portal</span>
						</div>
						<button
							onClick={() => setMobileMenuOpen(false)}
							className='lg:hidden text-gray-500 hover:text-gray-700'
						>
							<X className='w-5 h-5' />
						</button>
					</div>

					{/* Navigation */}
					<nav className='flex-1 p-4 space-y-1'>
						{navItems.map(item => {
							const Icon = item.icon
							const active = isActive(item.path)
							return (
								<button
									key={item.path}
									onClick={() => {
										navigate(item.path)
										setMobileMenuOpen(false)
									}}
									className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition ${
										active
											? 'bg-blue-50 text-blue-600'
											: 'text-gray-700 hover:bg-gray-100'
									}`}
								>
									<Icon className='w-5 h-5' />
									<span>{item.label}</span>
								</button>
							)
						})}

						{/* Community with submenu */}
						<div>
							<button
								onClick={() => setCommunityExpanded(!communityExpanded)}
								className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition ${
									location.pathname.startsWith('/dashboard/community')
										? 'bg-blue-50 text-blue-600'
										: 'text-gray-700 hover:bg-gray-100'
								}`}
							>
								<Users className='w-5 h-5' />
								<span className='flex-1 text-left'>Community & Clubss</span>
								<ChevronDown
									className={`w-4 h-4 transition-transform ${
										communityExpanded ? 'rotate-180' : ''
									}`}
								/>
							</button>
							{communityExpanded && (
								<div className='ml-12 mt-1 space-y-1'>
									<button
										onClick={() => {
											navigate('/dashboard/community')
											setMobileMenuOpen(false)
										}}
										className='w-full text-left px-4 py-2 text-gray-600 hover:text-blue-600 transition'
									>
										Clubs Directory
									</button>
									<button
										onClick={() => {
											navigate('/dashboard/community')
											setMobileMenuOpen(false)
										}}
										className='w-full text-left px-4 py-2 text-gray-600 hover:text-blue-600 transition'
									>
										Notice Board
									</button>
								</div>
							)}
						</div>
					</nav>

					{/* User Profile & Actions */}
					<div className='border-t border-gray-200 p-4 space-y-2'>
						<div className='px-4 py-3 bg-gray-50 rounded-lg'>
							<p className='text-gray-900'>{user?.full_name ?? 'Guest'}</p>
							<p className='text-gray-500 mt-0.5'>
								{user?.group ?? '—'}
								{user?.role ? ` · ${user.role}` : ''}
							</p>
						</div>
						<button className='w-full flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg transition'>
							<Settings className='w-5 h-5' />
							<span>Settings</span>
						</button>
						<button
							onClick={handleLogout}
							className='w-full flex items-center gap-3 px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg transition'
						>
							<LogOut className='w-5 h-5' />
							<span>Logout</span>
						</button>
					</div>
				</div>
			</aside>

			{/* Main Content */}
			<main className='flex-1 overflow-auto'>
				{/* Top header (notifications + mobile menu trigger) */}
				<div className='bg-white border-b border-gray-200 p-4 flex items-center gap-3 justify-between'>
					<div className='flex items-center gap-3'>
						<button
							onClick={() => setMobileMenuOpen(true)}
							className='text-gray-700 lg:hidden'
						>
							<Menu className='w-6 h-6' />
						</button>
						<div className='flex items-center gap-2 lg:hidden'>
							<div className='w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center'>
								<GraduationCap className='w-5 h-5 text-white' />
							</div>
							<span className='text-gray-900'>Portal</span>
						</div>
					</div>
					<NotificationsBell />
				</div>

				<div className='p-6 lg:p-8'>
					<Outlet />
				</div>
			</main>
		</div>
	)
}
