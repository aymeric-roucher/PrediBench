import { Trophy, Upload, User, LogOut } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { Button } from './ui/button'
import { useState } from 'react'
import { AuthModal } from './AuthModal'

interface NavigationProps {
  currentPage: string
  onPageChange: (page: string) => void
}

export function Navigation({ currentPage, onPageChange }: NavigationProps) {
  const { currentUser, logout } = useAuth()
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')

  const pages = [
    { id: 'leaderboard', name: 'Leaderboard', icon: Trophy },
    { id: 'models', name: 'Models', icon: null },
    { id: 'events', name: 'Events', icon: null },
    { id: 'submit', name: 'Submit', icon: Upload }
  ]

  const handleAuth = (mode: 'login' | 'register') => {
    setAuthMode(mode)
    setShowAuthModal(true)
  }

  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  return (
    <>
      <nav className="flex items-center justify-between w-full">
        <div className="flex items-center space-x-1">
          {pages.map((page) => (
            <button
              key={page.id}
              onClick={() => onPageChange(page.id)}
              className={`
                px-4 py-2 font-medium text-sm transition-colors duration-200
                ${currentPage === page.id
                  ? 'text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
                }
              `}
            >
              <div className="flex items-center space-x-2">
                {page.icon && <page.icon size={16} />}
                <span>{page.name}</span>
              </div>
            </button>
          ))}
        </div>

        <div className="flex items-center space-x-2">
          {currentUser ? (
            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-2 px-3 py-1 bg-green-50 rounded-full">
                <User size={14} className="text-green-600" />
                <span className="text-sm text-green-700">
                  {currentUser.displayName || currentUser.email}
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleLogout}
                className="flex items-center space-x-1"
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </Button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleAuth('login')}
              >
                Sign In
              </Button>
              <Button
                size="sm"
                onClick={() => handleAuth('register')}
              >
                Sign Up
              </Button>
            </div>
          )}
        </div>
      </nav>

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        mode={authMode}
        onSwitchMode={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
      />
    </>
  )
}