import { Calendar } from 'lucide-react'
import type { Event, LeaderboardEntry } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'

interface EventDetailProps {
  event: Event
  leaderboard: LeaderboardEntry[]
}

export function EventDetail({ event, leaderboard }: EventDetailProps) {
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
          <Card>
            <CardHeader>
              <CardTitle>Event Information</CardTitle>
              <CardDescription>Prediction market details and statistics</CardDescription>
            </CardHeader>
            <CardContent>
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