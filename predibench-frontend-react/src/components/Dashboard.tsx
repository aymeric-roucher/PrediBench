import { useState, useEffect } from 'react'
import { Button } from './ui/button'
import { Card } from './ui/card'
import { Copy, RefreshCw, Plus, Trash2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { apiService, type Agent } from '../api'
import { submissionService, type PredictionSubmission } from '../apiSubmission'

// Code examples for different languages
const getCodeExamples = (agentToken = 'YOUR_AGENT_TOKEN') => ({
  curl: `curl -X POST http://localhost:8080/api/submit \\
  -H "Authorization: Bearer ${agentToken}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "event_id": "event_123",
    "market_decisions": [
      {
        "market_id": "market_456",
        "bet": 0.7,
        "odds": 1.5,
        "rationale": "Analysis shows positive trend"
      }
    ],
    "rationale": "Overall market conditions look favorable"
  }'`,
  
  python: `import requests
import json

# Your agent token
token = "${agentToken}"

# Prediction data
prediction = {
    "event_id": "event_123",
    "market_decisions": [
        {
            "market_id": "market_456",
            "bet": 0.7,
            "odds": 1.5,
            "rationale": "Analysis shows positive trend"
        }
    ],
    "rationale": "Overall market conditions look favorable"
}

# Make the request
response = requests.post(
    "http://localhost:8080/api/submit",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    json=prediction
)

# Check response
if response.status_code == 200:
    result = response.json()
    print(f"Success: {result['message']}")
else:
    print(f"Error: {response.text}")`,

  javascript: `// Your agent token
const token = "${agentToken}";

// Prediction data
const prediction = {
  event_id: "event_123",
  market_decisions: [
    {
      market_id: "market_456",
      bet: 0.7,
      odds: 1.5,
      rationale: "Analysis shows positive trend"
    }
  ],
  rationale: "Overall market conditions look favorable"
};

// Make the request
async function submitPrediction() {
  try {
    const response = await fetch("http://localhost:8080/api/submit", {
      method: "POST",
      headers: {
        "Authorization": \`Bearer \${token}\`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(prediction)
    });

    if (response.ok) {
      const result = await response.json();
      console.log(\`Success: \${result.message}\`);
    } else {
      const error = await response.text();
      console.error(\`Error: \${error}\`);
    }
  } catch (error) {
    console.error("Request failed:", error);
  }
}

// Call the function
submitPrediction();`
})


export function Dashboard() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [newAgentName, setNewAgentName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [loading, setLoading] = useState(true)
  const { currentUser } = useAuth()

  useEffect(() => {
    if (!currentUser) return

    loadAgents()
  }, [currentUser])

  const loadAgents = async () => {
    if (!currentUser) return
    
    try {
      setLoading(true)
      const agentsData = await apiService.getAgents()
      setAgents(agentsData)
    } catch (error) {
      console.error('Error loading agents:', error)
    } finally {
      setLoading(false)
    }
  }

  const createAgent = async () => {
    if (!newAgentName.trim() || !currentUser) return

    try {
      const newAgent = await apiService.createAgent({
        name: newAgentName.trim()
      })
      
      // Add to local state
      setAgents(prev => [...prev, newAgent])
      
      setNewAgentName('')
      setIsCreating(false)
    } catch (error) {
      console.error('Error creating agent:', error)
    }
  }

  const regenerateToken = async (agentId: string) => {
    if (!currentUser) return

    try {
      const updatedAgent = await apiService.regenerateAgentToken(agentId)
      
      // Update local state
      setAgents(prev => prev.map(agent => 
        agent.id === agentId ? updatedAgent : agent
      ))
    } catch (error) {
      console.error('Error regenerating token:', error)
    }
  }

  const deleteAgent = async (agentId: string) => {
    if (!currentUser) return

    try {
      await apiService.deleteAgent(agentId)
      
      // Remove from local state
      setAgents(prev => prev.filter(agent => agent.id !== agentId))
    } catch (error) {
      console.error('Error deleting agent:', error)
    }
  }

  const copyToken = async (token: string) => {
    try {
      await navigator.clipboard.writeText(token)
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy token:', err)
    }
  }

  if (!currentUser) {
    return (
      <div className="container mx-auto px-6 py-8 text-center">
        <h1 className="text-3xl font-bold mb-4">Agent Dashboard</h1>
        <p className="text-muted-foreground mb-4">
          Please log in to create and manage your agents.
        </p>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Agent Dashboard</h1>
        <p className="text-muted-foreground">
          Create and manage your agents. Each agent gets a unique token for API submissions.
        </p>
      </div>

      {!loading && (
        <>
          {/* Create New Agent */}
          <Card className="p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Create New Agent</h2>
        {!isCreating ? (
          <Button onClick={() => setIsCreating(true)} className="flex items-center gap-2">
            <Plus size={16} />
            Add Agent
          </Button>
        ) : (
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={newAgentName}
              onChange={(e) => setNewAgentName(e.target.value)}
              placeholder="Enter agent name"
              className="px-3 py-2 border border-input rounded-md flex-1"
              onKeyDown={(e) => e.key === 'Enter' && createAgent()}
              autoFocus
            />
            <Button onClick={createAgent} disabled={!newAgentName.trim()}>
              Create
            </Button>
            <Button variant="outline" onClick={() => {
              setIsCreating(false)
              setNewAgentName('')
            }}>
              Cancel
            </Button>
          </div>
        )}
      </Card>

      {/* Agents List */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Your Agents ({agents.length})</h2>
        
        {agents.length === 0 ? (
          <Card className="p-8 text-center">
            <p className="text-muted-foreground">No agents created yet. Create your first agent to get started.</p>
          </Card>
        ) : (
          agents.map((agent) => (
            <Card key={agent.id} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-lg">{agent.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    Created {new Date(agent.created_at).toLocaleDateString()}
                    {agent.last_used && (
                      <span> • Last used {new Date(agent.last_used).toLocaleDateString()}</span>
                    )}
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    <code className="bg-muted px-2 py-1 rounded text-sm font-mono">
                      {agent.token}
                    </code>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToken(agent.token)}
                      className="flex items-center gap-1"
                    >
                      <Copy size={14} />
                      Copy
                    </Button>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => regenerateToken(agent.id)}
                    className="flex items-center gap-1"
                  >
                    <RefreshCw size={14} />
                    Regenerate
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => deleteAgent(agent.id)}
                    className="flex items-center gap-1"
                  >
                    <Trash2 size={14} />
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      {agents.length > 0 && (
        <Card className="p-4 mt-6 bg-muted/50">
          <h3 className="font-semibold mb-2">API Usage</h3>
          <p className="text-sm text-muted-foreground mb-2">
            Use your agent token in API requests:
          </p>
          
          <CodeExamplesSection agents={agents} />
          
          <div className="mt-6">
            <h4 className="font-medium mb-2">Test Submission</h4>
            <TestSubmission agents={agents} />
          </div>
        </Card>
      )}
      </>
      )}

      {loading && (
        <div className="text-center py-8">
          <p className="text-muted-foreground">Loading your agents...</p>
        </div>
      )}
    </div>
  )
}

function CodeExamplesSection({ agents }: { agents: Agent[] }) {
  const [selectedLanguage, setSelectedLanguage] = useState<'curl' | 'python' | 'javascript'>('curl')
  const [selectedAgent, setSelectedAgent] = useState('')

  const languages = [
    { id: 'curl' as const, name: 'cURL', icon: '$' },
    { id: 'python' as const, name: 'Python', icon: '🐍' },
    { id: 'javascript' as const, name: 'JavaScript', icon: '🟨' }
  ]

  const getTokenForExample = () => {
    if (!selectedAgent) return 'YOUR_AGENT_TOKEN'
    const agent = agents.find(a => a.id === selectedAgent)
    return agent?.token || 'YOUR_AGENT_TOKEN'
  }

  const codeExamples = getCodeExamples(getTokenForExample())

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(codeExamples[selectedLanguage])
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy code:', err)
    }
  }

  return (
    <div className="space-y-3">
      {/* Agent and Language Selectors */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Agent:</label>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="px-3 py-1 border border-input rounded text-sm"
          >
            <option value="">Select Agent for Token</option>
            {agents.map(agent => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </div>
        
        <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
          {languages.map(lang => (
            <button
              key={lang.id}
              onClick={() => setSelectedLanguage(lang.id)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                selectedLanguage === lang.id
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <span className="mr-1">{lang.icon}</span>
              {lang.name}
            </button>
          ))}
        </div>
      </div>

      {/* Code Block */}
      <div className="relative">
        <code className="block bg-background p-4 rounded text-sm whitespace-pre overflow-x-auto">
          {codeExamples[selectedLanguage]}
        </code>
        <Button
          variant="outline"
          size="sm"
          onClick={copyCode}
          className="absolute top-2 right-2 flex items-center gap-1"
        >
          <Copy size={14} />
          Copy
        </Button>
      </div>
    </div>
  )
}

function TestSubmission({ agents }: { agents: Agent[] }) {
  const [selectedAgent, setSelectedAgent] = useState('')
  const [eventId, setEventId] = useState('test_event_123')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState<string | null>(null)

  const testSubmission = async () => {
    if (!selectedAgent) return

    const agent = agents.find(a => a.id === selectedAgent)
    if (!agent) return

    setIsSubmitting(true)
    setSubmitResult(null)

    try {
      const submission: PredictionSubmission = {
        event_id: eventId,
        market_decisions: [
          {
            market_id: 'test_market_456',
            bet: 0.7,
            odds: 1.5,
            rationale: 'Test prediction from dashboard'
          }
        ],
        rationale: 'This is a test submission from the dashboard'
      }

      const result = await submissionService.submitPrediction(submission, agent.token)
      setSubmitResult(`✅ Success: ${result.message}`)
    } catch (error) {
      setSubmitResult(`❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <select
          value={selectedAgent}
          onChange={(e) => setSelectedAgent(e.target.value)}
          className="px-3 py-2 border border-input rounded-md text-sm"
        >
          <option value="">Select Agent</option>
          {agents.map(agent => (
            <option key={agent.id} value={agent.id}>
              {agent.name}
            </option>
          ))}
        </select>
        
        <input
          type="text"
          value={eventId}
          onChange={(e) => setEventId(e.target.value)}
          placeholder="Event ID"
          className="px-3 py-2 border border-input rounded-md text-sm"
        />
        
        <Button
          onClick={testSubmission}
          disabled={!selectedAgent || isSubmitting}
          size="sm"
        >
          {isSubmitting ? 'Submitting...' : 'Test Submit'}
        </Button>
      </div>
      
      {submitResult && (
        <div className="p-3 bg-muted rounded text-sm font-mono">
          {submitResult}
        </div>
      )}
    </div>
  )
}