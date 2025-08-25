import { useEffect, useState } from 'react'
import { Route, BrowserRouter as Router, Routes, useLocation } from 'react-router-dom'
import type { Event, LeaderboardEntry, Stats } from './api'
import { apiService } from './api'
import { AboutPage } from './components/AboutPage'
import { EventDetail } from './components/EventDetail'
import { HomePage } from './components/HomePage'
import { Layout } from './components/Layout'
import { LeaderboardPage } from './components/LeaderboardPage'
import { ModelsPage } from './components/ModelsPage'
import { QuestionsPage } from './components/QuestionsPage'
import { ThemeProvider } from './contexts/ThemeContext'
import { useAnalytics } from './hooks/useAnalytics'

function AppContent() {
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const location = useLocation()
  const { trackPageView } = useAnalytics()

  const loadData = async () => {
    try {
      console.log('Starting to load data...')
      const [leaderboardData, eventsData, statsData] = await Promise.all([
        apiService.getLeaderboard().then(data => {
          console.log('Leaderboard data received:', data)
          return data
        }),
        apiService.getEvents().then(data => {
          console.log('Events data received:', data)
          return data
        }),
        apiService.getStats().then(data => {
          console.log('Stats data received:', data)
          return data
        })
      ])

      setLeaderboard(leaderboardData)
      setEvents(eventsData)
      setStats(statsData)
      console.log('All data loaded successfully')
    } catch (error) {
      console.error('Error loading data:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      setError(`Failed to load data: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    trackPageView(getCurrentPage())
  }, [location, trackPageView])

  const getCurrentPage = () => {
    if (location.pathname === '/') return 'home'
    if (location.pathname === '/leaderboard') return 'leaderboard'
    if (location.pathname === '/events') return 'events'
    if (location.pathname === '/models') return 'models'
    if (location.pathname === '/about') return 'about'
    if (location.pathname.startsWith('/events/')) return 'events'
    return 'home'
  }

  if (error) {
    return (
      <Layout currentPage={getCurrentPage()}>
        <div className="container mx-auto px-6 py-12 text-center">
          <h2 className="text-xl font-bold text-red-600 mb-2">Error Loading Data</h2>
          <p className="text-muted-foreground mb-4">{error}</p>
          <button
            onClick={() => {
              setError(null)
              setLoading(true)
              loadData()
            }}
            className="px-4 py-2 bg-primary text-white rounded hover:bg-primary/90"
          >
            Retry
          </button>
          <div className="mt-4 text-sm text-muted-foreground">
            <p>Leaderboard data: {leaderboard.length} entries</p>
            <p>Events data: {events.length} entries</p>
          </div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout currentPage={getCurrentPage()}>
      <Routes>
        <Route path="/" element={<HomePage leaderboard={leaderboard} events={events} loading={loading} />} />
        <Route path="/leaderboard" element={<LeaderboardPage leaderboard={leaderboard} loading={loading} />} />
        <Route path="/events" element={<QuestionsPage events={events} leaderboard={leaderboard} loading={loading} />} />
        <Route path="/models" element={<ModelsPage leaderboard={leaderboard} />} />
        <Route path="/about" element={<AboutPage />} />
        <Route
          path="/events/:eventId"
          element={
            <EventDetailWrapper events={events} leaderboard={leaderboard} />
          }
        />
      </Routes>
    </Layout>
  )
}

function EventDetailWrapper({ events, leaderboard }: { events: Event[], leaderboard: LeaderboardEntry[] }) {
  const location = useLocation()
  const eventId = location.pathname.split('/events/')[1]
  const event = events.find(e => e.id === eventId)

  if (!event) {
    return (
      <div className="container mx-auto px-6 py-12 text-center">
        <h2 className="text-xl font-bold mb-2">Event Not Found</h2>
        <p className="text-muted-foreground">The event you're looking for doesn't exist.</p>
      </div>
    )
  }

  return <EventDetail event={event} leaderboard={leaderboard} />
}

function App() {
  return (
    <ThemeProvider defaultTheme="dark">
      <Router>
        <AppContent />
      </Router>
    </ThemeProvider>
  )
}

export default App
