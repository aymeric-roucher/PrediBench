import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { LeaderboardEntry, ModelMarketDetails } from '../api'
import { apiService } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'

interface ModelsPageProps {
  leaderboard: LeaderboardEntry[]
}

// Utility function to merge market data for charts
function mergeMarketData(markets: any[], dataType: 'prices' | 'pnl_data') {
  const allDates = new Set<string>()
  const dataMap = new Map<string, any>()

  // Collect all unique dates and create a map for each market's data
  markets.forEach((market) => {
    const data = market[dataType] || []
    data.forEach((point: any) => {
      allDates.add(point.date)
      if (!dataMap.has(point.date)) {
        dataMap.set(point.date, { date: point.date })
      }
      const key = dataType === 'prices' ? `price_${market.market_id}` : `pnl_${market.market_id}`
      const value = dataType === 'prices' ? point.price : point.pnl
      dataMap.get(point.date)[key] = value

      // For PnL data, also include position information
      if (dataType === 'pnl_data') {
        const positionData = market.positions?.find((p: any) => p.date === point.date)
        if (positionData) {
          dataMap.get(point.date)[`position_${market.market_id}`] = positionData.position
        }
      }
    })
  })

  // Convert to array and sort by date
  return Array.from(dataMap.values()).sort((a, b) =>
    new Date(a.date).getTime() - new Date(b.date).getTime()
  )
}

const CustomPnLDot = (props: any) => {
  const { cx, cy, dataKey, payload } = props;

  // Extract market_id from dataKey (format: pnl_{market_id})
  const marketId = dataKey.split('_')[1];
  const positionKey = `position_${marketId}`;
  const position = payload[positionKey];

  // Return null if no position data
  if (position === undefined || position === null) {
    return null;
  }

  const size = 6;

  if (position > 0) {
    // Triangle up for positive position
    return (
      <svg>
        <polygon
          points={`${cx},${cy - size} ${cx - size},${cy + size} ${cx + size},${cy + size}`}
          fill={props.stroke}
          stroke={props.stroke}
          strokeWidth={1}
        />
      </svg>
    );
  } else if (position < 0) {
    // Triangle down for negative position
    return (
      <svg>
        <polygon
          points={`${cx},${cy + size} ${cx - size},${cy - size} ${cx + size},${cy - size}`}
          fill={props.stroke}
          stroke={props.stroke}
          strokeWidth={1}
        />
      </svg>
    );
  } else {
    // Empty circle for zero position
    return (
      <svg>
        <circle
          cx={cx}
          cy={cy}
          r={size}
          fill={props.stroke}
        />
      </svg>
    );
  }
};

