const API_BASE_URL = 'http://localhost:8080/api'

export interface LeaderboardEntry {
  id: string
  model: string
  score: number
  accuracy: number
  trades: number
  profit: number
  lastUpdated: string
  trend: 'up' | 'down' | 'stable'
  performanceHistory: { date: string; score: number }[]
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
  topScore: number
  avgAccuracy: number
  totalTrades: number
  totalProfit: number
}

class ApiService {
  private async fetchWithTimeout(url: string, options: RequestInit = {}, timeout = 5000): Promise<Response> {
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
    try {
      const response = await this.fetchWithTimeout(`${API_BASE_URL}/leaderboard`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.warn('Failed to fetch leaderboard from API, using fallback data:', error)
      return this.getFallbackLeaderboard()
    }
  }

  async getEvents(): Promise<Event[]> {
    try {
      const response = await this.fetchWithTimeout(`${API_BASE_URL}/events`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.warn('Failed to fetch events from API, using fallback data:', error)
      return this.getFallbackEvents()
    }
  }

  async getStats(): Promise<Stats> {
    try {
      const response = await this.fetchWithTimeout(`${API_BASE_URL}/stats`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.warn('Failed to fetch stats from API, using fallback data:', error)
      return this.getFallbackStats()
    }
  }

  async getModelDetails(modelId: string): Promise<LeaderboardEntry | null> {
    try {
      const response = await this.fetchWithTimeout(`${API_BASE_URL}/model/${modelId}`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.warn('Failed to fetch model details from API:', error)
      return null
    }
  }

  // Fallback data methods (for when API is not available)
  private getFallbackLeaderboard(): LeaderboardEntry[] {
    return [
      {
        id: '1',
        model: 'GPT-5',
        score: 94.2,
        accuracy: 0.87,
        trades: 124,
        profit: 15420,
        lastUpdated: '2025-08-19',
        trend: 'up',
        performanceHistory: [
          { date: '2025-08-15', score: 89.5 },
          { date: '2025-08-16', score: 91.2 },
          { date: '2025-08-17', score: 92.8 },
          { date: '2025-08-18', score: 93.1 },
          { date: '2025-08-19', score: 94.2 }
        ]
      },
      {
        id: '2',
        model: 'Claude-4',
        score: 92.8,
        accuracy: 0.85,
        trades: 118,
        profit: 12890,
        lastUpdated: '2025-08-19',
        trend: 'up',
        performanceHistory: [
          { date: '2025-08-15', score: 88.2 },
          { date: '2025-08-16', score: 89.7 },
          { date: '2025-08-17', score: 91.3 },
          { date: '2025-08-18', score: 92.1 },
          { date: '2025-08-19', score: 92.8 }
        ]
      },
      {
        id: '3',
        model: 'GPT-4o',
        score: 89.1,
        accuracy: 0.82,
        trades: 97,
        profit: 9750,
        lastUpdated: '2025-08-18',
        trend: 'stable',
        performanceHistory: [
          { date: '2025-08-15', score: 88.9 },
          { date: '2025-08-16', score: 89.5 },
          { date: '2025-08-17', score: 88.8 },
          { date: '2025-08-18', score: 89.1 },
          { date: '2025-08-19', score: 89.1 }
        ]
      },
      {
        id: '4',
        model: 'Gemini Pro',
        score: 86.5,
        accuracy: 0.79,
        trades: 89,
        profit: 7340,
        lastUpdated: '2025-08-18',
        trend: 'down',
        performanceHistory: [
          { date: '2025-08-15', score: 88.1 },
          { date: '2025-08-16', score: 87.5 },
          { date: '2025-08-17', score: 86.9 },
          { date: '2025-08-18', score: 86.5 },
          { date: '2025-08-19', score: 86.5 }
        ]
      }
    ]
  }

  private getFallbackEvents(): Event[] {
    return [
      {
        id: '1',
        title: 'Will Bitcoin reach $100K by end of 2025?',
        description: 'Bitcoin price prediction for end of year 2025',
        probability: 0.72,
        volume: 1250000,
        endDate: '2025-12-31',
        category: 'Crypto',
        status: 'active'
      },
      {
        id: '2',
        title: 'US Election 2028 - Democratic Nominee',
        description: 'Who will be the Democratic nominee for President in 2028?',
        probability: 0.45,
        volume: 890000,
        endDate: '2028-07-01',
        category: 'Politics',
        status: 'active'
      },
      {
        id: '3',
        title: 'AI Breakthrough in 2025',
        description: 'Will there be a major AI breakthrough announcement in 2025?',
        probability: 0.68,
        volume: 675000,
        endDate: '2025-12-31',
        category: 'Technology',
        status: 'active'
      },
      {
        id: '4',
        title: 'Climate Goals Met by 2030',
        description: 'Will global climate targets be achieved by 2030?',
        probability: 0.23,
        volume: 445000,
        endDate: '2030-12-31',
        category: 'Environment',
        status: 'active'
      }
    ]
  }

  private getFallbackStats(): Stats {
    const leaderboard = this.getFallbackLeaderboard()
    return {
      topScore: Math.max(...leaderboard.map(entry => entry.score)),
      avgAccuracy: leaderboard.reduce((sum, entry) => sum + entry.accuracy, 0) / leaderboard.length,
      totalTrades: leaderboard.reduce((sum, entry) => sum + entry.trades, 0),
      totalProfit: leaderboard.reduce((sum, entry) => sum + entry.profit, 0)
    }
  }
}

export const apiService = new ApiService()