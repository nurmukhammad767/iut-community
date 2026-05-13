// API client wrapper.
//
// All requests go through the nginx gateway at VITE_API_BASE_URL.
// JWT is stored in localStorage and attached as Authorization: Bearer <token>.

const API_BASE_URL =
	(import.meta as ImportMeta & { env: { VITE_API_BASE_URL?: string } }).env
		.VITE_API_BASE_URL ?? 'http://localhost'

const WS_BASE_URL =
	(import.meta as ImportMeta & { env: { VITE_WS_BASE_URL?: string } }).env
		.VITE_WS_BASE_URL ?? 'ws://localhost'

const TOKEN_KEY = 'iut.jwt'
const USER_KEY = 'iut.user'

export type AuthenticatedUser = {
	student_id: string
	full_name: string
	group: string
	role: string
}

export function getToken(): string | null {
	return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
	localStorage.setItem(TOKEN_KEY, token)
}

export function clearAuth(): void {
	localStorage.removeItem(TOKEN_KEY)
	localStorage.removeItem(USER_KEY)
}

export function getCurrentUser(): AuthenticatedUser | null {
	const raw = localStorage.getItem(USER_KEY)
	return raw ? (JSON.parse(raw) as AuthenticatedUser) : null
}

export function setCurrentUser(user: AuthenticatedUser): void {
	localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export class ApiError extends Error {
	constructor(public status: number, message: string) {
		super(message)
	}
}

async function request<T>(
	path: string,
	options: RequestInit = {}
): Promise<T> {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...((options.headers as Record<string, string>) ?? {}),
	}
	const token = getToken()
	if (token) headers.Authorization = `Bearer ${token}`

	const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })

	if (res.status === 401) {
		clearAuth()
		throw new ApiError(401, 'Unauthorized')
	}
	if (!res.ok) {
		let detail = `HTTP ${res.status}`
		try {
			const body = await res.json()
			detail = body.detail ?? detail
		} catch {
			// ignore non-JSON body
		}
		throw new ApiError(res.status, detail)
	}
	if (res.status === 204) return undefined as T
	return (await res.json()) as T
}

// ---------- Auth ----------

export async function login(
	student_id: string,
	password: string
): Promise<{ access_token: string; token_type: string }> {
	return request('/login', {
		method: 'POST',
		body: JSON.stringify({ student_id, password }),
	})
}

export async function fetchMe(): Promise<AuthenticatedUser> {
	return request('/me')
}

// ---------- Dashboard ----------

export type DashboardResponse = {
	student_id: string
	full_name: string
	group: string
	enrolled_courses: { id: string; code: string; name: string }[]
	upcoming_assignments: {
		id: string
		course_code: string
		course_name: string
		title: string
		due_date: string
		status: string
	}[]
	my_bookings: {
		id: string
		room_name: string
		day: string
		start_period: number
		end_period: number
		status: string
		booked_at: string
	}[]
	my_clubs: { id: string; name: string; description: string }[]
}

export async function fetchDashboard(): Promise<DashboardResponse> {
	return request('/dashboard')
}

// ---------- Clubs & Posts ----------

export type Club = {
	id: string
	name: string
	description: string
	image_url?: string | null
	created_at?: string
}

export async function listClubs(): Promise<Club[]> {
	return request('/clubs')
}

export async function joinClub(clubId: string): Promise<void> {
	await request(`/clubs/${clubId}/join`, { method: 'POST' })
}

export type Post = {
	id: string
	club_id: string
	author_id: string
	author_name: string
	body: string
	created_at: string
}

export async function listPosts(clubId: string): Promise<Post[]> {
	return request(`/clubs/${clubId}/posts`)
}

export async function createPost(clubId: string, body: string): Promise<Post> {
	return request(`/clubs/${clubId}/posts`, {
		method: 'POST',
		body: JSON.stringify({ body }),
	})
}

// ---------- Bookings ----------

export type Booking = {
	id: string
	room_name: string
	day: string
	start_period: number
	end_period: number
	status: string
	booked_at: string
}

export async function listMyBookings(): Promise<Booking[]> {
	return request('/bookings')
}

export async function createBooking(payload: {
	room_name: string
	day: string
	start_period: number
	end_period: number
}): Promise<Booking> {
	return request('/bookings', {
		method: 'POST',
		body: JSON.stringify(payload),
	})
}

// ---------- My timetable + drops ----------

export type TimetableSession = {
	period: string
	subject: string
	professors: string[]
	groups: string[]
	rooms: string[]
	days: string[]
}

export type MySessionsResponse = {
	group: string
	total_sessions: number
	dropped_count: number
	sessions: TimetableSession[]
}

export type DropPayload = {
	day_mask: string
	period: string
	subject: string
}

export type DropRecord = DropPayload & {
	student_id: string
	student_identifier: string
	full_name: string
	group: string
	role: string
	dropped_at: string
}

export async function fetchMySessions(): Promise<MySessionsResponse> {
	return request('/timetable/my/sessions')
}

export async function listMyDrops(): Promise<{ total: number; drops: DropRecord[] }> {
	return request('/timetable/my/drops')
}

export async function dropSubject(payload: DropPayload): Promise<{ message: string; drop: DropRecord }> {
	return request('/timetable/my/drops', {
		method: 'POST',
		body: JSON.stringify(payload),
	})
}

export async function undropSubject(payload: DropPayload): Promise<void> {
	await request('/timetable/my/drops', {
		method: 'DELETE',
		body: JSON.stringify(payload),
	})
}

// ---------- Notifications ----------

export type Notification = {
	id: string
	type: string
	subject: string
	period: string
	start_time: string
	rooms: string[]
	professors: string[]
	minutes_until: number
	created_at: string
}

export async function listNotifications(): Promise<{ total: number; notifications: Notification[] }> {
	return request('/notifications')
}

export async function ackNotification(notificationId: string): Promise<void> {
	await request(`/notifications/ack/${notificationId}`, { method: 'POST' })
}

export async function clearNotifications(): Promise<void> {
	await request('/notifications', { method: 'DELETE' })
}

// ---------- WebSocket chat ----------

export function openChatSocket(clubId: string): WebSocket {
	const token = getToken() ?? ''
	return new WebSocket(
		`${WS_BASE_URL}/ws/chat/${clubId}?token=${encodeURIComponent(token)}`
	)
}

// ---------- WebSocket notifications (live push) ----------

export function openNotificationsSocket(): WebSocket {
	const token = getToken() ?? ''
	return new WebSocket(
		`${WS_BASE_URL}/ws/notifications?token=${encodeURIComponent(token)}`
	)
}
