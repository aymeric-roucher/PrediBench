import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { AuthModal } from './AuthModal'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Upload, User, CheckCircle, AlertCircle } from 'lucide-react'

interface SubmissionPageProps {
  events: any[]
}

export function SubmissionPage({ events }: SubmissionPageProps) {
  const { currentUser } = useAuth()
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  
  // Form state
  const [agentName, setAgentName] = useState('')
  const [selectedEventId, setSelectedEventId] = useState('')
  const [selectedDate, setSelectedDate] = useState('')
  const [jsonData, setJsonData] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState<{type: 'success' | 'error', message: string} | null>(null)

  const handleAuthRequired = (mode: 'login' | 'register') => {
    setAuthMode(mode)
    setShowAuthModal(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentUser) {
      handleAuthRequired('login')
      return
    }

    setIsSubmitting(true)
    setSubmitResult(null)

    try {
      // Validate JSON
      let parsedJson
      try {
        parsedJson = JSON.parse(jsonData)
      } catch {
        throw new Error('Invalid JSON format in decisions data')
      }

      // Get user's auth token
      const token = await currentUser.getIdToken()

      const response = await fetch('/api/submissions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          agent_name: agentName,
          date: selectedDate,
          event_id: selectedEventId,
          decisions_per_market: jsonData
        })
      })

      const result = await response.json()

      if (response.ok) {
        setSubmitResult({
          type: 'success',
          message: `Submission successful! ID: ${result.submission_id}`
        })
        // Clear form
        setAgentName('')
        setSelectedEventId('')
        setSelectedDate('')
        setJsonData('')
      } else {
        setSubmitResult({
          type: 'error',
          message: result.detail || 'Submission failed'
        })
      }
    } catch (error: any) {
      setSubmitResult({
        type: 'error',
        message: error.message || 'Network error occurred'
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const exampleJson = `[
  {
    "market_id": "21742633143463906290569050155826241533067272736897614950488156847949938836455",
    "model_decision": {
      "bet": 0.65,
      "odds": 1.54,
      "rationale": "Based on polling data and recent trends, I believe this outcome is likely."
    }
  }
]`

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-6 w-6" />
              Submit Your Model Results
            </CardTitle>
            <CardDescription>
              Submit your LLM model's prediction results to appear on the community leaderboard.
              {!currentUser && ' You need to sign in to submit results.'}
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            {!currentUser ? (
              <div className="text-center py-8">
                <User className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">Authentication Required</h3>
                <p className="text-muted-foreground mb-4">
                  Please sign in or create an account to submit your model results.
                </p>
                <div className="flex gap-2 justify-center">
                  <Button onClick={() => handleAuthRequired('login')}>
                    Sign In
                  </Button>
                  <Button variant="outline" onClick={() => handleAuthRequired('register')}>
                    Create Account
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-sm text-green-700">
                    ✓ Signed in as <strong>{currentUser.displayName || currentUser.email}</strong>
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label htmlFor="agentName" className="block text-sm font-medium mb-2">
                        Model/Agent Name *
                      </label>
                      <input
                        id="agentName"
                        type="text"
                        value={agentName}
                        onChange={(e) => setAgentName(e.target.value)}
                        placeholder="e.g., my-custom-gpt4o"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>

                    <div>
                      <label htmlFor="eventId" className="block text-sm font-medium mb-2">
                        Event *
                      </label>
                      <select
                        id="eventId"
                        value={selectedEventId}
                        onChange={(e) => setSelectedEventId(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      >
                        <option value="">Select an event</option>
                        {events.slice(0, 10).map((event) => (
                          <option key={event.id} value={event.id}>
                            {event.title?.substring(0, 60) || 'Untitled Event'}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label htmlFor="date" className="block text-sm font-medium mb-2">
                      Prediction Date *
                    </label>
                    <input
                      id="date"
                      type="date"
                      value={selectedDate}
                      onChange={(e) => setSelectedDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>

                  <div>
                    <label htmlFor="jsonData" className="block text-sm font-medium mb-2">
                      Market Decisions (JSON) *
                    </label>
                    <textarea
                      id="jsonData"
                      value={jsonData}
                      onChange={(e) => setJsonData(e.target.value)}
                      placeholder={exampleJson}
                      rows={12}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      required
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Format: Array of objects with market_id and model_decision (bet, odds, rationale)
                    </p>
                  </div>

                  {submitResult && (
                    <div className={`flex items-start gap-2 p-4 rounded-lg ${
                      submitResult.type === 'success' 
                        ? 'bg-green-50 border border-green-200' 
                        : 'bg-red-50 border border-red-200'
                    }`}>
                      {submitResult.type === 'success' ? (
                        <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                      ) : (
                        <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                      )}
                      <p className={`text-sm ${
                        submitResult.type === 'success' ? 'text-green-700' : 'text-red-700'
                      }`}>
                        {submitResult.message}
                      </p>
                    </div>
                  )}

                  <div className="flex justify-end">
                    <Button type="submit" disabled={isSubmitting}>
                      {isSubmitting ? 'Submitting...' : 'Submit Results'}
                    </Button>
                  </div>
                </form>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Info Card */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Submission Guidelines</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-medium mb-2">Data Format</h4>
              <p className="text-sm text-muted-foreground">
                Submit your predictions as a JSON array where each object contains a market_id and model_decision with bet (0-1), odds, and rationale.
              </p>
            </div>
            <div>
              <h4 className="font-medium mb-2">Validation</h4>
              <p className="text-sm text-muted-foreground">
                All submissions are validated for correct format. Ensure your market IDs exist and your bet values are between 0 and 1.
              </p>
            </div>
            <div>
              <h4 className="font-medium mb-2">Leaderboard</h4>
              <p className="text-sm text-muted-foreground">
                Submitted results will appear in the community section of the leaderboard once processed.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        mode={authMode}
        onSwitchMode={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
      />
    </div>
  )
}