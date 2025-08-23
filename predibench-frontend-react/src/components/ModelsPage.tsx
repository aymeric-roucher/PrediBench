import { useEffect, useState } from 'react'
import type { LeaderboardEntry, ModelMarketDetails } from '../api'
import { apiService } from '../api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { VisxLineChart } from './ui/visx-line-chart'
import { VisxPnLChart } from './ui/visx-pnl-chart'
import { getChartColor } from './ui/chart-colors'

interface ModelsPageProps {
  leaderboard: LeaderboardEntry[]
}


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
                        <VisxLineChart
                          height={320}
                          margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                          yDomain={[0, 1]}
                          series={Object.values(marketDetails).map((market, marketIndex) => ({
                            dataKey: `price_${market.market_id}`,
                            data: (market.prices || []).map(point => ({
                              x: point.date,
                              y: point.price
                            })),
                            stroke: getChartColor(marketIndex),
                            name: market.question
                          }))}
                        />
                      </div>
                    </div>

                    {/* PnL Chart */}
                    {Object.values(marketDetails).some(market => market.pnl_data && market.pnl_data.length > 0) && (
                      <div>
                        <h3 className="text-lg font-semibold mb-4">Cumulative PnL</h3>
                        <div className="h-80">
                          <VisxPnLChart
                            height={320}
                            margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                            series={Object.values(marketDetails)
                              .filter(market => market.pnl_data && market.pnl_data.length > 0)
                              .map((market, marketIndex) => ({
                                dataKey: `pnl_${market.market_id}`,
                                data: (market.pnl_data || []).map(point => {
                                  const positionData = market.positions?.find((p: { date: string }) => p.date === point.date)
                                  return {
                                    x: point.date,
                                    y: point.pnl,
                                    position: positionData?.position
                                  }
                                }),
                                stroke: getChartColor(marketIndex),
                                name: market.question
                              }))}
                          />
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