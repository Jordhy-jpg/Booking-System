<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

const apiBase = import.meta.env.VITE_API_URL || '/api'
const steps = ['Choose room', 'Find a time', 'Your details', 'Confirm']
const step = ref(1)
const screen = ref('booking')
const authMode = ref('login')
const session = ref(null)
try { session.value = JSON.parse(localStorage.getItem('workroom-session') || 'null') } catch { localStorage.removeItem('workroom-session') }
const authForm = reactive({ username: '', email: '', password: '' })
const authError = ref('')
const authBusy = ref(false)
const myBookings = ref([])
const bookingsLoading = ref(false)
const rooms = ref([])
const slots = ref([])
const loading = ref(false)
const submitting = ref(false)
const error = ref('')
const bookingCode = ref('')
const form = reactive({ room: null, date: '', slot: null, name: '', email: '', phone: '', participants: 1 })

const selectedRoom = computed(() => rooms.value.find((room) => room.id === form.room))
const selectedSlot = computed(() => slots.value.find((slot) => slot.id === form.slot))
const today = new Date().toISOString().slice(0, 10)
const formattedDate = computed(() => form.date ? new Intl.DateTimeFormat('en', { dateStyle: 'full' }).format(new Date(`${form.date}T00:00:00`)) : '—')
const price = computed(() => selectedRoom.value ? new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(selectedRoom.value.pricePerHour) : '—')
const canContinue = computed(() => {
  if (step.value === 1) return Boolean(form.room)
  if (step.value === 2) return Boolean(form.date && form.slot)
  if (step.value === 3) return form.name.trim().length > 1 && /^\S+@\S+\.\S+$/.test(form.email) && /^\+?[0-9\s-]{9,15}$/.test(form.phone) && form.participants > 0 && form.participants <= selectedRoom.value?.capacity
  return true
})

async function request(path, options) {
  const headers = new Headers(options?.headers || {})
  if (session.value?.access && !path.startsWith('/auth/')) headers.set('Authorization', `Bearer ${session.value.access}`)
  const response = await fetch(`${apiBase}${path}`, { ...options, headers })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const details = data.error?.details
    const first = details && typeof details === 'object' ? Object.values(details).flat()[0] : ''
    throw new Error(first || data.detail || 'Something went wrong. Please try again.')
  }
  return data
}

function setSession(data, username) {
  session.value = { ...data, username }
  localStorage.setItem('workroom-session', JSON.stringify(session.value))
  authForm.password = ''
  screen.value = 'booking'
  authError.value = ''
}

function openAuth(mode = 'login') {
  authMode.value = mode
  authError.value = ''
  screen.value = 'auth'
}

async function authenticate() {
  authBusy.value = true
  authError.value = ''
  try {
    if (authMode.value === 'register') {
      await request('/auth/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: authForm.username, email: authForm.email, password: authForm.password }),
      })
    }
    const tokens = await request('/auth/token/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: authForm.username, password: authForm.password }),
    })
    setSession(tokens, authForm.username)
  } catch (err) {
    authError.value = err.message
  } finally {
    authBusy.value = false
  }
}

async function loadMyBookings() {
  screen.value = 'bookings'
  bookingsLoading.value = true
  authError.value = ''
  try {
    myBookings.value = await request('/bookings/mine')
  } catch (err) {
    authError.value = err.message
  } finally {
    bookingsLoading.value = false
  }
}

function signOut() {
  session.value = null
  myBookings.value = []
  localStorage.removeItem('workroom-session')
  screen.value = 'booking'
}

async function loadRooms() {
  loading.value = true
  error.value = ''
  try { rooms.value = await request('/rooms') } catch (err) { error.value = err.message } finally { loading.value = false }
}

async function loadSlots() {
  if (!form.room || !form.date) return
  loading.value = true
  error.value = ''
  form.slot = null
  try { slots.value = await request(`/slots?roomId=${form.room}&date=${form.date}`) } catch (err) { error.value = err.message } finally { loading.value = false }
}

function selectRoom(room) { form.room = room.id; form.slot = null; slots.value = [] }
function back() { error.value = ''; step.value = Math.max(1, step.value - 1) }
async function next() {
  if (!canContinue.value) return
  error.value = ''
  if (step.value === 4) return submit()
  step.value += 1
  if (step.value === 2 && form.room && form.date) await loadSlots()
}
async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const result = await request('/bookings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ roomId: form.room, slotId: form.slot, date: form.date, name: form.name, email: form.email, phone: form.phone, participants: Number(form.participants) }) })
    bookingCode.value = result.code
    step.value = 5
  } catch (err) { error.value = err.message } finally { submitting.value = false }
}
function restart() { Object.assign(form, { room: null, date: '', slot: null, name: '', email: '', phone: '', participants: 1 }); slots.value = []; bookingCode.value = ''; step.value = 1 }
watch(() => [form.room, form.date], ([room, date], [oldRoom, oldDate]) => { if (room && date && (room !== oldRoom || date !== oldDate) && step.value === 2) loadSlots() })
onMounted(loadRooms)
</script>