export function ModelsPage({ leaderboard }: ModelsPageProps) {
  const [selectedModel, setSelectedModel] = useState<string>(leaderboard[0]?.id || '')
  const [marketDetails, setMarketDetails] = useState<ModelMarketDetails | null>(null)
  const [loading, setLoading] = useState(false)

  const selectedModelData = leaderboard.find(m => m.id === selectedModel)

  useEffect(() => {
    if (!selectedModel && leaderboard.length > 0) {
      setSelectedModel(leaderboard[0].id)
    }
  }, [leaderboard, selectedModel])

  useEffect(() => {
    if (selectedModel) {
      setLoading(true)
      apiService.getModelMarketDetails(selectedModel)
        .then(setMarketDetails)
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [selectedModel])

  const colors = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe', '#00c49f', '#ffbb28', '#ff8042']

  // Debug logging
  // if (marketDetails && marketDetails.markets.length > 0) {
  //   console.log('Market details:', {
  //     marketCount: marketDetails.markets.length,
  //     pnlCount: marketDetails.market_pnls.length,
  //     priceDataPoints: marketDetails.price_chart_data?.length,
  //     pnlDataPoints: marketDetails.pnl_chart_data?.length,
  //     marketInfo: marketDetails.market_info
  //   })
  // }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Model Performance</h1>
        <p className="text-muted-foreground">Detailed analysis of individual model performance</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Model Selection Sidebar */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Select Model</CardTitle>
              <CardDescription>Choose a model to view detailed performance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {leaderboard.map((model, index) => (
                  <button
                    key={model.id}
                    onClick={() => setSelectedModel(model.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${selectedModel === model.id
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50'
                      }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${index === 0 ? 'bg-yellow-100 text-yellow-800' :
                        index === 1 ? 'bg-slate-100 text-slate-800' :
                          index === 2 ? 'bg-orange-100 text-orange-800' :
                            'bg-muted text-muted-foreground'
                        }`}>
                        {index + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{model.model}</p>
                        <p className="text-sm text-muted-foreground">Score: {model.final_cumulative_pnl.toFixed(1)}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Model Details */}
        <div className="lg:col-span-3">
          {selectedModelData && (
            <>
              {/* Model Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Score</p>
                        <p className="text-2xl font-bold">{selectedModelData.final_cumulative_pnl.toFixed(1)}</p>
                      </div>
                      <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                        <span className="text-primary">🎯</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Accuracy</p>
                        <p className="text-2xl font-bold">{((selectedModelData.accuracy || 0) * 100).toFixed(0)}%</p>
                      </div>
                      <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                        <span className="text-green-600">✓</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Trades</p>
                        <p className="text-2xl font-bold">{selectedModelData.trades}</p>
                      </div>
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-blue-600">📊</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">Profit</p>
                        <p className="text-2xl font-bold text-green-600">${Math.round(selectedModelData.final_cumulative_pnl * 1000).toLocaleString()}</p>
                      </div>
                      <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                        <span className="text-green-600">💰</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Market Charts - Combined Price Evolution and PnL */}
              {marketDetails && Object.keys(marketDetails).length > 0 && (
                <Card className="mb-8">
                  <CardContent>
                    {/* Price Evolution Chart */}
                    <div className="mb-8">
                      <h3 className="text-lg font-semibold mb-4">Price Evolution</h3>
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={mergeMarketData(Object.values(marketDetails), 'prices')}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                            <XAxis
                              dataKey="date"
                              stroke="hsl(var(--muted-foreground))"
                            />
                            <YAxis
                              stroke="hsl(var(--muted-foreground))"
                              domain={[0, 1]}
                              label={{ value: 'Price', angle: -90, position: 'insideLeft' }}
                            />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '8px',
                                fontSize: '12px',
                                padding: '8px',
                                lineHeight: '1.2'
                              }}
                              labelFormatter={(value) => `Date: ${value}`}
                              formatter={(value: unknown, name: string) => {
                                if (value === null || value === undefined || value === 0.0) return null
                                return [
                                  typeof value === 'number' ? value.toFixed(3) : String(value),
                                  name
                                ]
                              }}
                            />
                            {Object.values(marketDetails).map((market, marketIndex) => {
                              const color = colors[marketIndex % colors.length]
                              const dataKey = `price_${market.market_id}`
                              return (
                                <Line
                                  key={`price_line_${market.market_id}`}
                                  type="monotone"
                                  dataKey={dataKey}
                                  stroke={color}
                                  strokeWidth={2}
                                  dot={false}
                                  connectNulls={false}
                                  name={market.question}
                                  activeDot={{ r: 6, strokeWidth: 2 }}
                                />
                              )
                            })}
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* PnL Chart */}
                    {Object.values(marketDetails).some(market => market.pnl_data && market.pnl_data.length > 0) && (
                      <div>
                        <h3 className="text-lg font-semibold mb-4">Cumulative PnL</h3>
                        <div className="h-80">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={mergeMarketData(Object.values(marketDetails).filter(m => m.pnl_data && m.pnl_data.length > 0), 'pnl_data')}>
                              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                              <XAxis
                                dataKey="date"
                                stroke="hsl(var(--muted-foreground))"
                              />
                              <YAxis
                                stroke="hsl(var(--muted-foreground))"
                                label={{ value: 'Cumulative PnL', angle: -90, position: 'insideLeft' }}
                              />
                              <Tooltip
                                contentStyle={{
                                  backgroundColor: 'hsl(var(--card))',
                                  border: '1px solid hsl(var(--border))',
                                  borderRadius: '8px',
                                  fontSize: '12px',
                                  padding: '8px',
                                  lineHeight: '1.2'
                                }}
                                labelFormatter={(value) => `Date: ${value}`}
                                formatter={(value: unknown, name: string) => {
                                  if (value === null || value === undefined || value === 0.0) return null
                                  return [
                                    typeof value === 'number' ? value.toFixed(3) : String(value),
                                    name
                                  ]
                                }}
                              />
                              {Object.values(marketDetails).map((market, marketIndex) => {
                                if (!market.pnl_data || market.pnl_data.length === 0) return null
                                const color = colors[marketIndex % colors.length]
                                const dataKey = `pnl_${market.market_id}`
                                return (
                                  <Line
                                    key={`pnl_line_${market.market_id}`}
                                    type="monotone"
                                    dataKey={dataKey}
                                    stroke={color}
                                    strokeWidth={2}
                                    dot={(props) => <CustomPnLDot {...props} dataKey={dataKey} stroke={color} />}
                                    connectNulls={false}
                                    name={market.question}
                                    activeDot={{ r: 6, strokeWidth: 2 }}
                                  />
                                )
                              })}
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    )}
                    {loading && <div className="text-center py-4">Loading market data...</div>}
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}