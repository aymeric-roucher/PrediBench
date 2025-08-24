import { ChevronDown, Clock, DollarSign, Search, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Event, LeaderboardEntry } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { getChartColor } from './ui/chart-colors'
import { VisxLineChart } from './ui/visx-line-chart'

interface LeaderboardPageProps {
  leaderboard: LeaderboardEntry[]
  events: Event[]
  loading?: boolean
}

export function LeaderboardPage({ leaderboard, events, loading = false }: LeaderboardPageProps) {
  const [visibleModels, setVisibleModels] = useState(10)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'volume' | 'probability' | 'endDate'>('volume')
  const [orderBy, setOrderBy] = useState<'asc' | 'desc'>('desc')
  const [isLive, setIsLive] = useState(false)

  const showMore = () => {
    setVisibleModels(prev => prev + 10)
  }

  // Filter and sort events for the events section
  const filteredAndSortedEvents = events
    .filter(event => {
      const matchesSearch = searchQuery === '' ||
        event.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        event.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        event.markets?.some(market =>
          market.question?.toLowerCase().includes(searchQuery.toLowerCase())
        )

      const matchesStatus = isLive ? (event.end_datetime ? new Date(event.end_datetime) > new Date() : true) : true

      return matchesSearch && matchesStatus
    })
    .sort((a, b) => {
      let comparison = 0
      switch (sortBy) {
        case 'volume':
          comparison = (a.volume || 0) - (b.volume || 0)
          break
        case 'probability': {
          const aAvgProb = a.markets?.reduce((sum, m) => sum + (m.outcomes[0].price), 0) / (a.markets.length)
          const bAvgProb = b.markets?.reduce((sum, m) => sum + (m.outcomes[0].price), 0) / (b.markets.length)
          comparison = (aAvgProb) - (bAvgProb)
          break
        }
        case 'endDate':
          comparison = new Date(a.end_datetime || '').getTime() - new Date(b.end_datetime || '').getTime()
          break
      }
      return orderBy === 'desc' ? -comparison : comparison
    })


  return (
    <div className="container mx-auto px-4 py-8">
      {/* Page Title and Subtitle */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">PrediBench Leaderboard</h1>
        <p className="text-lg text-muted-foreground">LLMs bet their money on the future</p>
      </div>

      {/* Leaderboard Table */}
      <div className="mb-16">
        <div className="bg-card rounded-xl border border-border/30 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/30">
                <tr>
                  <th className="text-left py-4 px-6 font-semibold">Model Name</th>
                  <th className="text-right py-4 px-6 font-semibold">Total PnL</th>
                  <th className="text-right py-4 px-6 font-semibold">Brier Score</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, index) => (
                    <tr key={index} className="border-t border-border/20">
                      <td className="py-4 px-6">
                        <div className="flex items-center space-x-4">
                          <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse"></div>
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-32"></div>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <div className="h-4 bg-gray-200 rounded animate-pulse w-16 ml-auto"></div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <div className="h-4 bg-gray-200 rounded animate-pulse w-16 ml-auto"></div>
                      </td>
                    </tr>
                  ))
                ) : (
                  leaderboard.slice(0, visibleModels).map((model, index) => (
                    <tr key={model.id} className="border-t border-border/20 hover:bg-muted/20 transition-colors">
                      <td className="py-4 px-6">
                        <div className="flex items-center space-x-4">
                          <div className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold ${
                            index === 0 ? 'bg-gradient-to-br from-yellow-100 to-yellow-50 text-yellow-800 shadow-md shadow-yellow-200/50' :
                            index === 1 ? 'bg-gradient-to-br from-slate-100 to-slate-50 text-slate-800 shadow-md shadow-slate-200/50' :
                            index === 2 ? 'bg-gradient-to-br from-amber-100 to-amber-50 text-amber-800 shadow-md shadow-amber-200/50' :
                            'bg-gradient-to-br from-muted to-muted/70 text-muted-foreground shadow-sm'
                          }`}>
                            {index + 1}
                          </div>
                          <span className="font-medium">{model.model}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-right font-medium">
                        <span className={model.final_cumulative_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          ${model.final_cumulative_pnl.toFixed(1)}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-right font-medium">
                        {model.accuracy ? (1 - model.accuracy).toFixed(3) : 'N/A'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
        
        {/* Show More Button */}
        {leaderboard.length > visibleModels && (
          <div className="text-center mt-6">
            <button
              onClick={showMore}
              className="inline-flex items-center space-x-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              <ChevronDown className="h-4 w-4" />
              <span>Show more</span>
            </button>
          </div>
        )}
      </div>

      {/* PnL Evolution Chart */}
      <div className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8">PnL Evolution</h2>
        <div className="bg-card rounded-xl border border-border/30 p-6">
          <div className="h-80">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : (
              <VisxLineChart
                height={320}
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
                  const padding = Math.max(range * 0.25, 0.02)
                  return [min - padding, max + padding]
                })()
                }
              />
            )}
          </div>
        </div>
      </div>

      {/* Events Section */}
      <div>
        <div className="text-center mb-8">
          <div className="flex items-center justify-center space-x-4">
            <h2 className="text-2xl font-bold">Events</h2>
            <Link 
              to="/events" 
              className="text-primary hover:text-primary/80 transition-colors font-medium"
            >
              View all →
            </Link>
          </div>
        </div>
        
        {/* Search and Filters */}
        <div className="mb-8 space-y-4">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search events by title, topic, ticker, or markets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-4">
            {/* Sort By */}
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium">Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'volume' | 'probability' | 'endDate')}
                className="px-3 py-1 border border-border rounded bg-background text-sm"
              >
                <option value="volume">Volume</option>
                <option value="probability">Probability</option>
                <option value="endDate">End Date</option>
              </select>
            </div>

            {/* Order */}
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium">Order:</span>
              <select
                value={orderBy}
                onChange={(e) => setOrderBy(e.target.value as 'asc' | 'desc')}
                className="px-3 py-1 border border-border rounded bg-background text-sm"
              >
                <option value="desc">High to Low</option>
                <option value="asc">Low to High</option>
              </select>
            </div>

            {/* Live/All Toggle */}
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium">Status:</span>
              <button
                onClick={() => setIsLive(!isLive)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  isLive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}
              >
                {isLive ? 'Live' : 'All'}
              </button>
            </div>
          </div>
        </div>

        {/* Events Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {loading || events.length === 0 ? (
            Array.from({ length: 6 }).map((_, index) => (
              <Card key={index}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-gray-200 rounded animate-pulse"></div>
                      <div className="h-3 bg-gray-200 rounded animate-pulse w-3/4"></div>
                    </div>
                    <div className="flex space-x-2 ml-2">
                      <div className="h-6 w-16 bg-gray-200 rounded-full animate-pulse"></div>
                      <div className="h-6 w-12 bg-gray-200 rounded-full animate-pulse"></div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="h-20 bg-gray-200 rounded animate-pulse"></div>
                </CardContent>
              </Card>
            ))
          ) : filteredAndSortedEvents.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <p className="text-muted-foreground">No events found matching your search criteria.</p>
            </div>
          ) : (
            filteredAndSortedEvents.slice(0, 6).map((event) => (
              <Link key={event.id} to={`/events/${event.id}`}>
                <Card className="cursor-pointer hover:shadow-lg transition-all duration-200 hover:scale-[1.02]">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between mb-2">
                      <CardTitle className="text-lg line-clamp-2 flex-1">{event.title}</CardTitle>
                      <div className="flex items-center space-x-2 ml-2">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {event.markets.length} Markets
                        </span>
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                          {event.end_datetime && new Date(event.end_datetime) > new Date() ? 'LIVE' : 'CLOSED'}
                        </span>
                      </div>
                    </div>
                    <CardDescription className="line-clamp-2 text-sm">
                      {event.description || "No description available"}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm font-medium mb-2">Markets in this event:</p>
                        <div className="space-y-1">
                          {event.markets?.slice(0, 2).map((market) => (
                            <div key={market.id} className="flex items-center justify-between text-sm">
                              <span className="text-muted-foreground line-clamp-1 flex-1">
                                {market.question}
                              </span>
                              <div className="flex items-center space-x-2 ml-2">
                                <span className="font-medium text-xs">
                                  {market.outcomes[0].price ? `${(market.outcomes[0].price * 100).toFixed(0)}%` : 'N/A'}
                                </span>
                              </div>
                            </div>
                          ))}
                          {(event.markets.length) > 2 && (
                            <div className="text-xs text-muted-foreground">
                              +{(event.markets.length) - 2} more markets
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between text-sm border-t pt-3">
                        <div className="flex items-center space-x-4">
                          <div className="flex items-center text-muted-foreground">
                            <DollarSign className="h-4 w-4 mr-1" />
                            <span className="font-medium">
                              {event.volume ? `$${(event.volume / 1000).toFixed(0)}K` : 'N/A'}
                            </span>
                          </div>
                          <div className="flex items-center text-muted-foreground">
                            <TrendingUp className="h-4 w-4 mr-1" />
                            <span className="text-xs">
                              {event.liquidity ? `$${(event.liquidity / 1000).toFixed(0)}K liquidity` : 'No liquidity'}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center text-muted-foreground">
                          <Clock className="h-4 w-4 mr-1" />
                          <span className="text-xs">
                            {event.end_datetime
                              ? `Closes ${new Date(event.end_datetime).toLocaleDateString()}`
                              : 'No end date'
                            }
                          </span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  )
}