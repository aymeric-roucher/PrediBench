import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, Calendar, DollarSign, Target, Trophy, Activity, RefreshCw } from 'lucide-react'
import { apiService } from './api'
import type { LeaderboardEntry, Event, Stats } from './api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card'
import { Button } from './components/ui/button'

function App() {
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
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

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadData()
  }

  useEffect(() => {
    loadData()
  }, [])

  const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-green-500" />
      case 'down':
        return <TrendingUp className="h-4 w-4 text-red-500 rotate-180" />
      default:
        return <Activity className="h-4 w-4 text-gray-500" />
    }
  }

  const getChartData = () => {
    if (selectedModel) {
      const model = leaderboard.find(m => m.id === selectedModel)
      return model?.performanceHistory || []
    }
    
    // Aggregate data for all models
    const dates = leaderboard[0]?.performanceHistory?.map(h => h.date) || []
    return dates.map(date => {
      const dataPoint: any = { date }
      leaderboard.forEach(model => {
        const point = model.performanceHistory.find(h => h.date === date)
        if (point) {
          dataPoint[model.model] = point.score
        }
      })
      return dataPoint
    })
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
      {/* Header */}
      <div className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-8">
          <div className="text-center">
            <h1 className="text-4xl font-bold tracking-tight mb-2">
              Polymarket LLM Benchmark
            </h1>
            <p className="text-lg text-muted-foreground">
              Real-time performance tracking of AI models on prediction markets
            </p>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-yellow-100 rounded-lg">
                    <Trophy className="h-6 w-6 text-yellow-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Top Score</p>
                    <p className="text-2xl font-bold">
                      {stats?.topScore.toFixed(1) || '--'}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleRefresh}
                  disabled={refreshing}
                >
                  <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Target className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Avg Accuracy</p>
                  <p className="text-2xl font-bold">
                    {stats ? `${(stats.avgAccuracy * 100).toFixed(0)}%` : '--'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Activity className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Trades</p>
                  <p className="text-2xl font-bold">
                    {stats?.totalTrades.toLocaleString() || '--'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-emerald-100 rounded-lg">
                  <DollarSign className="h-6 w-6 text-emerald-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Profit</p>
                  <p className="text-2xl font-bold">
                    ${stats ? (stats.totalProfit / 1000).toFixed(1) : '--'}K
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Leaderboard */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Leaderboard</CardTitle>
                <CardDescription>Current performance rankings of LLM models</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {leaderboard.map((entry, index) => (
                    <div 
                      key={entry.id} 
                      className={`p-4 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
                        selectedModel === entry.id ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
                      }`}
                      onClick={() => setSelectedModel(selectedModel === entry.id ? null : entry.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                            index === 0 ? 'bg-yellow-100 text-yellow-800' :
                            index === 1 ? 'bg-slate-100 text-slate-800' :
                            index === 2 ? 'bg-orange-100 text-orange-800' :
                            'bg-muted text-muted-foreground'
                          }`}>
                            {index + 1}
                          </div>
                          <div>
                            <h3 className="font-semibold">{entry.model}</h3>
                            <p className="text-sm text-muted-foreground">
                              {entry.trades} trades • Updated {entry.lastUpdated}
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-6">
                          <div className="text-right">
                            <p className="text-sm text-muted-foreground">Score</p>
                            <p className="text-lg font-bold">{entry.score.toFixed(1)}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm text-muted-foreground">Accuracy</p>
                            <p className="text-lg font-semibold">{(entry.accuracy * 100).toFixed(0)}%</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm text-muted-foreground">Profit</p>
                            <p className="text-lg font-semibold text-green-600">${entry.profit.toLocaleString()}</p>
                          </div>
                          <div className="flex items-center">
                            {getTrendIcon(entry.trend)}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Performance Chart */}
            <Card className="mt-8">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Performance Trend</CardTitle>
                    <CardDescription>
                      {selectedModel ? 
                        `Showing: ${leaderboard.find(m => m.id === selectedModel)?.model}` : 
                        'Click a model to view individual performance'
                      }
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={getChartData()}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" />
                      <YAxis stroke="hsl(var(--muted-foreground))" />
                      <Tooltip 
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px'
                        }}
                      />
                      {selectedModel ? (
                        <Line 
                          type="monotone" 
                          dataKey={leaderboard.find(m => m.id === selectedModel)?.model} 
                          stroke="hsl(var(--primary))" 
                          strokeWidth={2} 
                        />
                      ) : (
                        leaderboard.map((model, index) => (
                          <Line 
                            key={model.id}
                            type="monotone" 
                            dataKey={model.model} 
                            stroke={['#3B82F6', '#10B981', '#F59E0B', '#EF4444'][index % 4]} 
                            strokeWidth={2} 
                          />
                        ))
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Events Section */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Active Events</CardTitle>
                <CardDescription>Current prediction markets on Polymarket</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {events.map((event) => (
                    <Card key={event.id} className="p-4 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-3">
                        <h3 className="text-sm font-medium line-clamp-2 flex-1 mr-2">{event.title}</h3>
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium flex-shrink-0 ${
                          event.category === 'Crypto' ? 'bg-orange-100 text-orange-800' :
                          event.category === 'Politics' ? 'bg-blue-100 text-blue-800' :
                          event.category === 'Technology' ? 'bg-purple-100 text-purple-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {event.category}
                        </span>
                      </div>
                      
                      <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{event.description}</p>
                      
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Probability</span>
                          <span className="font-medium">{(event.probability * 100).toFixed(0)}%</span>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-2">
                          <div 
                            className="bg-primary h-2 rounded-full transition-all" 
                            style={{ width: `${event.probability * 100}%` }}
                          ></div>
                        </div>
                        
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center text-muted-foreground">
                            <DollarSign className="h-3 w-3 mr-1" />
                            ${(event.volume / 1000).toFixed(0)}K volume
                          </div>
                          <div className="flex items-center text-muted-foreground">
                            <Calendar className="h-3 w-3 mr-1" />
                            {event.endDate}
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
