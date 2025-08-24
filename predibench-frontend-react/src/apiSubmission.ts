const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api'

// Simplified submission types matching backend structure
export interface SimpleMarketDecision {
  market_id: string
  bet: number  // Model's bet on this market (-1.0 to 1.0)
}

export interface SimpleEventDecision {
  event_id: string
  market_decisions: SimpleMarketDecision[]
}

export interface AgentSubmission {
  event_decisions: SimpleEventDecision[]
}

// Legacy types for backward compatibility (can be removed later)
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

class SubmissionService {
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

  // New simplified submission method
  async submitAgentPrediction(submission: AgentSubmission, agentToken: string): Promise<SubmissionResponse> {
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

  // Legacy prediction submission (for backward compatibility - can be removed later)
  async submitPrediction(submission: PredictionSubmission, agentToken: string): Promise<SubmissionResponse> {
    // Convert legacy format to new format
    const agentSubmission: AgentSubmission = {
      event_decisions: [{
        event_id: submission.event_id,
        market_decisions: submission.market_decisions.map(md => ({
          market_id: md.market_id,
          bet: md.bet
        }))
      }]
    }
    
    return this.submitAgentPrediction(agentSubmission, agentToken)
  }

  // Get submissions for a user (if needed in the future)
  async getUserSubmissions(userToken: string): Promise<any[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/submissions`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userToken}`,
      },
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`HTTP error! status: ${response.status}, message: ${error}`)
    }
    return await response.json()
  }
}

export const submissionService = new SubmissionService()