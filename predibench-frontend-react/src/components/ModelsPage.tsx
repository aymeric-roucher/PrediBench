import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import type { LeaderboardEntry, ModelMarketDetails } from '../api'
import { apiService } from '../api'
import { VisxLineChart } from './ui/visx-line-chart'
import { VisxPnLChart } from './ui/visx-pnl-chart'
import { getChartColor } from './ui/chart-colors'

interface ModelsPageProps {
  leaderboard: LeaderboardEntry[]
}


export function ModelsPage({ leaderboard }: ModelsPageProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const [selectedModel, setSelectedModel] = useState<string>(leaderboard[0]?.id || '')
  const [marketDetails, setMarketDetails] = useState<ModelMarketDetails | null>(null)
  const [loading, setLoading] = useState(false)

  const selectedModelData = leaderboard.find(m => m.id === selectedModel)

  useEffect(() => {
    const urlParams = new URLSearchParams(location.search)
    const selectedFromUrl = urlParams.get('selected')
    
    if (selectedFromUrl && leaderboard.find(m => m.id === selectedFromUrl)) {
      setSelectedModel(selectedFromUrl)
    } else if (!selectedModel && leaderboard.length > 0) {
      setSelectedModel(leaderboard[0].id)
    }
  }, [leaderboard, selectedModel, location.search])

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

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-0">
        {/* Model Selection Sidebar */}
        <div className="lg:col-span-1">
          <div className="space-y-2">
                {leaderboard.map((model, index) => {
                  const handleModelSelect = (modelId: string) => {
                    setSelectedModel(modelId)
                    navigate(`/models?selected=${modelId}`, { replace: true })
                  }
                  
                  return (
                    <button
                      key={model.id}
                      onClick={() => handleModelSelect(model.id)}
                      className={`group w-full text-left p-4 rounded-xl border transition-all duration-200 ${selectedModel === model.id
                        ? 'border-gray-400 shadow-lg bg-card'
                        : 'border-border/30 hover:border-gray-300 hover:shadow-md bg-card'
                      }`}
                    >
                      <div className="flex items-center space-x-4">
                        <div className={`flex items-center justify-center w-10 h-10 rounded-full text-xs font-bold transition-transform group-hover:scale-105 ${
                          index === 0 ? 'bg-gradient-to-br from-yellow-100 to-yellow-50 text-yellow-800 shadow-md shadow-yellow-200/50' :
                          index === 1 ? 'bg-gradient-to-br from-slate-100 to-slate-50 text-slate-800 shadow-md shadow-slate-200/50' :
                          index === 2 ? 'bg-gradient-to-br from-amber-100 to-amber-50 text-amber-800 shadow-md shadow-amber-200/50' :
                          'bg-gradient-to-br from-muted to-muted/70 text-muted-foreground shadow-sm'
                        }`}>
                          {index + 1}
                        </div>
                        <div className="flex-1 min-w-0 space-y-1">
                          <p className={`font-semibold truncate transition-colors ${
                            selectedModel === model.id ? 'text-gray-700' : 'text-foreground group-hover:text-gray-600'
                          }`}>{model.model}</p>
                          <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground mt-1">
                            <div>Total PnL: {model.final_cumulative_pnl.toFixed(1)}</div>
                            <div>Accuracy: {((model.accuracy || 0) * 100).toFixed(0)}%</div>
                            <div>Trades: {model.trades}</div>
                            <div>Brier Score: ${Math.round(model.final_cumulative_pnl * 1000).toLocaleString()}</div>
                          </div>
                        </div>
                      </div>
                    </button>
                  )
                })}
          </div>
        </div>

        {/* Model Details */}
        <div className="lg:col-span-3 relative">
          {/* Border overlay that hides at selected model intersection */}
          <div className="absolute inset-0 border rounded-xl border-border/30 pointer-events-none" />
          {selectedModelData && (
            <>

              {/* Market Charts - Combined Price Evolution and PnL */}
              {marketDetails && Object.keys(marketDetails).length > 0 && (
                <div className="p-6 bg-card rounded-xl relative z-10">
                  <div>
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
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}