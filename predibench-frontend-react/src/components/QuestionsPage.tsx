import { useState, useEffect } from 'react'
import { Calendar, DollarSign, X } from 'lucide-react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Event, LeaderboardEntry } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'

interface QuestionsPageProps {
  events: Event[]
  leaderboard: LeaderboardEntry[]
}

interface PriceData {
  date: string
  price: number
}

interface Prediction {
  model: string
  prediction: string
  confidence: number
  lastUpdated: string
}

export function QuestionsPage({ events, leaderboard }: QuestionsPageProps) {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null)
  const [priceHistory, setPriceHistory] = useState<PriceData[]>([])
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [loading, setLoading] = useState(false)

  const loadEventDetails = async (eventId: string) => {
    setLoading(true)
    try {
      const [priceData, predictionsData] = await Promise.all([
        fetch(`http://localhost:8080/api/event/${eventId}/prices`).then(r => r.json()),
        fetch(`http://localhost:8080/api/event/${eventId}/predictions`).then(r => r.json())
      ])
      setPriceHistory(priceData)
      setPredictions(predictionsData)
    } catch (error) {
      console.error('Error loading event details:', error)
      // Fallback to mock data
      setPriceHistory(mockPriceHistory())
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

  const mockPriceHistory = () => {
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
        price: parseFloat(price.toFixed(3))
      })
    }
    return data
  }

  useEffect(() => {
    if (selectedEvent) {
      loadEventDetails(selectedEvent.id)
    }
  }, [selectedEvent])

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
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ml-4 ${
                    selectedEvent.category === 'Crypto' ? 'bg-orange-100 text-orange-800' :
                    selectedEvent.category === 'Politics' ? 'bg-blue-100 text-blue-800' :
                    selectedEvent.category === 'Technology' ? 'bg-purple-100 text-purple-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {selectedEvent.category}
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Current Probability</p>
                    <p className="text-2xl font-bold text-primary">{(selectedEvent.probability * 100).toFixed(0)}%</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Volume</p>
                    <p className="text-2xl font-bold">${(selectedEvent.volume / 1000).toFixed(0)}K</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Ends</p>
                    <p className="text-2xl font-bold">{selectedEvent.endDate}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Price Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Price History</CardTitle>
                <CardDescription>30-day price movement for this prediction market</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="h-64 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  </div>
                ) : (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={priceHistory}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" />
                      <YAxis stroke="hsl(var(--muted-foreground))" domain={[0, 1]} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px'
                        }}
                        formatter={(value: any) => [`${(value * 100).toFixed(1)}%`, 'Probability']}
                      />
                      <Line
                        type="monotone"
                        dataKey="price"
                        stroke="hsl(var(--primary))"
                        strokeWidth={2}
                        dot={false}
                      />
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
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            prediction.prediction === 'Yes' 
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
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">This Week's Questions</h1>
        <p className="text-muted-foreground">Active prediction markets that LLM models are betting on</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {events.map((event) => (
          <Card
            key={event.id}
            className="cursor-pointer hover:shadow-lg transition-all duration-200 hover:scale-[1.02]"
            onClick={() => setSelectedEvent(event)}
          >
            <CardHeader>
              <div className="flex items-start justify-between mb-2">
                <CardTitle className="text-lg line-clamp-2">{event.title}</CardTitle>
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium flex-shrink-0 ml-2 ${
                  event.category === 'Crypto' ? 'bg-orange-100 text-orange-800' :
                  event.category === 'Politics' ? 'bg-blue-100 text-blue-800' :
                  event.category === 'Technology' ? 'bg-purple-100 text-purple-800' :
                  'bg-green-100 text-green-800'
                }`}>
                  {event.category}
                </span>
              </div>
              <CardDescription className="line-clamp-3">{event.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Probability</span>
                    <span className="font-medium">{(event.probability * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all"
                      style={{ width: `${event.probability * 100}%` }}
                    ></div>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center text-muted-foreground">
                    <DollarSign className="h-4 w-4 mr-1" />
                    ${(event.volume / 1000).toFixed(0)}K volume
                  </div>
                  <div className="flex items-center text-muted-foreground">
                    <Calendar className="h-4 w-4 mr-1" />
                    {event.endDate}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}