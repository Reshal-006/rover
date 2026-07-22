import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Settings as SettingsIcon, 
  User, 
  Github, 
  Bot, 
  Bell, 
  Palette, 
  BarChart3, 
  Shield, 
  AlertTriangle,
  LogOut,
  RefreshCw,
  CheckCircle2,
  Moon,
  Sun,
  Monitor,
  Trash2,
  Power
} from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import { useThemeStore } from '../store/useThemeStore';
import { useSettingsStore } from '../store/useSettingsStore';
import { toast } from 'sonner';

const Toggle = ({ enabled, onChange, label, description }: any) => (
  <div className="flex items-center justify-between p-4 rounded-xl bg-card border border-border hover:border-primary/50 transition-colors">
    <div className="flex-1 pr-4">
      <span className="font-bold text-foreground text-sm block mb-1">{label}</span>
      {description && <p className="text-muted-foreground text-xs leading-relaxed">{description}</p>}
    </div>
    <button
      onClick={() => onChange(!enabled)}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${enabled ? 'bg-primary' : 'bg-muted'}`}
    >
      <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-background shadow ring-0 transition duration-200 ease-in-out ${enabled ? 'translate-x-4' : 'translate-x-0'}`} />
    </button>
  </div>
);

export const Settings: React.FC = () => {
  const { user, logout } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  
  const {
    autoMode, setAutoMode,
    autoPR, setAutoPR,
    autoRetry, setAutoRetry,
    scanType, setScanType,
    maxScans, setMaxScans,
    notifyComplete, setNotifyComplete,
    notifyPR, setNotifyPR,
    notifyFail, setNotifyFail,
    notifySync, setNotifySync,
    animations, setAnimations,
    compact, setCompact
  } = useSettingsStore();

  const [stats, setStats] = useState({
    total_repositories: 0,
    total_scans: 0,
    total_vulnerabilities: 0,
    resolved_vulnerabilities: 0,
    pull_requests_merged: 0,
    ai_compute_savings: "0.0%"
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = localStorage.getItem('rover_jwt_token');
        const res = await fetch('/api/v1/dashboard/summary', {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch (e) {
        console.error("Failed to fetch stats", e);
      }
    };
    fetchStats();
  }, []);

  const handleReconnectGitHub = async () => {
    try {
      const res = await fetch('/api/v1/auth/github/url');
      if (res.ok) {
        const data = await res.json();
        window.location.href = data.url;
      } else {
        toast.error('Failed to get GitHub auth URL');
      }
    } catch (e) {
      toast.error('Network error connecting to backend');
    }
  };

  const handleSyncGitHub = async () => {
    try {
      const token = localStorage.getItem('rover_jwt_token');
      const res = await fetch('/api/v1/repositories/sync', {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        toast.success('Syncing with GitHub started in background...');
      } else {
        toast.error('Failed to trigger GitHub sync');
      }
    } catch (e) {
      toast.error('Network error connecting to backend');
    }
  };

  const handleDisconnectGitHub = async () => {
    try {
      const token = localStorage.getItem('rover_jwt_token');
      const res = await fetch('/api/v1/auth/github', {
        method: 'DELETE',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        toast.success('GitHub connection disconnected.');
        // Refresh page to update state
        setTimeout(() => window.location.reload(), 1500);
      } else {
        toast.error('Failed to disconnect GitHub');
      }
    } catch (e) {
      toast.error('Network error connecting to backend');
    }
  };

  const handleResetWorkspace = async () => {
    try {
      const token = localStorage.getItem('rover_jwt_token');
      const res = await fetch('/api/v1/workspace', {
        method: 'DELETE',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        toast.success('Workspace reset! All data has been wiped.');
        setTimeout(() => {
          localStorage.removeItem('rover_jwt_token');
          window.location.href = '/';
        }, 1500);
      } else {
        toast.error('Failed to reset workspace');
      }
    } catch (e) {
      toast.error('Network error connecting to backend');
    }
  };

  return (
    <div className="space-y-8 max-w-4xl pb-10">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
          <SettingsIcon className="w-6 h-6 text-muted-foreground" />
          <span>Settings</span>
        </h1>
        <p className="text-xs text-muted-foreground mt-1">Manage your account, autonomous agent preferences, and workspace configuration.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        
        {/* Navigation / TOC */}
        <div className="md:col-span-3 space-y-1">
          {['Account', 'GitHub Integration', 'Agent Configuration', 'Notifications', 'Appearance', 'Workspace Statistics', 'Security', 'Danger Zone'].map((item, idx) => (
            <a 
              key={item} 
              href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
              className="block px-3 py-2 rounded-lg text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              {item}
            </a>
          ))}
        </div>

        {/* Settings Content */}
        <div className="md:col-span-9 space-y-8">

          {/* 1. Account */}
          <section id="account" className="space-y-4">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2 uppercase tracking-widest border-b border-border pb-2">
              <User className="w-4 h-4 text-primary" /> Account
            </h2>
            <div className="glass-panel p-6 rounded-2xl border border-border bg-card flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <img
                  src={user?.avatar_url || 'https://github.com/ghost.png'}
                  alt="Avatar"
                  className="w-16 h-16 rounded-2xl object-cover ring-2 ring-border shadow-xl"
                />
                <div>
                  <h3 className="text-lg font-bold text-foreground">{user?.name || 'Developer'}</h3>
                  <p className="text-sm text-muted-foreground">@{user?.username || 'user'}</p>
                  <p className="text-[11px] text-muted-foreground mt-1 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-green-500" /> Connected since {new Date().toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex flex-col gap-2 w-full md:w-auto">
                <button 
                  onClick={handleReconnectGitHub}
                  className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground text-xs font-semibold rounded-xl border border-border transition-colors w-full text-center">
                  Reconnect GitHub
                </button>
                <button 
                  onClick={logout}
                  className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 text-xs font-semibold rounded-xl border border-red-500/20 transition-colors flex items-center justify-center gap-2 w-full"
                >
                  <LogOut className="w-3.5 h-3.5" /> Sign Out
                </button>
              </div>
            </div>
          </section>

          {/* 2. GitHub Integration */}
          <section id="github-integration" className="space-y-4">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2 uppercase tracking-widest border-b border-border pb-2">
              <Github className="w-4 h-4 text-green-500" /> GitHub Integration
            </h2>
            <div className="glass-panel p-6 rounded-2xl border border-border bg-card">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-sm font-bold text-foreground mb-1 flex items-center gap-2">
                    Rover App Installation <span className="bg-green-500/10 text-green-500 border border-green-500/20 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider">Connected</span>
                  </h3>
                  <p className="text-xs text-muted-foreground">App manages repository scanning and pull requests.</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-primary">12</div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-widest">Connected Repos</div>
                </div>
              </div>
              
              <div className="flex items-center justify-between p-4 rounded-xl bg-muted border border-border">
                <div>
                  <span className="text-xs font-semibold text-foreground block">Last Synchronization</span>
                  <span className="text-xs text-muted-foreground block mt-0.5">Today at {new Date().toLocaleTimeString()}</span>
                </div>
                <button 
                  onClick={handleSyncGitHub}
                  className="px-3 py-1.5 bg-muted hover:bg-muted/80 text-foreground text-[11px] font-bold rounded-lg border border-border transition-colors flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3 h-3" /> Sync Now
                </button>
              </div>

              <div className="flex items-center justify-between p-4 rounded-xl bg-muted border border-border mt-3">
                <div>
                  <span className="text-xs font-semibold text-foreground block">GitHub App Authentication</span>
                  <span className="text-xs text-muted-foreground block mt-0.5">Refresh your token if you encounter access issues</span>
                </div>
                <button 
                  onClick={handleReconnectGitHub}
                  className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground text-xs font-semibold rounded-xl border border-border transition-colors"
                >
                  Reconnect GitHub
                </button>
              </div>
            </div>
          </section>

          {/* 3. Agent Configuration */}
          <section id="agent-configuration" className="space-y-4">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2 uppercase tracking-widest border-b border-border pb-2">
              <Bot className="w-4 h-4 text-primary" /> Agent Configuration
            </h2>
            <div className="glass-panel p-6 rounded-2xl border border-border bg-card space-y-3">
              <Toggle 
                enabled={autoMode} 
                onChange={setAutoMode} 
                label="Autonomous Mode" 
                description="Allow Rover to automatically scan new commits and generate fixes without manual intervention." 
              />
              <Toggle 
                enabled={autoPR} 
                onChange={setAutoPR} 
                label="Automatic Pull Request Creation" 
                description="If enabled, Rover will push branches and open PRs autonomously when fixes are generated." 
              />
              <Toggle 
                enabled={autoRetry} 
                onChange={setAutoRetry} 
                label="Auto-Retry Failed Scans" 
                description="Automatically retry AST or AI analysis if they fail due to rate limits." 
              />
              
              <div className="flex items-center justify-between p-4 rounded-xl bg-card border border-border mt-2 hover:border-primary/50 transition-colors">
                <div className="pr-4">
                  <span className="font-bold text-foreground text-sm block mb-1">Default Scan Type</span>
                  <p className="text-muted-foreground text-xs">Choose the thoroughness of autonomous scans.</p>
                </div>
                <select 
                  value={scanType}
                  onChange={(e) => setScanType(e.target.value as 'quick' | 'deep')}
                  className="bg-background border border-border text-foreground text-xs rounded-lg px-3 py-2 outline-none focus:border-primary transition-colors cursor-pointer"
                >
                  <option value="quick">Quick Scan (AST + Shallow AI)</option>
                  <option value="deep">Deep Scan (Full AI Reasoning)</option>
                </select>
              </div>

              <div className="flex items-center justify-between p-4 rounded-xl bg-card border border-border mt-2 hover:border-primary/50 transition-colors">
                <div className="pr-4">
                  <span className="font-bold text-foreground text-sm block mb-1">Max Concurrent Scans</span>
                  <p className="text-muted-foreground text-xs">Limit how many repositories Rover scans simultaneously.</p>
                </div>
                <input 
                  type="number" 
                  min="1" 
                  max="10" 
                  value={maxScans}
                  onChange={(e) => setMaxScans(parseInt(e.target.value) || 3)}
                  className="bg-background border border-border text-foreground text-sm font-mono rounded-lg px-3 py-1.5 w-16 text-center outline-none focus:border-primary"  
                />
              </div>
            </div>
          </section>

          {/* 4. Notifications */}
          <section id="notifications" className="space-y-4">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2 uppercase tracking-widest border-b border-border pb-2">
              <Bell className="w-4 h-4 text-orange-400" /> Notifications
            </h2>
            <div className="glass-panel p-6 rounded-2xl border border-border bg-card grid grid-cols-1 md:grid-cols-2 gap-3">
              <Toggle enabled={notifyComplete} onChange={setNotifyComplete} label="Scan Completes" />
              <Toggle enabled={notifyPR} onChange={setNotifyPR} label="PR Created" />
              <Toggle enabled={notifyFail} onChange={setNotifyFail} label="Scan Fails" />
              <Toggle enabled={notifySync} onChange={setNotifySync} label="Repo Sync Finishes" />
            </div>
          </section>

          {/* 5. Appearance */}
          <section id="appearance" className="space-y-4">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2 uppercase tracking-widest border-b border-border pb-2">
              <Palette className="w-4 h-4 text-primary" /> Appearance
            </h2>
            <div className="glass-panel p-6 rounded-2xl border border-border bg-card space-y-4">
              
              <div>
                <span className="font-bold text-foreground text-sm block mb-3">Theme Preference</span>
                <div className="flex gap-3">
                  <button onClick={() => setTheme('light')} className={`flex-1 flex flex-col items-center gap-2 p-4 rounded-xl border ${theme === 'light' ? 'bg-primary/10 border-primary/50 text-primary' : 'bg-background border-border text-muted-foreground hover:bg-muted'}`}>
                    <Sun className="w-5 h-5" />
                    <span className="text-xs font-semibold">Light</span>
                  </button>
                  <button onClick={() => setTheme('dark')} className={`flex-1 flex flex-col items-center gap-2 p-4 rounded-xl border ${theme === 'dark' ? 'bg-primary/10 border-primary/50 text-primary' : 'bg-background border-border text-muted-foreground hover:bg-muted'}`}>
                    <Moon className="w-5 h-5" />
                    <span className="text-xs font-semibold">Dark</span>
                  </button>
                  <button onClick={() => setTheme('system')} className={`flex-1 flex flex-col items-center gap-2 p-4 rounded-xl border ${theme === 'system' ? 'bg-primary/10 border-primary/50 text-primary' : 'bg-background border-border text-muted-foreground hover:bg-muted'}`}>
                    <Monitor className="w-5 h-5" />
                    <span className="text-xs font-semibold">System</span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                <Toggle enabled={animations} onChange={setAnimations} label="UI Animations" description="Enable smooth transitions and micro-animations." />
                <Toggle enabled={compact} onChange={setCompact} label="Compact Mode" description="Reduce padding and spacing to fit more data." />
              </div>
            </div>
          </section>

          {/* 6. Workspace Statistics */}
          <section id="workspace-statistics" className="space-y-4">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2 uppercase tracking-widest border-b border-border pb-2">
              <BarChart3 className="w-4 h-4 text-primary" /> Workspace Statistics
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {[
                { label: 'Connected Repos', value: stats.total_repositories },
                { label: 'Total Scans', value: stats.total_scans },
                { label: 'Bugs Detected', value: stats.total_vulnerabilities },
                { label: 'Bugs Fixed', value: stats.resolved_vulnerabilities },
                { label: 'PRs Created', value: stats.pull_requests_merged },
                { label: 'AI Savings', value: stats.ai_compute_savings },
              ].map(stat => (
                <div key={stat.label} className="glass-panel p-4 rounded-xl border border-border bg-card flex flex-col justify-center items-center text-center">
                  <span className="text-2xl font-bold text-foreground mb-1">{stat.value}</span>
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">{stat.label}</span>
                </div>
              ))}
            </div>
          </section>

          {/* 7. Security */}
          <section id="security" className="space-y-4">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2 uppercase tracking-widest border-b border-border pb-2">
              <Shield className="w-4 h-4 text-green-500" /> Security
            </h2>
            <div className="glass-panel p-6 rounded-2xl border border-border bg-card space-y-3">
              <div className="flex items-center justify-between p-4 rounded-xl bg-muted border border-border">
                <div>
                  <span className="font-bold text-foreground text-sm block mb-1">Current Session</span>
                  <p className="text-muted-foreground text-xs">Active since {new Date().toLocaleDateString()}</p>
                </div>
                <span className="bg-green-500/10 text-green-500 border border-green-500/20 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-bold">Active</span>
              </div>
              <div className="flex items-center justify-between p-4 rounded-xl bg-muted border border-border">
                <div>
                  <span className="font-bold text-foreground text-sm block mb-1">Active GitHub Connection</span>
                  <p className="text-muted-foreground text-xs">Rover App is authorized and connected.</p>
                </div>
                <span className="bg-green-500/10 text-green-500 border border-green-500/20 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-bold">Valid</span>
              </div>
              <div className="flex items-center justify-between p-4 rounded-xl bg-muted border border-border">
                <div>
                  <span className="font-bold text-foreground text-sm block mb-1">Last Login IP</span>
                  <p className="text-muted-foreground text-xs font-mono">192.168.1.104</p>
                </div>
                <button 
                  onClick={async () => {
                    try {
                      const token = localStorage.getItem('rover_jwt_token');
                      await fetch('/api/v1/auth/revoke', { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
                      toast.error('Session revoked. You have been signed out of this device.');
                      setTimeout(() => {
                        localStorage.removeItem('rover_jwt_token');
                        window.location.href = '/';
                      }, 1000);
                    } catch (e) {
                      toast.error('Failed to revoke session');
                    }
                  }}
                  className="px-3 py-1.5 bg-muted hover:bg-muted/80 text-foreground text-xs font-semibold rounded-lg border border-border transition-colors"
                >
                  Revoke Session
                </button>
              </div>
            </div>
          </section>

          {/* 8. Danger Zone */}
          <section id="danger-zone" className="space-y-4 pt-4">
            <h2 className="text-sm font-bold text-red-500 flex items-center gap-2 uppercase tracking-widest border-b border-red-500/50 pb-2">
              <AlertTriangle className="w-4 h-4" /> Danger Zone
            </h2>
            <div className="p-6 rounded-2xl border border-red-500/30 bg-red-500/5 space-y-4">
              
              <div className="flex items-center justify-between p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                <div>
                  <span className="font-bold text-red-500 text-sm block mb-1">Disconnect GitHub</span>
                  <p className="text-red-500/70 text-xs">Remove the Rover App installation from your GitHub account.</p>
                </div>
                <button 
                  onClick={handleDisconnectGitHub}
                  className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-500 text-xs font-bold rounded-lg border border-red-500/30 transition-colors shrink-0"
                >
                  Disconnect
                </button>
              </div>

              <div className="flex items-center justify-between p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                <div>
                  <span className="font-bold text-red-500 text-sm block mb-1">Clear Scan History</span>
                  <p className="text-red-500/70 text-xs">Permanently delete all previous scan logs and findings from the database.</p>
                </div>
                <button 
                  onClick={async () => {
                    try {
                      const token = localStorage.getItem('rover_jwt_token');
                      const res = await fetch('/api/v1/history', { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
                      if (res.ok) {
                        toast.success('Scan history cleared successfully.');
                      } else {
                        toast.error('Failed to clear history.');
                      }
                    } catch (e) {
                      toast.error('Network error while clearing history.');
                    }
                  }}
                  className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-500 text-xs font-bold rounded-lg border border-red-500/30 transition-colors shrink-0 flex items-center gap-2"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Clear History
                </button>
              </div>

              <div className="flex items-center justify-between p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                <div>
                  <span className="font-bold text-red-500 text-sm block mb-1">Reset Workspace</span>
                  <p className="text-red-500/70 text-xs">Deletes all repositories, findings, and restores default settings.</p>
                </div>
                <button 
                  onClick={handleResetWorkspace}
                  className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white text-xs font-bold rounded-lg transition-colors shrink-0 flex items-center gap-2 shadow-sm"
                >
                  <Power className="w-3.5 h-3.5" /> Reset Rover
                </button>
              </div>

            </div>
          </section>

        </div>
      </div>
    </div>
  );
};
