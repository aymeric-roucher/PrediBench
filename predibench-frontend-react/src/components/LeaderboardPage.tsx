import { Activity, Calendar, DollarSign, TrendingUp } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { Event, LeaderboardEntry } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { VisxLineChart } from './ui/visx-line-chart'
import { getChartColor } from './ui/chart-colors'

interface LeaderboardPageProps {
  leaderboard: LeaderboardEntry[]
  events: Event[]
  loading?: boolean
}

export function LeaderboardPage({ leaderboard, events, loading = false }: LeaderboardPageProps) {
  const navigate = useNavigate()
  
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
  
  const handleModelClick = (modelId: string) => {
    navigate(`/models?selected=${modelId}`)
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
                      className="group relative p-6 rounded-xl border border-border/50 hover:border-primary/30 transition-all duration-200 hover:shadow-lg hover:shadow-primary/5 cursor-pointer bg-gradient-to-r from-background to-background hover:from-primary/[0.02] hover:to-background"
                      onClick={() => handleModelClick(entry.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-5">
                          <div className={`flex items-center justify-center w-12 h-12 rounded-full text-sm font-bold transition-transform group-hover:scale-105 ${
                            index === 0 ? 'bg-gradient-to-br from-yellow-100 to-yellow-50 text-yellow-800 shadow-md shadow-yellow-200/50' :
                            index === 1 ? 'bg-gradient-to-br from-slate-100 to-slate-50 text-slate-800 shadow-md shadow-slate-200/50' :
                            index === 2 ? 'bg-gradient-to-br from-amber-100 to-amber-50 text-amber-800 shadow-md shadow-amber-200/50' :
                            'bg-gradient-to-br from-muted to-muted/70 text-muted-foreground shadow-sm'
                          }`}>
                            {index + 1}
                          </div>
                          <div className="space-y-1">
                            <h3 className="font-semibold text-lg text-foreground group-hover:text-primary transition-colors">{entry.model}</h3>
                            <p className="text-sm text-muted-foreground">
                              {entry.trades} trades • Updated {entry.lastUpdated}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center space-x-8">
                          <div className="text-right space-y-1">
                            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Score</p>
                            <p className="text-xl font-bold text-foreground">{entry.final_cumulative_pnl.toFixed(1)}</p>
                          </div>
                          <div className="text-right space-y-1">
                            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Value</p>
                            <p className="text-xl font-bold text-emerald-600">${Math.round(entry.final_cumulative_pnl * 1000).toLocaleString()}</p>
                          </div>
                          <div className="flex items-center">
                            {getTrendIcon(entry.trend)}
                          </div>
                        </div>
                      </div>
                      <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none" />
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
                  <VisxLineChart
                    height={256}
                    margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                    series={leaderboard.slice(0, 3).map((model, index) => ({
                      dataKey: model.model,
                      data: (model.pnl_history || []).map(point => ({
                        x: point.date,
                        y: point.value
                      })),
                      stroke: getChartColor(index),
                      name: model.model
                    }))}
                    yDomain={(() => {
                      const allValues = leaderboard.slice(0, 3).flatMap(model => 
                        (model.pnl_history || []).map(point => point.value)
                      )
                      if (allValues.length === 0) return [0, 1]
                      const min = Math.min(...allValues)
                      const max = Math.max(...allValues)
                      const range = max - min
                      const padding = Math.max(range * 0.25, 0.02) // 25% padding or minimum 0.02
                      return [min - padding, max + padding]
                    })()}
                  />
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