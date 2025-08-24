import { Github } from 'lucide-react'

export function Footer() {
  const links = [
    { name: 'Home', href: '/' },
    { name: 'About', href: '/about' },
    { name: 'Leaderboard', href: '/leaderboard' },
    { name: 'Models', href: '/models' },
    { name: 'Events', href: '/events' },
    { name: 'Add Your Model', href: '/add-your-model' }
  ]

  return (
    <footer className="mt-auto border-t border-border bg-background">
      <div className="container mx-auto px-6 py-6">
        <div className="flex flex-col items-center space-y-4">
          <nav className="flex items-center space-x-8">
            {links.map((link, index) => (
              <a
                key={index}
                href={link.href}
                className="text-muted-foreground hover:text-foreground text-sm font-medium transition-colors"
              >
                {link.name}
              </a>
            ))}
          </nav>

          <div className="flex items-center space-x-4 text-sm text-gray-500">
            <p>© 2025 PrediBench. All rights reserved.</p>
            <a
              href="https://github.com/aymeric-roucher/PrediBench"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-1 text-muted-foreground hover:text-foreground transition-colors"
            >
              <Github size={16} />
              <span>PrediBench</span>
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
