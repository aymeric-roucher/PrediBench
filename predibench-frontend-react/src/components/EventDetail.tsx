import { ExternalLink, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Event, LeaderboardEntry } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'

interface EventDetailProps {
  event: Event
  leaderboard: LeaderboardEntry[]
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

export function EventDetail({ event, leaderboard }: EventDetailProps) {
  const [marketPricesData, setMarketPricesData] = useState<{ [marketId: string]: PriceData[] }>({})
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [loading, setLoading] = useState(false)

  // Function to convert URLs in text to clickable links
  const linkify = (text: string | null | undefined) => {
    if (!text) return null

    const urlRegex = /(https?:\/\/[^\s]+)/g

    return text.split(urlRegex).map((part, index) => {
      if (urlRegex.test(part)) {
        // Remove trailing punctuation from the URL
        const cleanUrl = part.replace(/[.,;:!?\)\]]+$/, '')
        const trailingPunct = part.slice(cleanUrl.length)

        return (
          <span key={index}>
            <a
              href={cleanUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 underline"
            >
              {cleanUrl}
            </a>
            {trailingPunct}
          </span>
        )
      }
      return part
    })
  }

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
      event?.markets?.forEach((market) => {
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
    if (event) {
      loadEventDetails(event.id)
    }
  }, [event])
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <button
          onClick={() => window.history.back()}
          className="flex items-center text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Back to events
        </button>
        <button
          onClick={() => window.history.back()}
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
                  <CardTitle className="text-xl mb-2">{event.title}</CardTitle>
                  <div className="text-muted-foreground text-base mb-4 leading-relaxed">{linkify(event.description)}</div>
                  <a
                    href={`https://polymarket.com/event/${event.slug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm mt-3 transition-colors"
                  >
                    See the event on Polymarket
                    <ExternalLink className="h-4 w-4 ml-1" />
                  </a>
                </div>
                <div className="flex items-center space-x-2 ml-4">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                    {event.markets?.length || 0} Markets
                  </span>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                    {event.end_datetime && new Date(event.end_datetime) > new Date() ? 'LIVE' : 'CLOSED'}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Markets</p>
                  <p className="text-2xl font-bold text-primary">{event.markets?.length || 0}</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Volume</p>
                  <p className="text-2xl font-bold">
                    {event.volume ? `$${(event.volume / 1000).toFixed(0)}K` : 'N/A'}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Ends</p>
                  <p className="text-2xl font-bold">
                    {event.end_datetime
                      ? new Date(event.end_datetime).toLocaleDateString()
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
                    {event?.markets?.map((market, index) => (
                      <div key={market.id} className="flex items-center space-x-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{
                            backgroundColor: `hsl(${index * 360 / (event.markets?.length || 1)}, 70%, 50%)`
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
                      {event?.markets?.map((market, index) => {
                        const marketData = marketPricesData[market.id] || []
                        return (
                          <Line
                            key={market.id}
                            type="monotone"
                            dataKey="price"
                            data={marketData}
                            stroke={`hsl(${index * 360 / (event.markets?.length || 1)}, 70%, 50%)`}
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