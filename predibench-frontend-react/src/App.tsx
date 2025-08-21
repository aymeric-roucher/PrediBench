import { useEffect, useState } from 'react'
import type { Event, LeaderboardEntry, Stats } from './api'
import { apiService } from './api'
import { Navigation } from './components/Navigation'
import { LeaderboardPage } from './components/LeaderboardPage'
import { ModelsPage } from './components/ModelsPage'
import { QuestionsPage } from './components/QuestionsPage'

function App() {
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState('leaderboard')
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
      console.error('Error details:', {
        message: errorMessage,
        stack: error instanceof Error ? error.stack : undefined,
        name: error instanceof Error ? error.name : 'Unknown'
      })
      setError(`Failed to load data: ${errorMessage}`)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }


  useEffect(() => {
    loadData()
  }, [])

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'leaderboard':
        return <LeaderboardPage leaderboard={leaderboard} events={events} />
      case 'models':
        return <ModelsPage leaderboard={leaderboard} />
      case 'questions':
        return <QuestionsPage events={events} leaderboard={leaderboard} />
      default:
        return <LeaderboardPage leaderboard={leaderboard} events={events} />
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header and Navigation */}
      <header className="border-b border-border bg-card shadow-sm">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <h1 className="text-3xl font-bold tracking-tight">
                PrediBench
              </h1>
              <p className="text-sm text-muted-foreground">
                Letting LLMs bet their money on the future
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <Navigation currentPage={currentPage} onPageChange={setCurrentPage} />
            </div>
          </div>
        </div>
      </header>

      {/* Page Content */}
      {error ? (
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
      ) : loading ? (
        <div className="container mx-auto px-6 py-12 flex items-center justify-center">
          <div className="flex items-center space-x-3">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="text-muted-foreground">Loading benchmark data...</span>
          </div>
        </div>
      ) : (
        renderCurrentPage()
      )}
    </div>
  )
}

export default App
