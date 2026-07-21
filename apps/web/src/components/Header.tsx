import React, { useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Bell, Moon, Sun, Bot, LayoutDashboard, FolderGit2, ShieldAlert, GitPullRequest, History, BarChart3, Settings
} from 'lucide-react';

const NAV_ITEMS = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/' },
  { label: 'Repositories', icon: FolderGit2, path: '/repositories' },
  { label: 'Bug Explorer', icon: ShieldAlert, path: '/explorer' },
  { label: 'Pull Requests', icon: GitPullRequest, path: '/pull-requests' },
  { label: 'Analytics', icon: BarChart3, path: '/analytics' },
  { label: 'History', icon: History, path: '/history' },
  { label: 'Settings', icon: Settings, path: '/settings' },
];
import { useAuthStore } from '../store/useAuthStore';
import { useThemeStore } from '../store/useThemeStore';
import { toast } from 'sonner';

export const Header: React.FC = () => {
  const { user } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const overlayRef = useRef<HTMLDivElement>(null);

  const toggleTheme = (e: React.MouseEvent<HTMLButtonElement>) => {
    const isDark = document.documentElement.classList.contains('dark');
    const newTheme = isDark ? 'light' : 'dark';

    // Get click coordinates for circular reveal
    const rect = e.currentTarget.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;

    const overlay = document.createElement('div');
    overlay.className = 'theme-transition-overlay';
    // Use the next theme's background color
    overlay.style.backgroundColor = isDark ? '#f5f5f4' : '#030712';
    overlay.style.clipPath = `circle(0px at ${x}px ${y}px)`;
    overlay.style.transition = 'clip-path 0.5s ease-in-out';
    document.body.appendChild(overlay);

    // Force reflow
    void overlay.offsetWidth;

    // Expand circle
    const radius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
    overlay.style.clipPath = `circle(${radius}px at ${x}px ${y}px)`;

    setTimeout(() => {
      setTheme(newTheme);
      setTimeout(() => {
        overlay.remove();
      }, 100);
    }, 500);
  };

  return (
    <header className="h-20 border-b border-border bg-background/50 backdrop-blur-sm sticky top-0 z-30 flex items-center justify-between px-8 select-none shrink-0 gap-4">
      
      {/* Left: Brand Logo & Animated Name */}
      <div className="flex-1 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-card border border-border flex items-center justify-center shadow-md">
          <Bot className="w-5 h-5 text-primary" />
        </div>
        <div className="flex items-center gap-1.5 overflow-hidden">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={{
              hidden: { opacity: 0 },
              visible: {
                opacity: 1,
                transition: { staggerChildren: 0.1 }
              }
            }}
            className="flex font-black text-lg tracking-tight bg-gradient-to-r from-primary to-purple-500 bg-clip-text text-transparent"
          >
            {"Rover".split("").map((char, index) => (
              <motion.span
                key={index}
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  visible: { opacity: 1, y: 0 }
                }}
                className="inline-block"
              >
                {char}
              </motion.span>
            ))}
          </motion.div>
          <span className="bg-primary/10 text-primary border border-primary/20 text-[10px] font-bold px-1.5 py-0.2 rounded-full">v2.0</span>
        </div>
      </div>

      {/* Center: Navigation Links */}
      <nav className="hidden lg:flex items-center justify-center gap-1 bg-card/60 p-1.5 rounded-2xl border border-border backdrop-blur-md">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-200 ${
                  isActive
                    ? 'bg-primary/10 text-primary shadow-sm ring-1 ring-primary/20'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }`
              }
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Right Side: Profile & Actions */}
      <div className="flex items-center justify-end gap-4 shrink-0 flex-1">
        
        {/* Theme Toggle */}
        <button 
          onClick={toggleTheme}
          className="w-10 h-10 flex items-center justify-center rounded-xl bg-card hover:bg-muted border border-border text-muted-foreground hover:text-foreground transition-colors relative backdrop-blur-md shadow-sm"
        >
          {theme === 'light' ? <Moon className="w-4.5 h-4.5" /> : <Sun className="w-4.5 h-4.5" />}
        </button>

        {/* Notifications */}
        <button 
          onClick={() => toast.info('No new notifications', { description: 'You are all caught up!' })}
          className="w-10 h-10 flex items-center justify-center rounded-xl bg-card hover:bg-muted border border-border text-muted-foreground hover:text-foreground transition-colors relative backdrop-blur-md shadow-sm"
        >
          <Bell className="w-4.5 h-4.5" />
          <span className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_var(--primary)]"></span>
        </button>

        {/* User Avatar */}
        {user && (
          <img
            src={user.avatar_url}
            alt={user.name}
            className="w-10 h-10 rounded-xl object-cover ring-1 ring-border shadow-md"
          />
        )}
      </div>
    </header>
  );
};
