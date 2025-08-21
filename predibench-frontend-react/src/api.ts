const API_BASE_URL = 'http://localhost:8080/api'

export interface LeaderboardEntry {
  id: string
  model: string
  final_cumulative_pnl: number
  trades: number
  lastUpdated: string
  trend: 'up' | 'down' | 'stable'
  performanceHistory: { date: string; cumulative_pnl: number }[]
}

export interface Event {
  id: string
  title: string
  description: string
  probability: number
  volume: number
  endDate: string
  category: string
  status: 'active' | 'resolved'
}

export interface Stats {
  topFinalCumulativePnl: number
  avgPnl: number
  totalTrades: number
  totalProfit: number
}

class ApiService {
  private async fetchWithTimeout(url: string, options: RequestInit = {}, timeout = 30000): Promise<Response> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      return response
    } catch (error) {
      clearTimeout(timeoutId)
      throw error
    }
  }

  async getLeaderboard(): Promise<LeaderboardEntry[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/leaderboard`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getEvents(): Promise<Event[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/events`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getStats(): Promise<Stats> {

    const response = await this.fetchWithTimeout(`${API_BASE_URL}/stats`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()

  }

  async getModelDetails(modelId: string): Promise<LeaderboardEntry | null> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/model/${modelId}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }
}

export const apiService = new ApiService()