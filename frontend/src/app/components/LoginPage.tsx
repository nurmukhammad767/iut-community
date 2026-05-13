import { useState } from 'react'
import { useNavigate } from 'react-router'
import {
	fetchMe,
	login,
	setCurrentUser,
	setToken,
} from '../lib/api'
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
	AlertDialogTrigger,
} from './ui/alert-dialog'

export function LoginPage() {
	const navigate = useNavigate()
	const [studentId, setStudentId] = useState('')
	const [password, setPassword] = useState('')
	const [error, setError] = useState<string | null>(null)
	const [submitting, setSubmitting] = useState(false)
	const [backgroundImage] = useState(() => {
		const backgrounds = [
			'/assest/bg1.webp',
			'/assest/bg2.webp',
			'/assest/bg3.webp',
		]
		return backgrounds[Math.floor(Math.random() * backgrounds.length)]
	})
	const adminTelegramUsername = (
		import.meta as ImportMeta & {
			env: { VITE_ADMIN_TELEGRAM_USERNAME?: string }
		}
	).env.VITE_ADMIN_TELEGRAM_USERNAME
	const adminTelegramLink = adminTelegramUsername
		? `https://t.me/${adminTelegramUsername}`
		: 'https://t.me/'

	const handleLogin = async (e: React.FormEvent) => {
		e.preventDefault()
		setError(null)
		setSubmitting(true)
		try {
			const { access_token } = await login(studentId, password)
			setToken(access_token)
			const me = await fetchMe()
			setCurrentUser(me)
			navigate('/dashboard')
		} catch (err) {
			setError(err instanceof Error ? err.message : 'Login failed')
		} finally {
			setSubmitting(false)
		}
	}

	return (
		<div
			className='min-h-screen flex flex-col bg-cover bg-center bg-no-repeat'
			style={{
				backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.1), rgba(0, 0, 0, 0.1)), url(${backgroundImage})`,
			}}
		>
			<div className='flex-1 flex items-center justify-center p-4'>
				<div className='w-full max-w-md'>
					<div className='rounded-2xl border border-white/15 bg-blue-950/60 p-8 shadow-xl backdrop-blur-sm'>
						<div className='flex flex-col items-center mb-8'>
							<img
								src='/assets/logo/logo_white.png'
								alt='University Portal Logo'
								className='h-auto w-70 object-fill'
								onError={e => {
									e.currentTarget.src = '/assest/logo/logo_white.png'
								}}
							/>
						</div>

						<form onSubmit={handleLogin} className='space-y-5'>
							<div>
								<label htmlFor='studentId' className='block mb-2 text-white/90'>
									Student ID
								</label>
								<input
									id='studentId'
									type='text'
									placeholder='U1234567'
									value={studentId}
									onChange={e => setStudentId(e.target.value)}
									className='w-full rounded-lg border border-white/15 bg-white/10 px-4 py-3 text-white placeholder:text-white/60 outline-none transition focus:border-white/30 focus:ring-2 focus:ring-white/10 backdrop-blur-sm'
								/>
							</div>

							<div>
								<label htmlFor='password' className='block mb-2 text-white/90'>
									Password
								</label>
								<input
									id='password'
									type='password'
									placeholder='Enter your password'
									value={password}
									onChange={e => setPassword(e.target.value)}
									className='w-full rounded-lg border border-white/15 bg-white/10 px-4 py-3 text-white placeholder:text-white/60 outline-none transition focus:border-white/30 focus:ring-2 focus:ring-white/10 backdrop-blur-sm'
								/>
							</div>

							{error && (
								<div className='rounded-lg border border-red-300/40 bg-red-500/20 px-3 py-2 text-sm text-red-100'>
									{error}
								</div>
							)}

							<button
								type='submit'
								disabled={submitting}
								className='w-full rounded-lg border border-white/15 bg-blue-700 py-3 text-white transition hover:bg-blue-800 shadow-lg hover:shadow-xl disabled:opacity-60'
							>
								{submitting ? 'Signing in…' : 'Login'}
							</button>

							<AlertDialog>
								<AlertDialogTrigger asChild>
									<button
										type='button'
										className='w-full rounded-lg border border-white/30 bg-white py-3 text-center text-blue-700 hover:bg-white/90 whitespace-normal leading-relaxed transition shadow-md'
									>
										Contact admin on Telegram for login password
									</button>
								</AlertDialogTrigger>
								<AlertDialogContent>
									<AlertDialogHeader>
										<AlertDialogTitle>Security notice</AlertDialogTitle>
										<AlertDialogDescription>
											To keep everyone safe, please go to Telegram and request
											your login password manually from the admin account using
											the link below.
										</AlertDialogDescription>
									</AlertDialogHeader>
									<AlertDialogFooter>
										<AlertDialogCancel>Close</AlertDialogCancel>
										<AlertDialogAction asChild>
											<a
												href={adminTelegramLink}
												target='_blank'
												rel='noopener noreferrer'
												aria-disabled={!adminTelegramUsername}
												className={
													!adminTelegramUsername
														? 'pointer-events-none opacity-60'
														: ''
												}
											>
												{adminTelegramUsername
													? `Open @${adminTelegramUsername}`
													: 'Admin Telegram username is not set'}
											</a>
										</AlertDialogAction>
									</AlertDialogFooter>
								</AlertDialogContent>
							</AlertDialog>
						</form>

						{/* <div className='mt-6 text-center'>
							<a href='#' className='text-white/90 hover:underline'>
								Forgot password?
							</a>
						</div> */}
					</div>
				</div>
			</div>

			<p className='pb-4 text-center text-white/90'>
				&copy; 2026 University Portal. All rights reserved.
			</p>
		</div>
	)
}
