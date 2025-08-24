import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../../contexts/ThemeContext'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      className="inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-muted-foreground focus:ring-offset-2"
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'dark' ? (
        <Moon size={16} className="text-muted-foreground" />
      ) : (
        <Sun size={16} className="text-muted-foreground" />
      )}
    </button>
  )
}