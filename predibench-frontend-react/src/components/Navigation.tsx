interface NavigationProps {
  currentPage: string
  onPageChange: (page: string) => void
}

export function Navigation({ currentPage, onPageChange }: NavigationProps) {
  const pages = [
    { id: 'leaderboard', name: 'Leaderboard', icon: '🏆' },
    { id: 'models', name: 'Models', icon: '🤖' },
    { id: 'questions', name: 'This Week\'s Questions', icon: '❓' }
  ]

  return (
    <div className="flex space-x-1">
      {pages.map((page) => (
        <button
          key={page.id}
          onClick={() => onPageChange(page.id)}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
            currentPage === page.id
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
          }`}
        >
          <span className="mr-2">{page.icon}</span>
          {page.name}
        </button>
      ))}
    </div>
  )
}