<template>
  <main class="site-shell">
    <header class="nav"><a class="wordmark" href="#" @click.prevent="screen = 'booking'; restart()"><span>W</span> workroom</a><p>Meet with intent.</p><div class="account-actions"><template v-if="session"><button class="nav-link" @click="loadMyBookings">My bookings</button><span class="account-name">{{ session.username }}</span><button class="nav-link" @click="signOut">Sign out</button></template><template v-else><button class="nav-link" @click="openAuth('login')">Log in</button><button class="nav-join" @click="openAuth('register')">Create account</button></template></div></header>

    <template v-if="screen === 'booking'">
    <section v-if="step < 5" class="hero"><p class="eyebrow">ROOM RESERVATION</p><h1>Make space<br><em>for good work.</em></h1><p class="lede">A calmer way to reserve a room for your next idea, conversation, or decision.</p></section>

    <section v-if="step < 5" class="progress" aria-label="Booking progress">
      <template v-for="(label, index) in steps" :key="label"><div :class="['progress-item', { active: step === index + 1, complete: step > index + 1 }]"><span>{{ String(index + 1).padStart(2, '0') }}</span><small>{{ label }}</small></div><i v-if="index < steps.length - 1"></i></template>
    </section>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>

    <section v-if="step === 1" class="panel room-panel">
      <div class="section-heading"><div><p class="eyebrow">01 — ROOM</p><h2>Pick your setting.</h2></div><p>{{ loading ? 'Loading rooms…' : `${rooms.length} spaces available` }}</p></div>
      <div class="room-grid">
        <button v-for="room in rooms" :key="room.id" class="room-card" :class="{ selected: form.room === room.id }" @click="selectRoom(room)">
          <img :src="room.image" :alt="room.name" /><div class="card-content"><div class="room-title"><h3>{{ room.name }}</h3><span>{{ room.capacity }} people</span></div><div class="facilities"><b v-for="facility in room.facilities.slice(0, 3)" :key="facility">{{ facility }}</b></div><div class="price">{{ new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(room.pricePerHour) }} <small>/ hour</small></div></div>
        </button>
      </div>
    </section>

    <section v-if="step === 2" class="panel time-panel">
      <div class="section-heading"><div><p class="eyebrow">02 — DATE & TIME</p><h2>Find your window.</h2></div><p>{{ selectedRoom?.name }}</p></div>
      <div class="date-row"><label><span>Date</span><input v-model="form.date" :min="today" type="date" /></label><div class="capacity-note"><span>Capacity</span><strong>{{ selectedRoom?.capacity }} people</strong></div></div>
      <div v-if="form.date" class="slots"><p class="slot-label">Available on {{ formattedDate }}</p><div class="slot-grid"><button v-for="slot in slots" :key="slot.id" :disabled="!slot.isAvailable" :class="{ selected: form.slot === slot.id }" @click="form.slot = slot.id">{{ slot.time.slice(0, 5) }}<small>{{ slot.isAvailable ? 'available' : 'taken' }}</small></button></div></div>
      <p v-else class="empty">Choose a date to see the openings.</p>
    </section>

    <section v-if="step === 3" class="panel details-panel"><div class="section-heading"><div><p class="eyebrow">03 — HOST DETAILS</p><h2>Who is this for?</h2></div></div>
      <div class="form-grid"><label class="wide"><span>Your name</span><input v-model="form.name" placeholder="Your full name" autocomplete="name" /></label><label><span>Email address</span><input v-model="form.email" type="email" placeholder="you@company.com" autocomplete="email" /></label><label><span>Phone number</span><input v-model="form.phone" type="tel" placeholder="0812 3456 7890" autocomplete="tel" /></label><label><span>Guests</span><input v-model.number="form.participants" type="number" min="1" :max="selectedRoom?.capacity" /></label></div><p class="hint">Up to {{ selectedRoom?.capacity }} guests are welcome in this room.</p>
    </section>

    <section v-if="step === 4" class="panel confirm-panel"><p class="eyebrow">04 — ONE LAST LOOK</p><h2>Ready when you are.</h2><div class="receipt"><div><span>Room</span><strong>{{ selectedRoom?.name }}</strong></div><div><span>Date</span><strong>{{ formattedDate }}</strong></div><div><span>Time</span><strong>{{ selectedSlot?.time.slice(0, 5) }}</strong></div><div><span>Guests</span><strong>{{ form.participants }} people</strong></div><div class="total"><span>Hourly rate</span><strong>{{ price }}</strong></div></div><p class="confirmation-note">By confirming, you reserve this room for the selected time. We’ll send the booking details to {{ form.email }}.</p></section>

    <section v-if="step < 5" class="actions"><button v-if="step > 1" class="back" @click="back">← Back</button><span v-else></span><button class="continue" :disabled="!canContinue || submitting" @click="next">{{ submitting ? 'Reserving…' : step === 4 ? 'Confirm booking →' : 'Continue →' }}</button></section>

    <section v-if="step === 5" class="success"><div class="success-mark">✓</div><p class="eyebrow">ALL SET</p><h1>Your room is<br><em>waiting.</em></h1><p class="lede">{{ selectedRoom?.name }} is reserved for {{ formattedDate }}, {{ selectedSlot?.time.slice(0, 5) }}.</p><div class="code"><span>BOOKING CODE</span><strong>{{ bookingCode }}</strong></div><p v-if="session" class="hint">This reservation is saved to your account.</p><p v-else class="hint">Log in before booking to keep this reservation in your account.</p><button class="continue" @click="restart">Book another room →</button></section>
    </template>

    <section v-else-if="screen === 'auth'" class="account-panel panel">
      <p class="eyebrow">YOUR WORKROOM ACCOUNT</p>
      <h2>{{ authMode === 'login' ? 'Welcome back.' : 'Make it yours.' }}</h2>
      <p class="account-intro">{{ authMode === 'login' ? 'Log in to find your upcoming room reservations.' : 'Create an account to keep all your room reservations together.' }}</p>
      <p v-if="authError" class="alert" role="alert">{{ authError }}</p>
      <form class="account-form" @submit.prevent="authenticate">
        <label><span>Username</span><input v-model="authForm.username" autocomplete="username" required minlength="3" /></label>
        <label v-if="authMode === 'register'"><span>Email address</span><input v-model="authForm.email" type="email" autocomplete="email" required /></label>
        <label><span>Password</span><input v-model="authForm.password" type="password" :autocomplete="authMode === 'login' ? 'current-password' : 'new-password'" required minlength="8" /></label>
        <button class="continue" :disabled="authBusy">{{ authBusy ? 'One moment…' : authMode === 'login' ? 'Log in →' : 'Create account →' }}</button>
      </form>
      <p class="account-switch">{{ authMode === 'login' ? 'New to workroom?' : 'Already have an account?' }} <button class="inline-link" @click="openAuth(authMode === 'login' ? 'register' : 'login')">{{ authMode === 'login' ? 'Create an account' : 'Log in' }}</button></p>
      <button class="text-back" @click="screen = 'booking'">← Back to rooms</button>
    </section>

    <section v-else class="bookings-view">
      <div class="bookings-heading"><div><p class="eyebrow">YOUR WORKROOM ACCOUNT</p><h1>Room to return to.</h1><p class="lede">Reservations made while logged in appear here.</p></div><span class="booking-count">{{ myBookings.length }} {{ myBookings.length === 1 ? 'reservation' : 'reservations' }}</span></div>
      <p v-if="authError" class="alert" role="alert">{{ authError }}</p>
      <div v-if="bookingsLoading" class="empty-bookings">Gathering your reservations…</div>
      <div v-else-if="myBookings.length" class="booking-list">
        <article v-for="booking in myBookings" :key="booking.code" class="booking-card">
          <div class="booking-card-top"><span class="booking-date">{{ new Intl.DateTimeFormat('en', { dateStyle: 'medium' }).format(new Date(`${booking.date}T00:00:00`)) }}</span><span class="booking-code">{{ booking.code }}</span></div>
          <h2>{{ booking.room }}</h2>
          <div class="booking-meta"><span><small>TIME</small>{{ booking.time }}</span><span><small>GUESTS</small>{{ booking.participants }} people</span></div>
        </article>
      </div>
      <div v-else-if="!authError" class="empty-bookings"><span class="empty-mark">W</span><h2>Nothing on the calendar yet.</h2><p>Book a room while logged in and it will be waiting here.</p><button class="continue" @click="screen = 'booking'; restart()">Explore rooms →</button></div>
      <button class="text-back" @click="screen = 'booking'">← Back to rooms</button>
    </section>
  </main>
</template>
