import type { ReactNode } from 'react'
import { Trophy, BarChart3, Newspaper } from 'lucide-react'
import { Footer } from './Footer'

interface LayoutProps {
  children: ReactNode
  currentPage?: string
}

export function Layout({ children, currentPage }: LayoutProps) {
  const pages = [
    { id: 'leaderboard', name: 'Leaderboard', href: '/leaderboard', icon: Trophy },
    { id: 'models', name: 'Models', href: '/models', icon: BarChart3 },
    { id: 'events', name: 'Events', href: '/events', icon: Newspaper }
  ]

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header and Navigation */}
      <header className="border-b border-border bg-card shadow-sm">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <a href="/" className="text-3xl font-bold tracking-tight hover:text-muted-foreground transition-colors">
                PrediBench
              </a>
              <p className="text-sm text-muted-foreground">
                Letting LLMs bet their money on the future
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <nav className="flex items-center space-x-1">
                {pages.map((page) => (
                  <a
                    key={page.id}
                    href={page.href}
                    className={`
                      px-3 py-2 font-medium text-sm transition-colors duration-200
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
                  </a>
                ))}
              </nav>
            </div>
          </div>
        </div>
      </header>

      {/* Page Content */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <Footer />
    </div>
  )
}