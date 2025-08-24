import { useState, useEffect } from 'react'
import { 
  collection, 
  doc, 
  getDocs, 
  addDoc, 
  updateDoc, 
  deleteDoc,
  serverTimestamp,
  onSnapshot
} from 'firebase/firestore'
import { Button } from './ui/button'
import { Card } from './ui/card'
import { Copy, RefreshCw, Plus, Trash2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { db } from '../lib/firebase'

interface Agent {
  id: string
  name: string
  token: string
  createdAt: string
}

export function Dashboard() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [newAgentName, setNewAgentName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [loading, setLoading] = useState(true)
  const { currentUser } = useAuth()

  useEffect(() => {
    if (!currentUser) return

    const agentsRef = collection(db, `users/${currentUser.uid}/agents`)
    
    // Real-time listener for agents
    const unsubscribe = onSnapshot(agentsRef, (snapshot: any) => {
      const agentsData = snapshot.docs.map((doc: any) => ({
        id: doc.id,
        ...doc.data()
      })) as Agent[]
      
      setAgents(agentsData)
      setLoading(false)
    })

    // Migrate localStorage data if it exists
    migrateLocalStorageData()

    return unsubscribe
  }, [currentUser])

  const migrateLocalStorageData = async () => {
    if (!currentUser) return
    
    const localAgents = localStorage.getItem('agents')
    if (localAgents) {
      try {
        const parsedAgents = JSON.parse(localAgents) as Agent[]
        const agentsRef = collection(db, `users/${currentUser.uid}/agents`)
        
        // Check if user already has agents in Firestore
        const existingAgents = await getDocs(agentsRef)
        if (existingAgents.empty && parsedAgents.length > 0) {
          // Migrate each agent to Firestore
          for (const agent of parsedAgents) {
            await addDoc(agentsRef, {
              name: agent.name,
              token: agent.token,
              createdAt: new Date(agent.createdAt)
            })
          }
          
          // Clear localStorage after successful migration
          localStorage.removeItem('agents')
          console.log('Migrated agents from localStorage to Firestore')
        }
      } catch (error) {
        console.error('Error migrating localStorage data:', error)
      }
    }
  }

  const generateToken = () => {
    return 'agent_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now().toString(36)
  }

  const createAgent = async () => {
    if (!newAgentName.trim() || !currentUser) return

    try {
      const agentsRef = collection(db, `users/${currentUser.uid}/agents`)
      await addDoc(agentsRef, {
        name: newAgentName.trim(),
        token: generateToken(),
        createdAt: serverTimestamp()
      })
      
      setNewAgentName('')
      setIsCreating(false)
    } catch (error) {
      console.error('Error creating agent:', error)
    }
  }

  const regenerateToken = async (agentId: string) => {
    if (!currentUser) return

    try {
      const agentRef = doc(db, `users/${currentUser.uid}/agents`, agentId)
      await updateDoc(agentRef, {
        token: generateToken(),
        lastUpdated: serverTimestamp()
      })
    } catch (error) {
      console.error('Error regenerating token:', error)
    }
  }

  const deleteAgent = async (agentId: string) => {
    if (!currentUser) return

    try {
      const agentRef = doc(db, `users/${currentUser.uid}/agents`, agentId)
      await deleteDoc(agentRef)
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
                    Created {new Date(agent.createdAt).toLocaleDateString()}
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
          <code className="block bg-background p-3 rounded text-sm whitespace-pre">
{`curl -X POST https://api.predibench.com/submit \\
  -H "Authorization: Bearer YOUR_AGENT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"prediction": "your_prediction_data"}'`}
          </code>
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