<<<<<<< Updated upstream
import { Calendar } from 'lucide-react'
=======
import { ExternalLink, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
>>>>>>> Stashed changes
import type { Event, LeaderboardEntry } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'

interface EventDetailProps {
  event: Event
  leaderboard: LeaderboardEntry[]
}

<<<<<<< Updated upstream
export function EventDetail({ event, leaderboard }: EventDetailProps) {
=======
interface PriceData {
  date: string
  price: number
  marketId?: string
  marketName?: string
}



interface MarketInvestmentDecision {
  market_id: string
  agent_name: string
  bet: number
  odds: number
  rationale: string
}

export function EventDetail({ event, leaderboard }: EventDetailProps) {
  const [marketPricesData, setMarketPricesData] = useState<{ [marketId: string]: PriceData[] }>({})
  const [investmentDecisions, setInvestmentDecisions] = useState<MarketInvestmentDecision[]>([])
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
      const [marketPrices, investmentDecisions] = await Promise.all([
        fetch(`http://localhost:8080/api/event/${eventId}/market_prices`).then(r => r.json()),
        fetch(`http://localhost:8080/api/event/${eventId}/investment_decisions`).then(r => r.json())
      ])

      // Transform market prices data from {marketId: {date: price}} to {marketId: [{date, price}]}
      const transformedPrices: { [marketId: string]: PriceData[] } = {}
      Object.entries(marketPrices).forEach(([marketId, pricesByDate]) => {
        transformedPrices[marketId] = Object.entries(pricesByDate as Record<string, number>).map(([date, price]) => ({
          date,
          price,
          marketId
        }))
      })

      setMarketPricesData(transformedPrices)
      setInvestmentDecisions(investmentDecisions)
    } catch (error) {
      console.error('Error loading event details:', error)
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    if (event) {
      loadEventDetails(event.id)
    }
  }, [event])
>>>>>>> Stashed changes
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <button
          onClick={() => window.history.back()}
          className="text-muted-foreground hover:text-foreground mb-4 text-sm"
        >
          ← Back to Events
        </button>
        <h1 className="text-3xl font-bold mb-2">{event.title}</h1>
        <p className="text-muted-foreground text-lg">{event.description}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Event Details */}
        <div className="lg:col-span-2">
<<<<<<< Updated upstream
=======
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
>>>>>>> Stashed changes
          <Card>
            <CardHeader>
              <CardTitle>Event Information</CardTitle>
              <CardDescription>Prediction market details and statistics</CardDescription>
            </CardHeader>
            <CardContent>
<<<<<<< Updated upstream
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-semibold mb-2">Market Details</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Markets:</span>
                      <span>{event.markets?.length || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Volume:</span>
                      <span>{event.volume ? `$${(event.volume / 1000).toFixed(0)}K` : 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Liquidity:</span>
                      <span>{event.liquidity ? `$${(event.liquidity / 1000).toFixed(0)}K` : 'N/A'}</span>
                    </div>
                  </div>
=======
              {loading ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : (
                <div className="w-full">
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
                        <span className="text-sm text-muted-foreground">
                          {market.question.length > 50 ? market.question.substring(0, 47) + '...' : market.question}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="w-full h-96">
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
>>>>>>> Stashed changes
                </div>

                <div>
                  <h3 className="font-semibold mb-2">Timeline</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center">
                      <Calendar className="h-4 w-4 mr-2 text-muted-foreground" />
                      <span className="text-muted-foreground">End Date:</span>
                      <span className="ml-2">
                        {event.end_datetime 
                          ? new Date(event.end_datetime).toLocaleDateString()
                          : 'No end date'
                        }
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

<<<<<<< Updated upstream
          {/* Markets */}
          {event.markets && event.markets.length > 0 && (
            <Card className="mt-8">
              <CardHeader>
                <CardTitle>Markets</CardTitle>
                <CardDescription>Individual betting markets for this event</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {event.markets.map((market, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <h4 className="font-medium mb-2">{market.question || `Market ${index + 1}`}</h4>
                      <p className="text-sm text-muted-foreground">{market.description || 'No description available'}</p>
                    </div>
                  ))}
=======
        {/* Latest Model Predictions */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>LatestModel Predictions</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">Model</th>
                        <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">Bet</th>
                        <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {investmentDecisions.map((investmentDecision, index) => (
                        <tr key={index} className={`${index % 2 === 1 ? 'bg-muted/50' : ''}`}>
                          <td className="py-3 px-3 font-medium">{investmentDecision.agent_name}</td>
                          <td className="py-3 px-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${investmentDecision.bet < 0
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                              }`}>
                              {investmentDecision.bet.toFixed(2)}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-muted-foreground">{(investmentDecision.odds * 100).toFixed(0)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
>>>>>>> Stashed changes
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Model Performance */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Model Performance</CardTitle>
              <CardDescription>How models performed on this event</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {leaderboard.slice(0, 5).map((model, index) => (
                  <div key={model.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        index === 0 ? 'bg-yellow-100 text-yellow-800' :
                        index === 1 ? 'bg-slate-100 text-slate-800' :
                        index === 2 ? 'bg-orange-100 text-orange-800' :
                        'bg-muted text-muted-foreground'
                      }`}>
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium text-sm">{model.model}</p>
                        <p className="text-xs text-muted-foreground">{model.trades} trades</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold">{model.final_cumulative_pnl.toFixed(1)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}