import { Clock, DollarSign, Search, TrendingUp, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Event, LeaderboardEntry } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'

interface QuestionsPageProps {
  events: Event[]
  leaderboard: LeaderboardEntry[]
  loading?: boolean
}

interface PriceData {
  date: string
  price: number
  marketId?: string
  marketName?: string
}

interface Prediction {
  model: string
  prediction: string
  confidence: number
  lastUpdated: string
}

export function QuestionsPage({ events, leaderboard, loading: initialLoading = false }: QuestionsPageProps) {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null)
  const [marketPricesData, setMarketPricesData] = useState<{ [marketId: string]: PriceData[] }>({})
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'volume' | 'probability' | 'endDate'>('volume')
  const [orderBy, setOrderBy] = useState<'asc' | 'desc'>('desc')
  const [isLive, setIsLive] = useState(false)

  const loadEventDetails = async (eventId: string) => {
    setLoading(true)
    try {
      const [marketPrices, predictionsData] = await Promise.all([
        fetch(`http://localhost:8080/api/event/${eventId}/markets/prices`).then(r => r.json()),
        fetch(`http://localhost:8080/api/event/${eventId}/predictions`).then(r => r.json())
      ])
      setMarketPricesData(marketPrices)
      setPredictions(predictionsData)
    } catch (error) {
      console.error('Error loading event details:', error)
      // Fallback to mock data
      const mockData: { [key: string]: PriceData[] } = {}
      selectedEvent?.markets?.forEach((market) => {
        mockData[market.id] = mockPriceHistory(market.question)
      })
      setMarketPricesData(mockData)
      setPredictions(mockModelPredictions())
    } finally {
      setLoading(false)
    }
  }

  const mockModelPredictions = () => {
    return leaderboard.slice(0, 4).map(model => ({
      model: model.model,
      prediction: Math.random() > 0.5 ? 'Yes' : 'No',
      confidence: parseFloat((Math.random() * 0.4 + 0.6).toFixed(2)),
      lastUpdated: '2 hours ago'
    }))
  }

  const mockPriceHistory = (marketName?: string) => {
    const days = 30
    const data = []
    let price = Math.random() * 0.4 + 0.3

    for (let i = 0; i < days; i++) {
      const date = new Date()
      date.setDate(date.getDate() - (days - i))
      price += (Math.random() - 0.5) * 0.1
      price = Math.max(0.1, Math.min(0.9, price))

      data.push({
        date: date.toISOString().split('T')[0],
        price: parseFloat(price.toFixed(3)),
        marketName: marketName
      })
    }
    return data
  }

  useEffect(() => {
    if (selectedEvent) {
      loadEventDetails(selectedEvent.id)
    }
  }, [selectedEvent])

  // Filter and sort events
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
        case 'probability':
          // Use average probability of markets
          const aAvgProb = a.markets?.reduce((sum, m) => sum + (m.outcomes?.[0]?.price || 0), 0) / (a.markets?.length || 1)
          const bAvgProb = b.markets?.reduce((sum, m) => sum + (m.outcomes?.[0]?.price || 0), 0) / (b.markets?.length || 1)
          comparison = (aAvgProb || 0) - (bAvgProb || 0)
          break
        case 'endDate':
          comparison = new Date(a.end_datetime || '').getTime() - new Date(b.end_datetime || '').getTime()
          break
      }
      return orderBy === 'desc' ? -comparison : comparison
    })

  if (selectedEvent) {

    return (
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={() => setSelectedEvent(null)}
            className="flex items-center text-muted-foreground hover:text-foreground transition-colors"
          >
            ← Back to questions
          </button>
          <button
            onClick={() => setSelectedEvent(null)}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Event Details */}
          <div className="lg:col-span-2">
            <Card className="mb-8">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-xl mb-2">{selectedEvent.title}</CardTitle>
                    <CardDescription className="text-base">{selectedEvent.description}</CardDescription>
                  </div>
                  <div className="flex items-center space-x-2 ml-4">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                      {selectedEvent.markets?.length || 0} Markets
                    </span>
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                      <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                      {selectedEvent.end_datetime && new Date(selectedEvent.end_datetime) > new Date() ? 'LIVE' : 'CLOSED'}
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Markets</p>
                    <p className="text-2xl font-bold text-primary">{selectedEvent.markets?.length || 0}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Volume</p>
                    <p className="text-2xl font-bold">
                      {selectedEvent.volume ? `$${(selectedEvent.volume / 1000).toFixed(0)}K` : 'N/A'}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Ends</p>
                    <p className="text-2xl font-bold">
                      {selectedEvent.end_datetime
                        ? new Date(selectedEvent.end_datetime).toLocaleDateString()
                        : 'N/A'
                      }
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Market Price Charts - Superposed */}
            <Card>
              <CardHeader>
                <CardTitle>Market Price History</CardTitle>
                <CardDescription>30-day price movements for all markets in this event</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="h-64 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  </div>
                ) : (
                  <div className="h-96">
                    {/* Market Legend */}
                    <div className="mb-4 flex flex-wrap gap-2">
                      {selectedEvent?.markets?.map((market, index) => (
                        <div key={market.id} className="flex items-center space-x-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{
                              backgroundColor: `hsl(${index * 360 / (selectedEvent.markets?.length || 1)}, 70%, 50%)`
                            }}
                          ></div>
                          <span className="text-sm text-muted-foreground line-clamp-1">
                            {market.question.length > 50 ? market.question.substring(0, 47) + '...' : market.question}
                          </span>
                        </div>
                      ))}
                    </div>

                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis
                          dataKey="date"
                          stroke="hsl(var(--muted-foreground))"
                          type="category"
                          allowDuplicatedCategory={false}
                        />
                        <YAxis stroke="hsl(var(--muted-foreground))" domain={[0, 1]} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px'
                          }}
                          formatter={(value: any, name: string) => [
                            `${(Number(value) * 100).toFixed(1)}%`,
                            name
                          ]}
                        />

                        {/* Create a line for each market */}
                        {selectedEvent?.markets?.map((market, index) => {
                          const marketData = marketPricesData[market.id] || []
                          return (
                            <Line
                              key={market.id}
                              type="monotone"
                              dataKey="price"
                              data={marketData}
                              stroke={`hsl(${index * 360 / (selectedEvent.markets?.length || 1)}, 70%, 50%)`}
                              strokeWidth={2}
                              dot={false}
                              name={market.question.length > 30 ? market.question.substring(0, 27) + '...' : market.question}
                            />
                          )
                        })}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Model Predictions */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Model Predictions</CardTitle>
                <CardDescription>Latest predictions from LLM models</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {predictions.map((prediction, index) => (
                      <div key={index} className="p-4 rounded-lg border border-border">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium">{prediction.model}</h4>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${prediction.prediction === 'Yes'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                            }`}>
                            {prediction.prediction}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-sm text-muted-foreground">
                          <span>Confidence: {prediction.confidence}</span>
                          <span>{prediction.lastUpdated}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Events</h1>
        <p className="text-muted-foreground">Prediction markets that LLM models are actively betting on</p>
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
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${isLive
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
                }`}
            >
              {isLive ? 'Live' : 'All'}
            </button>
          </div>
        </div>
      </div>

      {/* Events Grid with Loading States */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {initialLoading || events.length === 0 ? (
          // Show skeleton loading cards while loading
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
                <div className="space-y-1">
                  <div className="h-3 bg-gray-200 rounded animate-pulse"></div>
                  <div className="h-3 bg-gray-200 rounded animate-pulse w-5/6"></div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-4">
                  <div>
                    <div className="h-3 bg-gray-200 rounded animate-pulse mb-2"></div>
                    <div className="space-y-1">
                      {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="flex items-center justify-between">
                          <div className="h-3 bg-gray-200 rounded animate-pulse w-20"></div>
                          <div className="h-3 bg-gray-200 rounded animate-pulse w-12"></div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center justify-between border-t pt-3">
                    <div className="flex space-x-4">
                      <div className="h-4 bg-gray-200 rounded animate-pulse w-12"></div>
                      <div className="h-4 bg-gray-200 rounded animate-pulse w-16"></div>
                    </div>
                    <div className="h-4 bg-gray-200 rounded animate-pulse w-20"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        ) : filteredAndSortedEvents.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-muted-foreground">No events found matching your search criteria.</p>
          </div>
        ) : (
          filteredAndSortedEvents.map((event) => (
            <Card
              key={event.id}
              className="cursor-pointer hover:shadow-lg transition-all duration-200 hover:scale-[1.02]"
              onClick={() => setSelectedEvent(event)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between mb-2">
                  <CardTitle className="text-lg line-clamp-2 flex-1">{event.title}</CardTitle>
                  <div className="flex items-center space-x-2 ml-2">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {event.markets?.length || 0} Markets
                    </span>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                      {event.end_datetime && new Date(event.end_datetime) > new Date() ? 'LIVE' : 'CLOSED'}
                    </span>
                  </div>
                </div>
                <CardDescription className="line-clamp-2 text-sm">{event.description || "No description available"}</CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-4">
                  {/* Markets Preview */}
                  <div>
                    <p className="text-sm font-medium mb-2">Markets in this event:</p>
                    <div className="space-y-1">
                      {event.markets?.slice(0, 3).map((market) => (
                        <div key={market.id} className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground line-clamp-1 flex-1">{market.question}</span>
                          <div className="flex items-center space-x-2 ml-2">
                            <span className="font-medium text-xs">
                              {market.outcomes?.[0]?.price ? `${(market.outcomes[0].price * 100).toFixed(0)}%` : 'N/A'}
                            </span>
                          </div>
                        </div>
                      ))}
                      {(event.markets?.length || 0) > 3 && (
                        <div className="text-xs text-muted-foreground">
                          +{(event.markets?.length || 0) - 3} more markets
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Volume and End Date */}
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
                          {event.liquidity ? `$${(event.liquidity / 1000).toFixed(0)}K liquidity` : 'No liquidity data'}
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
          ))
        )}
      </div>
    </div>
  )
}