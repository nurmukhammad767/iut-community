import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import {
	MessageSquare,
	Search,
	Send,
	Users,
} from 'lucide-react'
import {
	ApiError,
	Club,
	Post,
	createPost,
	joinClub,
	listClubs,
	listPosts,
} from '../lib/api'
import { ChatPanel } from './ChatPanel'

export function CommunityPage() {
	const navigate = useNavigate()
	const [activeTab, setActiveTab] = useState<'clubs' | 'board' | 'chat'>(
		'clubs'
	)
	const [searchQuery, setSearchQuery] = useState('')
	const [clubs, setClubs] = useState<Club[]>([])
	const [error, setError] = useState<string | null>(null)
	const [selectedClub, setSelectedClub] = useState<Club | null>(null)
	const [posts, setPosts] = useState<Post[]>([])
	const [draft, setDraft] = useState('')
	const [posting, setPosting] = useState(false)

	useEffect(() => {
		listClubs()
			.then(setClubs)
			.catch(err => {
				if (err instanceof ApiError && err.status === 401) {
					navigate('/')
					return
				}
				setError(err instanceof Error ? err.message : 'Failed to load clubs')
			})
	}, [navigate])

	useEffect(() => {
		if (!selectedClub) {
			setPosts([])
			return
		}
		listPosts(selectedClub.id)
			.then(setPosts)
			.catch(() => setPosts([]))
	}, [selectedClub])

	const filteredClubs = clubs.filter(c =>
		c.name.toLowerCase().includes(searchQuery.toLowerCase())
	)

	const handleJoin = async (club: Club) => {
		try {
			await joinClub(club.id)
		} catch (err) {
			if (err instanceof ApiError && err.status === 409) {
				// already a member — fine
			} else {
				setError(err instanceof Error ? err.message : 'Join failed')
				return
			}
		}
		setSelectedClub(club)
		setActiveTab('board')
	}

	const handlePost = async (e: React.FormEvent) => {
		e.preventDefault()
		if (!selectedClub || !draft.trim()) return
		setPosting(true)
		setError(null)
		try {
			const newPost = await createPost(selectedClub.id, draft.trim())
			setPosts(prev => [newPost, ...prev])
			setDraft('')
		} catch (err) {
			if (err instanceof ApiError && err.status === 429) {
				setError('Too many posts — slow down a bit.')
			} else {
				setError(err instanceof Error ? err.message : 'Post failed')
			}
		} finally {
			setPosting(false)
		}
	}

	return (
		<div className='space-y-6'>
			<div>
				<h1 className='text-gray-900'>Community & Clubs</h1>
				<p className='text-muted-foreground mt-1'>
					Connect with fellow students
				</p>
			</div>

			{error && (
				<div className='rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700'>
					{error}
				</div>
			)}

			<div className='flex gap-2 border-b border-gray-200'>
				<button
					onClick={() => setActiveTab('clubs')}
					className={`px-4 py-3 border-b-2 transition ${
						activeTab === 'clubs'
							? 'border-blue-600 text-blue-600'
							: 'border-transparent text-gray-600 hover:text-gray-900'
					}`}
				>
					Clubs Directory
				</button>
				<button
					onClick={() => setActiveTab('board')}
					disabled={!selectedClub}
					className={`px-4 py-3 border-b-2 transition disabled:opacity-40 ${
						activeTab === 'board'
							? 'border-blue-600 text-blue-600'
							: 'border-transparent text-gray-600 hover:text-gray-900'
					}`}
				>
					Notice Board
				</button>
				<button
					onClick={() => setActiveTab('chat')}
					disabled={!selectedClub}
					className={`px-4 py-3 border-b-2 transition disabled:opacity-40 ${
						activeTab === 'chat'
							? 'border-blue-600 text-blue-600'
							: 'border-transparent text-gray-600 hover:text-gray-900'
					}`}
				>
					Live Chat
				</button>
			</div>

			{activeTab === 'clubs' && (
				<>
					<div className='relative'>
						<Search className='absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400' />
						<input
							value={searchQuery}
							onChange={e => setSearchQuery(e.target.value)}
							placeholder='Search clubs…'
							className='w-full pl-10 pr-4 py-3 rounded-lg border border-gray-200 outline-none focus:border-blue-500'
						/>
					</div>
					<div className='grid md:grid-cols-2 lg:grid-cols-3 gap-4'>
						{filteredClubs.map(club => (
							<div
								key={club.id}
								className='rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition'
							>
								<h3 className='text-gray-900'>{club.name}</h3>
								<p className='text-gray-600 text-sm mt-2 line-clamp-3'>
									{club.description}
								</p>
								<button
									onClick={() => handleJoin(club)}
									className='mt-4 w-full rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 flex items-center justify-center gap-2'
								>
									<Users className='w-4 h-4' /> Join & open
								</button>
							</div>
						))}
						{filteredClubs.length === 0 && (
							<p className='text-gray-500 col-span-full py-8 text-center'>
								No clubs match your search.
							</p>
						)}
					</div>
				</>
			)}

			{activeTab === 'board' && selectedClub && (
				<div className='space-y-4'>
					<div className='rounded-xl border border-gray-200 bg-white p-5'>
						<h3 className='text-gray-900'>{selectedClub.name}</h3>
						<p className='text-gray-500 text-sm'>{selectedClub.description}</p>
					</div>

					<form
						onSubmit={handlePost}
						className='rounded-xl border border-gray-200 bg-white p-4'
					>
						<textarea
							value={draft}
							onChange={e => setDraft(e.target.value)}
							placeholder={`Share something with ${selectedClub.name}…`}
							rows={3}
							className='w-full rounded-lg border border-gray-200 px-3 py-2 outline-none focus:border-blue-500 resize-none'
						/>
						<div className='flex justify-end mt-2'>
							<button
								type='submit'
								disabled={posting || !draft.trim()}
								className='rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1'
							>
								<Send className='w-4 h-4' />
								{posting ? 'Posting…' : 'Post'}
							</button>
						</div>
					</form>

					<div className='space-y-3'>
						{posts.map(p => (
							<div
								key={p.id}
								className='rounded-xl border border-gray-200 bg-white p-4'
							>
								<div className='flex items-center justify-between'>
									<p className='text-gray-900'>{p.author_name}</p>
									<p className='text-xs text-gray-400'>
										{new Date(p.created_at).toLocaleString()}
									</p>
								</div>
								<p className='text-gray-700 mt-2 whitespace-pre-wrap'>
									{p.body}
								</p>
							</div>
						))}
						{posts.length === 0 && (
							<div className='text-center py-12 text-gray-500'>
								<MessageSquare className='w-12 h-12 mx-auto mb-2 text-gray-300' />
								<p>No posts yet — start the conversation.</p>
							</div>
						)}
					</div>
				</div>
			)}

			{activeTab === 'chat' && selectedClub && (
				<ChatPanel clubId={selectedClub.id} clubName={selectedClub.name} />
			)}
		</div>
	)
}
