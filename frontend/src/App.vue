<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

const apiBase = import.meta.env.VITE_API_URL || '/api'
const steps = ['Choose room', 'Find a time', 'Your details', 'Confirm']
const step = ref(1)
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
  const response = await fetch(`${apiBase}${path}`, options)
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const details = data.error?.details
    const first = details && typeof details === 'object' ? Object.values(details).flat()[0] : ''
    throw new Error(first || data.detail || 'Something went wrong. Please try again.')
  }
  return data
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
    <header class="nav"><a class="wordmark" href="#" @click.prevent="restart"><span>W</span> workroom</a><p>Meet with intent.</p></header>

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

    <section v-if="step === 5" class="success"><div class="success-mark">✓</div><p class="eyebrow">ALL SET</p><h1>Your room is<br><em>waiting.</em></h1><p class="lede">{{ selectedRoom?.name }} is reserved for {{ formattedDate }}, {{ selectedSlot?.time.slice(0, 5) }}.</p><div class="code"><span>BOOKING CODE</span><strong>{{ bookingCode }}</strong></div><button class="continue" @click="restart">Book another room →</button></section>
  </main>
</template>
