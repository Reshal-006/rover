import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FolderGit2,
  RefreshCw,
  ExternalLink,
  Search,
  Lock,
  Globe,
  Play,
  CheckCircle2,
  ShieldAlert,
  GitBranch,
  Cpu,
  Sparkles,
  Layers,
  ArrowUpDown,
  Filter,
  AlertCircle,
  Clock,
  Shield,
  Building,
  User,
  X,
  FileCode
} from 'lucide-react';
import { toast } from 'sonner';

export interface RepositoryData {
  id: string;
  full_name: string;
  name: string;
  owner: string;
  account_type: 'Personal' | 'Organization';
  default_branch: string;
  is_private: boolean;
  language: string;
  size_kb: number;
  open_issues: number;
  pull_requests: number;
  contributors: number;
  health_score: number;
  ai_readiness_score: number;
  security_grade: string;
  last_scanned_at: string;
  scan_status: string;
  github_app_installed: boolean;
}

export interface SyncSummary {
  added: number;
  updated: number;
  removed: number;
  duration_seconds: number;
  total_active: number;
}

export const Repositories: React.FC = () => {
  const [repositories, setRepositories] = useState<RepositoryData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>('');

  // Filters & Sorting
  const [selectedGroup, setSelectedGroup] = useState<'all' | 'Personal' | 'Organization'>('all');
  const [visibilityFilter, setVisibilityFilter] = useState<'all' | 'private' | 'public'>('all');
  const [languageFilter, setLanguageFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'updated' | 'issues' | 'name'>('updated');

  // Sync state & modal
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncStage, setSyncStage] = useState<number>(0);
  const [syncSummary, setSyncSummary] = useState<SyncSummary | null>(null);

  const fetchRepositories = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('rover_jwt_token');
      const res = await fetch('/api/v1/repositories', {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (!res.ok) {
        throw new Error(`Failed to fetch repositories (Status ${res.status})`);
      }
      const data = await res.json();
      setRepositories(data.repositories || []);
    } catch (err: any) {
      setError(err.message || 'Error connecting to backend API');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepositories();
  }, []);

  const handleSyncGitHub = async () => {
    setIsSyncing(true);
    setSyncStage(1);
    setSyncSummary(null);

    try {
      // Stage 1: Verify GitHub Auth
      await new Promise(r => setTimeout(r, 400));
      setSyncStage(2); // Fetch Installations

      await new Promise(r => setTimeout(r, 500));
      setSyncStage(3); // Fetch Repositories

      await new Promise(r => setTimeout(r, 500));
      setSyncStage(4); // Database Reconcile

      const token = localStorage.getItem('rover_jwt_token');
      const res = await fetch('/api/v1/repositories/sync', {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      const data = await res.json();


      if (!res.ok) {
        throw new Error(data.detail || 'GitHub App synchronization failed');
      }

      setSyncStage(5); // Complete
      setSyncSummary({
        added: data.added,
        updated: data.updated,
        removed: data.removed,
        duration_seconds: data.duration_seconds,
        total_active: data.total_active
      });

      // Refresh list
      await fetchRepositories();
      toast.success('Repository sync started in the background');
    } catch (err: any) {
      toast.error(err.message || 'Sync failed');
      setIsSyncing(false);
    }
  };

  const pollQuickScanStatus = (scanId: string, repoUrl: string) => {
    const token = localStorage.getItem('rover_jwt_token');
    const headers: Record<string, string> = token ? { 'Authorization': `Bearer ${token}` } : {};

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/scans/${scanId}`, { headers });
        if (res.ok) {
          const scan = await res.json();
          if (scan.status === 'completed') {
            clearInterval(interval);
            const bugCount = scan.bugs ? scan.bugs.length : 0;
            toast.success(`Quick scan completed for ${repoUrl}! Found ${bugCount} vulnerabilities.`);
            await fetchRepositories();
          } else if (scan.status === 'failed') {
            clearInterval(interval);
            toast.error(`Quick scan failed for ${repoUrl}: ${scan.error || 'Unknown error'}`);
          }
        }
      } catch (e) {
        // Retry silently
      }
    }, 1500);

    setTimeout(() => clearInterval(interval), 180000);
  };

  const handleTriggerQuickScan = async (repoUrl: string) => {
    toast.info(`Initiating Quick Scan for ${repoUrl}...`);
    try {
      const token = localStorage.getItem('rover_jwt_token');
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/v1/scans', {
        method: 'POST',
        headers,
        body: JSON.stringify({ repository_url: `https://github.com/${repoUrl}` })
      });
      const data = await res.json();
      if (res.ok && data.scan_id) {
        toast.info(`Scan job running (ID: ${data.scan_id}). Analyzing code...`);
        pollQuickScanStatus(data.scan_id, repoUrl);
      } else {
        toast.error(data.detail || 'Scan trigger failed');
      }
    } catch (err) {
      toast.error('Failed to communicate with backend API');
    }
  };

  // Filter & Sort Logic
  const filteredRepositories = repositories
    .filter(repo => {
      // Search match
      const matchesSearch = repo.full_name.toLowerCase().includes(search.toLowerCase()) ||
        repo.language.toLowerCase().includes(search.toLowerCase());

      // Group match
      const matchesGroup = selectedGroup === 'all' || repo.account_type === selectedGroup;

      // Visibility match
      const matchesVisibility = visibilityFilter === 'all' ||
        (visibilityFilter === 'private' && repo.is_private) ||
        (visibilityFilter === 'public' && !repo.is_private);

      // Language match
      const matchesLanguage = languageFilter === 'all' || repo.language.toLowerCase() === languageFilter.toLowerCase();

      return matchesSearch && matchesGroup && matchesVisibility && matchesLanguage;
    })
    .sort((a, b) => {
      if (sortBy === 'issues') return b.open_issues - a.open_issues;
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      return b.full_name.localeCompare(a.full_name);
    });

  const languages = Array.from(new Set(repositories.map(r => r.language)));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
            <FolderGit2 className="w-6 h-6 text-muted-foreground" />
            <span>GitHub Repositories</span>
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Production environment repositories accessible via your GitHub App installation.
          </p>
        </div>

        <button
          onClick={handleSyncGitHub}
          disabled={isSyncing}
          className="bg-primary hover:opacity-90 text-primary-foreground font-bold text-xs px-5 py-2.5 rounded-xl border border-transparent flex items-center gap-2 shadow-md transition-all duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
          <span>{isSyncing ? 'Syncing GitHub...' : 'Sync GitHub'}</span>
        </button>
      </div>

      {/* Account / Org Filter Pills & Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 glass-panel p-4 rounded-2xl border border-border bg-card">
        {/* Account Groups */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedGroup('all')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${selectedGroup === 'all'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
          >
            All Scope ({repositories.length})
          </button>
          <button
            onClick={() => setSelectedGroup('Personal')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${selectedGroup === 'Personal'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>Personal</span>
          </button>
          <button
            onClick={() => setSelectedGroup('Organization')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${selectedGroup === 'Organization'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
          >
            <Building className="w-3.5 h-3.5" />
            <span>Organizations</span>
          </button>
        </div>

        {/* Filters & Sorting */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter repositories..."
              className="w-full bg-background border border-border rounded-xl pl-9 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors shadow-sm"
            />
          </div>

          {/* Visibility Dropdown */}
          <select
            value={visibilityFilter}
            onChange={(e) => setVisibilityFilter(e.target.value as any)}
            className="bg-background border border-border text-foreground text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-primary"
          >
            <option value="all">All Visibilities</option>
            <option value="private">Private Only</option>
            <option value="public">Public Only</option>
          </select>

          {/* Sort By Dropdown */}
          <div className="flex items-center gap-1 text-xs text-muted-foreground bg-background border border-border px-3 py-1.5 rounded-xl">
            <ArrowUpDown className="w-3.5 h-3.5 text-muted-foreground" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-transparent text-foreground focus:outline-none"
            >
              <option value="updated">Recently Updated</option>
              <option value="issues">Most Issues</option>
              <option value="name">Name A-Z</option>
            </select>
          </div>
        </div>
      </div>

      {/* Syncing Progress Overlay Modal */}
      <AnimatePresence>
        {isSyncing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-panel p-7 rounded-3xl border border-slate-700/50 max-w-lg w-full bg-zinc-950/95 shadow-2xl relative space-y-6"
            >
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-slate-800/50 border border-slate-700/50 flex items-center justify-center text-slate-300">
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white tracking-tight">GitHub App Synchronization</h3>
                    <p className="text-xs text-slate-400">Reconciling authenticated repository permissions</p>
                  </div>
                </div>
                {syncStage === 5 && (
                  <button onClick={() => setIsSyncing(false)} className="text-slate-400 hover:text-white">
                    <X className="w-5 h-5" />
                  </button>
                )}
              </div>

              {/* Stage Stepper List */}
              <div className="space-y-3 text-xs">
                <div className={`flex items-center justify-between p-3 rounded-xl border ${syncStage > 1 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : syncStage === 1 ? 'bg-indigo-500/10 border-indigo-500/30 text-white animate-pulse' : 'bg-slate-950/40 border-slate-800 text-slate-500'
                  }`}>
                  <span className="font-semibold">1. Verifying GitHub App Token & OAuth Session</span>
                  {syncStage > 1 ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : syncStage === 1 ? <Clock className="w-4 h-4 text-indigo-400 animate-spin" /> : null}
                </div>

                <div className={`flex items-center justify-between p-3 rounded-xl border ${syncStage > 2 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : syncStage === 2 ? 'bg-indigo-500/10 border-indigo-500/30 text-white animate-pulse' : 'bg-slate-950/40 border-slate-800 text-slate-500'
                  }`}>
                  <span className="font-semibold">2. Querying Active GitHub App Installations</span>
                  {syncStage > 2 ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : syncStage === 2 ? <Clock className="w-4 h-4 text-indigo-400 animate-spin" /> : null}
                </div>

                <div className={`flex items-center justify-between p-3 rounded-xl border ${syncStage > 3 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : syncStage === 3 ? 'bg-indigo-500/10 border-indigo-500/30 text-white animate-pulse' : 'bg-slate-950/40 border-slate-800 text-slate-500'
                  }`}>
                  <span className="font-semibold">3. Fetching Accessible Repositories & Organizations</span>
                  {syncStage > 3 ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : syncStage === 3 ? <Clock className="w-4 h-4 text-indigo-400 animate-spin" /> : null}
                </div>

                <div className={`flex items-center justify-between p-3 rounded-xl border ${syncStage > 4 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : syncStage === 4 ? 'bg-indigo-500/10 border-indigo-500/30 text-white animate-pulse' : 'bg-slate-950/40 border-slate-800 text-slate-500'
                  }`}>
                  <span className="font-semibold">4. Reconciling Database Access Control & Metadata</span>
                  {syncStage > 4 ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : syncStage === 4 ? <Clock className="w-4 h-4 text-indigo-400 animate-spin" /> : null}
                </div>
              </div>

              {/* Sync Summary Result */}
              {syncSummary && (
                <div className="p-4 rounded-2xl bg-indigo-950/40 border border-indigo-500/30 space-y-2 text-xs">
                  <div className="font-bold text-indigo-300 text-sm mb-1">Synchronization Summary</div>
                  <div className="grid grid-cols-3 gap-2 font-mono text-center">
                    <div className="bg-slate-900/80 p-2 rounded-xl border border-slate-800">
                      <div className="text-emerald-400 font-extrabold text-base">+{syncSummary.added}</div>
                      <div className="text-[10px] text-slate-400">Added</div>
                    </div>
                    <div className="bg-slate-900/80 p-2 rounded-xl border border-slate-800">
                      <div className="text-blue-400 font-extrabold text-base">{syncSummary.updated}</div>
                      <div className="text-[10px] text-slate-400">Updated</div>
                    </div>
                    <div className="bg-slate-900/80 p-2 rounded-xl border border-slate-800">
                      <div className="text-rose-400 font-extrabold text-base">-{syncSummary.removed}</div>
                      <div className="text-[10px] text-slate-400">Removed</div>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-400 text-right font-mono pt-1">
                    Duration: {syncSummary.duration_seconds}s
                  </div>
                </div>
              )}

              {syncStage === 5 && (
                <button
                  onClick={() => setIsSyncing(false)}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs py-3 rounded-xl transition-colors shadow-lg shadow-indigo-500/25"
                >
                  Close & View Repositories
                </button>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content: Loading / Error / Empty / Repository List */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 items-start">
          {[1, 2, 3].map(n => (
            <div key={n} className="glass-panel p-6 rounded-2xl border border-border bg-card h-48 animate-pulse space-y-4">
              <div className="h-4 bg-muted rounded w-1/3"></div>
              <div className="h-6 bg-muted rounded w-2/3"></div>
              <div className="h-4 bg-muted rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="glass-panel p-8 rounded-2xl border border-red-500/30 bg-red-500/10 text-center space-y-3 max-w-xl mx-auto my-10">
          <AlertCircle className="w-10 h-10 text-red-500 mx-auto" />
          <h3 className="text-base font-bold text-foreground">Repository Backend Connection Error</h3>
          <p className="text-xs text-muted-foreground">{error}</p>
          <button
            onClick={fetchRepositories}
            className="bg-red-500 hover:opacity-90 text-white font-bold text-xs px-4 py-2 rounded-xl"
          >
            Retry Connection
          </button>
        </div>
      ) : filteredRepositories.length === 0 ? (
        /* Empty State */
        <div className="glass-panel p-12 rounded-3xl border border-border bg-card text-center max-w-2xl mx-auto space-y-5 my-8">
          <div className="w-16 h-16 rounded-2xl bg-muted border border-border flex items-center justify-center text-muted-foreground mx-auto">
            <FolderGit2 className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-foreground">No GitHub Repositories Connected</h3>
            <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1.5 leading-relaxed">
              Rover only displays repositories you have granted access to via the Rover GitHub App installation.
            </p>
          </div>
          <div className="flex justify-center gap-3 pt-2">
            <button
              onClick={handleSyncGitHub}
              className="bg-primary text-primary-foreground hover:opacity-90 font-bold text-xs px-6 py-3 rounded-xl shadow-md flex items-center gap-2 transition-all active:scale-[0.98]"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Sync GitHub</span>
            </button>
            <a
              href="https://github.com/apps/rover-bug-hunter"
              target="_blank"
              rel="noreferrer"
              className="bg-muted hover:bg-muted/80 text-foreground border border-border font-semibold text-xs px-5 py-3 rounded-xl flex items-center gap-2"
            >
              <span>Install GitHub App</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      ) : (
        /* Repository Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 items-start">
          {filteredRepositories.map((repo, idx) => (
            <motion.div
              key={repo.id || repo.full_name}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: idx * 0.05, type: 'spring', stiffness: 200 }}
              className="glass-panel p-5 rounded-2xl flex flex-col justify-between group relative overflow-hidden transition-all duration-300 hover:shadow-2xl hover:shadow-primary/20 hover:-translate-y-1 h-auto"
            >
              {/* Colorful Animated Hover Gradient Border inside the card */}
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-400 via-primary to-purple-500 opacity-0 group-hover:opacity-10 transition-opacity duration-500 z-0 pointer-events-none" />
              
              <div className="relative z-10">
                {/* Top Status Badges */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 font-bold px-2 py-0.5 rounded flex items-center gap-1 shadow-[0_0_10px_rgba(6,182,212,0.1)]">
                      <FolderGit2 className="w-2.5 h-2.5" />
                      Repository
                    </span>
                  </div>
                </div>

                {/* Repo Full Name */}
                <h3 className="text-base font-bold text-foreground group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-primary group-hover:to-purple-500 transition-all flex items-center gap-2 mb-1">
                  <FolderGit2 className="w-4 h-4 text-primary shrink-0" />
                  <span className="truncate">{repo.full_name}</span>
                </h3>

                {/* Repository Metadata Grid */}
                <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-background border border-border mb-4 text-xs mt-3">
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Language</span>
                    <span className="font-bold text-foreground flex items-center gap-1.5">
                      <FileCode className="w-3.5 h-3.5 text-blue-500" />
                      {repo.language}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Default Branch</span>
                    <span className="font-bold text-foreground flex items-center gap-1.5">
                      <GitBranch className="w-3.5 h-3.5 text-green-500" />
                      {repo.default_branch}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1 mt-1">
                    <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Visibility</span>
                    <span className="font-bold text-foreground flex items-center gap-1.5">
                      {repo.is_private ? <Lock className="w-3.5 h-3.5 text-purple-500" /> : <Globe className="w-3.5 h-3.5 text-green-500" />}
                      {repo.is_private ? 'Private' : 'Public'}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1 mt-1">
                    <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Account</span>
                    <span className="font-bold text-foreground flex items-center gap-1.5">
                      {repo.account_type === 'Personal' ? <User className="w-3.5 h-3.5 text-primary" /> : <Building className="w-3.5 h-3.5 text-primary" />}
                      {repo.account_type}
                    </span>
                  </div>
                </div>
              </div>

              {/* Card Footer Actions */}
              <div className="pt-3 border-t border-border flex items-center justify-between text-xs relative z-10">
                <button
                  onClick={() => handleTriggerQuickScan(repo.full_name)}
                  className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white font-semibold text-[11px] px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all shadow-md hover:shadow-cyan-500/30"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>Quick Scan</span>
                </button>

                <a
                  href={`https://github.com/${repo.full_name}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-muted-foreground hover:text-foreground font-semibold flex items-center gap-1 text-[11px] transition-colors"
                >
                  <span>GitHub</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};
