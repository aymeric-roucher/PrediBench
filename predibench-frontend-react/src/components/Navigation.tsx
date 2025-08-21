import { Trophy } from 'lucide-react'

interface NavigationProps {
  currentPage: string
  onPageChange: (page: string) => void
}

export function Navigation({ currentPage, onPageChange }: NavigationProps) {
  const pages = [
    { id: 'leaderboard', name: 'Leaderboard', icon: Trophy },
    { id: 'models', name: 'Models', icon: null },
    { id: 'questions', name: 'This Week\'s Questions', icon: null }
  ]

  return (
    <nav className="flex items-center space-x-1">
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
    </nav>
  )
}