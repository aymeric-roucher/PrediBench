import { Activity, Calendar, DollarSign, TrendingUp } from 'lucide-react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Event, LeaderboardEntry } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'

interface LeaderboardPageProps {
  leaderboard: LeaderboardEntry[]
  events: Event[]
  loading?: boolean
}

export function LeaderboardPage({ leaderboard, events, loading = false }: LeaderboardPageProps) {
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

  const getTopModelsChartData = () => {
    const topModels = leaderboard.slice(0, 3)
    const dates = topModels[0]?.performanceHistory?.map(h => h.date) || []

    return dates.map(date => {
      const dataPoint: any = { date }
      topModels.forEach(model => {
        const point = model.performanceHistory.find(h => h.date === date)
        if (point) {
          dataPoint[model.model] = point.cumulative_pnl
        }
      })
      return dataPoint
    })
  }

  return (
    <div className="container mx-auto px-4 py-8">
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
                {loading ? (
                  Array.from({ length: 5 }).map((_, index) => (
                    <div key={index} className="p-4 rounded-lg border border-border">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse"></div>
                          <div>
                            <div className="h-4 bg-gray-200 rounded animate-pulse w-24 mb-2"></div>
                            <div className="h-3 bg-gray-200 rounded animate-pulse w-32"></div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-6">
                          <div className="text-right">
                            <div className="h-3 bg-gray-200 rounded animate-pulse w-16 mb-1"></div>
                            <div className="h-5 bg-gray-200 rounded animate-pulse w-12"></div>
                          </div>
                          <div className="text-right">
                            <div className="h-3 bg-gray-200 rounded animate-pulse w-20 mb-1"></div>
                            <div className="h-5 bg-gray-200 rounded animate-pulse w-16"></div>
                          </div>
                          <div className="w-4 h-4 bg-gray-200 rounded animate-pulse"></div>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  leaderboard.map((entry, index) => (
                    <div
                      key={entry.id}
                      className="p-4 rounded-lg border border-border hover:border-primary/50 transition-all hover:shadow-md"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${index === 0 ? 'bg-yellow-100 text-yellow-800' :
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
                            <p className="text-sm text-muted-foreground">Final PnL</p>
                            <p className="text-lg font-bold">{entry.final_cumulative_pnl.toFixed(1)}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm text-muted-foreground">Brier score</p>
                            <p className="text-lg font-semibold text-green-600">${Math.round(entry.final_cumulative_pnl * 1000).toLocaleString()}</p>
                          </div>
                          <div className="flex items-center">
                            {getTrendIcon(entry.trend)}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Top Models Performance Chart */}
          <Card className="mt-8">
            <CardHeader>
              <CardTitle>Top 3 Models Performance</CardTitle>
              <CardDescription>Performance trends of the leading models</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                {loading ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={getTopModelsChartData()}>
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
                      {leaderboard.slice(0, 3).map((model, index) => (
                        <Line
                          key={model.id}
                          type="monotone"
                          dataKey={model.model}
                          stroke={['#3B82F6', '#10B981', '#F59E0B'][index]}
                          strokeWidth={2}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Events */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Recent Events</CardTitle>
              <CardDescription>Latest prediction markets LLMs have bet on</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {loading ? (
                  Array.from({ length: 6 }).map((_, index) => (
                    <Card key={index} className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1 mr-2 space-y-2">
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2"></div>
                        </div>
                        <div className="h-6 w-16 bg-gray-200 rounded-full animate-pulse"></div>
                      </div>
                      <div className="h-3 bg-gray-200 rounded animate-pulse w-full mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded animate-pulse w-2/3 mb-3"></div>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="h-3 bg-gray-200 rounded animate-pulse w-12"></div>
                          <div className="h-3 bg-gray-200 rounded animate-pulse w-16"></div>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="h-3 bg-gray-200 rounded animate-pulse w-20"></div>
                          <div className="h-3 bg-gray-200 rounded animate-pulse w-20"></div>
                        </div>
                      </div>
                    </Card>
                  ))
                ) : (
                  events.slice(0, 6).map((event) => (
                    <a key={event.id} href={`/events/${event.id}`}>
                      <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                        <div className="flex items-start justify-between mb-3">
                          <h3 className="text-sm font-medium line-clamp-2 flex-1 mr-2">{event.title}</h3>
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {event.markets.length} Markets
                          </span>
                        </div>

                        <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{event.description}</p>

                        <div className="space-y-3">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground">Volume</span>
                            <span className="font-medium">
                              {event.volume ? `$${(event.volume / 1000).toFixed(0)}K` : 'N/A'}
                            </span>
                          </div>

                          <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center text-muted-foreground">
                              <DollarSign className="h-3 w-3 mr-1" />
                              {event.liquidity ? `$${(event.liquidity / 1000).toFixed(0)}K liquidity` : 'No liquidity'}
                            </div>
                            <div className="flex items-center text-muted-foreground">
                              <Calendar className="h-3 w-3 mr-1" />
                              {event.end_datetime
                                ? new Date(event.end_datetime).toLocaleDateString()
                                : 'No end date'
                              }
                            </div>
                          </div>
                        </div>
                      </Card>
                    </a>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}