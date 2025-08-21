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

  const loadData = async () => {
    try {
      const [leaderboardData, eventsData, statsData] = await Promise.all([
        apiService.getLeaderboard(),
        apiService.getEvents(),
        apiService.getStats()
      ])

      setLeaderboard(leaderboardData)
      setEvents(eventsData)
      setStats(statsData)
    } catch (error) {
      console.error('Error loading data:', error)
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

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex items-center space-x-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <span className="text-muted-foreground">Loading benchmark data...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header and Navigation */}
      <div className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <h1 className="text-3xl font-bold tracking-tight">
                PrediBench
              </h1>
              <p className="text-sm text-muted-foreground">
                Letting LLMs bet their money on the future
              </p>
            </div>
            <div className="flex items-center space-x-1">
              {refreshing && (
                <div className="flex items-center mr-4">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary mr-2"></div>
                  <span className="text-xs text-muted-foreground">Refreshing...</span>
                </div>
              )}
              <Navigation currentPage={currentPage} onPageChange={setCurrentPage} />
            </div>
          </div>
        </div>
      </div>

      {/* Page Content */}
      {renderCurrentPage()}
    </div>
  )
}

export default App
