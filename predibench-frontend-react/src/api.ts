const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api'

export interface LeaderboardEntry {
  id: string
  model: string
  final_cumulative_pnl: number
  trades: number
  accuracy: number
  lastUpdated: string
  trend: 'up' | 'down' | 'stable'
  pnl_history: { date: string; value: number }[]
}

export interface MarketData {
  market_id: string
  question: string
  prices: { date: string; price: number }[]
  positions: { date: string; position: number }[]
  pnl_data: { date: string; pnl: number }[]
}


export interface ModelMarketDetails {
  [marketId: string]: MarketData
}

export interface Market {
  id: string
  question: string
  slug: string
  description: string
  outcomes: MarketOutcome[]
}

export interface MarketOutcome {
  name: string
  price: number
}

export interface Event {
  id: string
  slug: string
  title: string
  description: string | null
  start_datetime: string | null
  end_datetime: string | null
  creation_datetime: string
  volume: number | null
  volume24hr: number | null
  volume1wk: number | null
  volume1mo: number | null
  volume1yr: number | null
  liquidity: number | null
  markets: Market[]
}

export interface Stats {
  topFinalCumulativePnl: number
  avgPnl: number
  totalTrades: number
  totalProfit: number
}

// Agent Management Types
export interface Agent {
  id: string
  name: string
  token: string
  created_at: string
  last_used?: string
}

export interface AgentCreate {
  name: string
}

export interface PredictionSubmission {
  event_id: string
  market_decisions: MarketDecision[]
  rationale?: string
}

export interface MarketDecision {
  market_id: string
  bet: number
  odds: number
  rationale: string
}

export interface SubmissionResponse {
  success: boolean
  message: string
  submission_id?: string
  agent_name?: string
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

  private async getAuthToken(): Promise<string | null> {
    // Get Firebase user token
    const { auth } = await import('./lib/firebase')
    const user = auth.currentUser
    if (!user) return null
    
    return await user.getIdToken()
  }

  private async fetchAuthenticated(url: string, options: RequestInit = {}): Promise<Response> {
    const token = await this.getAuthToken()
    if (!token) {
      throw new Error('User not authenticated')
    }

    return this.fetchWithTimeout(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers,
      },
    })
  }

  async getLeaderboard(): Promise<LeaderboardEntry[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/leaderboard`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getEvents(params?: {
    search?: string
    category?: string
    sort_by?: string
    order?: string
    limit?: number
  }): Promise<Event[]> {
    const searchParams = new URLSearchParams()
    if (params?.search) searchParams.append('search', params.search)
    if (params?.category) searchParams.append('category', params.category)
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by)
    if (params?.order) searchParams.append('order', params.order)
    if (params?.limit) searchParams.append('limit', params.limit.toString())

    const url = `${API_BASE_URL}/events${searchParams.toString() ? `?${searchParams.toString()}` : ''}`
    const response = await this.fetchWithTimeout(url)
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

  async getModelMarketDetails(modelId: string): Promise<ModelMarketDetails> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/model/${modelId}/pnl`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getEventDetails(eventId: string): Promise<Event> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/event/${eventId}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getEventMarketPrices(eventId: string): Promise<{ [marketId: string]: { date: string; price: number }[] }> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/event/${eventId}/market_prices`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  // Agent Management Methods
  async getAgents(): Promise<Agent[]> {
    const response = await this.fetchAuthenticated(`${API_BASE_URL}/agents`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async createAgent(agentData: AgentCreate): Promise<Agent> {
    const response = await this.fetchAuthenticated(`${API_BASE_URL}/agents`, {
      method: 'POST',
      body: JSON.stringify(agentData),
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`HTTP error! status: ${response.status}, message: ${error}`)
    }
    return await response.json()
  }

  async regenerateAgentToken(agentId: string): Promise<Agent> {
    const response = await this.fetchAuthenticated(`${API_BASE_URL}/agents/${agentId}/regenerate-token`, {
      method: 'PUT',
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`HTTP error! status: ${response.status}, message: ${error}`)
    }
    return await response.json()
  }

  async deleteAgent(agentId: string): Promise<{ message: string }> {
    const response = await this.fetchAuthenticated(`${API_BASE_URL}/agents/${agentId}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`HTTP error! status: ${response.status}, message: ${error}`)
    }
    return await response.json()
  }

  // Prediction Submission
  async submitPrediction(submission: PredictionSubmission, agentToken: string): Promise<SubmissionResponse> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${agentToken}`,
      },
      body: JSON.stringify(submission),
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`HTTP error! status: ${response.status}, message: ${error}`)
    }
    return await response.json()
  }
}

export const apiService = new ApiService()