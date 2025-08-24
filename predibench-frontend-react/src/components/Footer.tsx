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
    <footer className="mt-auto border-t border-gray-300 bg-background">
      <div className="container mx-auto px-6 py-6">
        <div className="flex flex-col items-center space-y-4">
          <nav className="flex items-center space-x-8">
            {links.map((link, index) => (
              <a
                key={index}
                href={link.href}
                className="text-blue-500 hover:text-blue-600 text-sm font-medium transition-colors"
              >
                {link.name}
              </a>
            ))}
          </nav>

          <p className="text-sm text-gray-500">
            © 2025 PrediBench. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}
