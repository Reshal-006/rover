import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ShieldAlert,
  GitPullRequest,
  Sparkles,
  Search,
  FolderGit2,
  Loader2,
  Zap
} from 'lucide-react';
import { useRoverStore } from '../store/useRoverStore';
import { useAuthStore } from '../store/useAuthStore';
import { toast } from 'sonner';

export const Dashboard: React.FC = () => {
  const [repoUrl, setRepoUrl] = useState('');
  const { isScanning, setIsScanning, setActiveScanId } = useRoverStore();
  const { user } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);

  const [summary, setSummary] = useState<any>({
    total_repositories: 0,
    total_vulnerabilities: 0,
    pull_requests_merged: 0,
    ai_compute_savings: '94.2%',
    issue_severity_breakdown: []
  });

  const [repositories, setRepositories] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any[]>([]);

  const loadDashboardData = async () => {
    const token = localStorage.getItem('rover_jwt_token');
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

    try {
      const [sumRes, repoRes, analyticsRes] = await Promise.all([
        fetch('/api/v1/dashboard/summary', { headers }).then(res => res.ok ? res.json() : null),
        fetch('/api/v1/repositories', { headers }).then(res => res.ok ? res.json() : null),
        fetch('/api/v1/analytics', { headers }).then(res => res.ok ? res.json() : null)
      ]);

      if (sumRes) setSummary(sumRes);
      if (repoRes && repoRes.repositories) setRepositories(repoRes.repositories);
      if (analyticsRes && analyticsRes.scan_analytics) setAnalytics(analyticsRes.scan_analytics);

    } catch (e) {
      console.error("Failed to load dashboard data", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const pollScanStatus = (scanId: string, repo: string) => {
    const token = localStorage.getItem('rover_jwt_token');
    const headers: Record<string, string> = token ? { 'Authorization': `Bearer ${token}` } : {};

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/scans/${scanId}`, { headers });
        if (res.ok) {
          const scan = await res.json();
          if (scan.status === 'completed') {
            clearInterval(interval);
            setIsScanning(false);
            const count = scan.bugs ? scan.bugs.length : 0;
            toast.success(`Scan completed for ${repo}! Found ${count} vulnerabilities.`);
            loadDashboardData();
          } else if (scan.status === 'failed') {
            clearInterval(interval);
            setIsScanning(false);
            toast.error(`Scan failed for ${repo}: ${scan.error || 'Unknown error'}`);
          }
        }
      } catch (e) {
        // Silent retry
      }
    }, 1500);

    setTimeout(() => {
      clearInterval(interval);
      setIsScanning(false);
    }, 180000);
  };

  const handleStartScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl) {
      toast.error('Please enter a GitHub repository URL');
      return;
    }

    setIsScanning(true);
    toast.info('Initiating autonomous codebase scan...');

    try {
      const token = localStorage.getItem('rover_jwt_token');
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/v1/scans', {
        method: 'POST',
        headers,
        body: JSON.stringify({ repository_url: repoUrl })
      });
      const data = await res.json();
      if (res.ok && data.scan_id) {
        setActiveScanId(data.scan_id);
        toast.info(`Scan started (ID: ${data.scan_id}). Running static & LLM analysis...`);
        pollScanStatus(data.scan_id, repoUrl);
      } else {
        setIsScanning(false);
        toast.error(data.detail || 'Scan failed to trigger');
      }
    } catch (err) {
      setIsScanning(false);
      toast.error('Failed to reach backend API');
    }
  };

  // Framer Motion Animation Variants
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 15, scale: 0.98 },
    show: { opacity: 1, y: 0, scale: 1, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  const renderGradeBadge = (grade: string) => {
    const isA = grade.startsWith('A');
    const isB = grade.startsWith('B');
    if (isA) return <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">Grade {grade}</span>;
    if (isB) return <span className="text-[10px] font-bold text-sky-400 bg-sky-500/10 px-2.5 py-1 rounded-full border border-sky-500/20">Grade {grade}</span>;
    return <span className="text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20">Grade {grade}</span>;
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col xl:flex-row items-start gap-6 pb-16 bg-noise relative z-10"
    >
      {/* Primary Left Column */}
      <div className="flex-1 space-y-6">

        {/* Main Hero Header */}
        <motion.div variants={itemVariants} className="relative glass-panel rounded-3xl p-6 overflow-hidden bg-card border-border h-auto">
          <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-primary/5 to-transparent pointer-events-none" />
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-2">
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 }}
                className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-[11px] font-bold tracking-wide uppercase"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Autonomous Operations</span>
              </motion.div>
              <h1 className="text-3xl md:text-4xl font-black text-foreground tracking-tight leading-tight">
                Welcome back, <br />
                <span className="bg-gradient-to-r from-cyan-400 via-primary to-purple-500 bg-clip-text text-transparent">{user?.name || 'Reshal-006'}</span>
              </h1>
              <p className="text-sm text-muted-foreground max-w-xl leading-relaxed font-medium">
                Rover is actively monitoring your repositories, scanning commits for AST & LLM vulnerabilities, and auto-dispatching pull request fixes.
              </p>
            </div>
          </div>
        </motion.div>

        {/* KPI Cards */}
        <motion.div variants={containerVariants} className="grid grid-cols-1 sm:grid-cols-2 gap-4">

          <motion.div variants={itemVariants} className="group relative p-5 rounded-2xl overflow-hidden cursor-default transition-all flex flex-col justify-between h-auto min-h-[110px] bg-card border border-border hover:shadow-xl hover:shadow-blue-500/10 hover:-translate-y-1 backdrop-blur-xl">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-transparent to-transparent group-hover:from-blue-500/20 transition-all duration-500 pointer-events-none" />
            <div className="relative z-10 flex items-center justify-between mb-2">
              <span className="text-xs font-bold tracking-wide text-muted-foreground uppercase">Scanned Repos</span>
              <div className="w-7 h-7 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary transition-colors">
                <FolderGit2 className="w-3.5 h-3.5" />
              </div>
            </div>
            <div className="relative z-10 flex items-baseline gap-3">
              <div className="text-3xl font-black text-foreground tracking-tight">{summary.total_repositories}</div>
              <div className="text-[10px] text-green-500 dark:text-emerald-400 font-medium whitespace-nowrap">
                Tracked & Secure
              </div>
            </div>
          </motion.div>

          <motion.div variants={itemVariants} className="group relative p-5 rounded-2xl overflow-hidden cursor-default transition-all flex flex-col justify-between h-auto min-h-[110px] bg-card border border-border hover:shadow-xl hover:shadow-red-500/10 hover:-translate-y-1 backdrop-blur-xl">
            <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 via-transparent to-transparent group-hover:from-red-500/20 transition-all duration-500 pointer-events-none" />
            <div className="relative z-10 flex items-center justify-between mb-2">
              <span className="text-xs font-bold tracking-wide text-muted-foreground uppercase">Resolved Flaws</span>
              <div className="w-7 h-7 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 transition-colors">
                <ShieldAlert className="w-3.5 h-3.5" />
              </div>
            </div>
            <div className="relative z-10 flex items-baseline gap-3">
              <div className="text-3xl font-black text-foreground tracking-tight">{summary.resolved_vulnerabilities}</div>
              <div className="text-[10px] text-green-500 dark:text-emerald-400 font-medium whitespace-nowrap">
                Secured codebase
              </div>
            </div>
          </motion.div>

          <motion.div variants={itemVariants} className="group relative p-5 rounded-2xl overflow-hidden cursor-default transition-all flex flex-col justify-between h-auto min-h-[110px] bg-card border border-border hover:shadow-xl hover:shadow-purple-500/10 hover:-translate-y-1 backdrop-blur-xl">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 via-transparent to-transparent group-hover:from-purple-500/20 transition-all duration-500 pointer-events-none" />
            <div className="relative z-10 flex items-center justify-between mb-2">
              <span className="text-xs font-bold tracking-wide text-muted-foreground uppercase">PRs Merged</span>
              <div className="w-7 h-7 rounded-full bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-500 transition-colors">
                <GitPullRequest className="w-3.5 h-3.5" />
              </div>
            </div>
            <div className="relative z-10 flex items-baseline gap-3">
              <div className="text-3xl font-black text-foreground tracking-tight">{summary.pull_requests_merged}</div>
              <div className="text-[10px] text-purple-500 font-medium whitespace-nowrap">
                Auto-resolved
              </div>
            </div>
          </motion.div>

          <motion.div variants={itemVariants} className="group relative p-5 rounded-2xl overflow-hidden cursor-default transition-all flex flex-col justify-between h-auto min-h-[110px] bg-card border border-border hover:shadow-xl hover:shadow-orange-500/10 hover:-translate-y-1 backdrop-blur-xl">
            <div className="absolute inset-0 bg-gradient-to-br from-orange-500/10 via-transparent to-transparent group-hover:from-orange-500/20 transition-all duration-500 pointer-events-none" />
            <div className="relative z-10 flex items-center justify-between mb-2">
              <span className="text-xs font-bold tracking-wide text-muted-foreground uppercase">AI Savings</span>
              <div className="w-7 h-7 rounded-full bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-500 transition-colors">
                <Zap className="w-3.5 h-3.5" />
              </div>
            </div>
            <div className="relative z-10 flex items-baseline gap-3">
              <div className="text-3xl font-black text-foreground tracking-tight">{summary.ai_compute_savings}</div>
              <div className="text-[10px] text-muted-foreground font-medium whitespace-nowrap">
                Dev time saved
              </div>
            </div>
          </motion.div>
        </motion.div>

      </div>

      {/* Right Secondary Column */}
      <div className="w-full xl:w-[400px] space-y-6 shrink-0">

        {/* Autonomous Scan Control Center */}
        <motion.div variants={itemVariants} className="glass-panel p-6 rounded-3xl space-y-6 relative overflow-hidden bg-card border-border h-auto">
          <div className="absolute -top-20 -right-20 w-40 h-40 bg-primary/20 rounded-full blur-[60px] pointer-events-none" />

          <div className="relative z-10">
            <h2 className="text-2xl font-black text-foreground tracking-tight leading-tight mb-2">Deep Scan</h2>
            <p className="text-sm text-muted-foreground font-medium">Deploy an autonomous agent to analyze and patch your codebase instantly.</p>
          </div>

          <form onSubmit={handleStartScan} className="space-y-5 relative z-10">
            <div className="relative group">
              <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" />
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="Repository URL..."
                className="w-full bg-background border border-border rounded-2xl pl-12 pr-4 py-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>

            {/* Highly Dynamic Button */}
            <motion.button
              type="submit"
              disabled={isScanning}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="relative w-full group overflow-hidden rounded-2xl disabled:opacity-50 disabled:pointer-events-none bg-gradient-to-r from-primary to-purple-600 text-primary-foreground shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-shadow"
            >
              <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div className="relative px-6 py-4 flex items-center justify-center font-bold text-sm tracking-wide">
                {isScanning ? 'Initializing Agent...' : 'Launch Agent'}
              </div>
            </motion.button>
          </form>
        </motion.div>

        {/* System Metrics */}
        <motion.div variants={itemVariants} className="glass-panel p-6 rounded-3xl space-y-6 bg-card border-border h-auto">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-foreground tracking-wide uppercase">Scan Metrics</h2>
            <div className="flex gap-1.5">
              <div className="w-1 h-1 bg-muted-foreground/30 rounded-full" />
              <div className="w-1 h-1 bg-muted-foreground/30 rounded-full" />
              <div className="w-1 h-1 bg-muted-foreground/30 rounded-full" />
            </div>
          </div>

          <div className="text-xs text-muted-foreground mb-2 font-medium">Bugs found per recent scan</div>

          {/* Dynamic Bar Chart */}
          <div className="h-48 flex items-end gap-2 pt-4 border-l border-b border-border pb-2 px-2 relative">
            <div className="absolute left-0 top-0 text-[9px] text-muted-foreground -translate-x-full pr-2 font-medium">10</div>
            <div className="absolute left-0 top-1/4 text-[9px] text-muted-foreground -translate-x-full pr-2 font-medium">7</div>
            <div className="absolute left-0 top-2/4 text-[9px] text-muted-foreground -translate-x-full pr-2 font-medium">5</div>
            <div className="absolute left-0 top-3/4 text-[9px] text-muted-foreground -translate-x-full pr-2 font-medium">2</div>
            <div className="absolute left-0 bottom-0 text-[9px] text-muted-foreground -translate-x-full pr-2 font-medium">0</div>

            {analytics.length === 0 ? (
              <div className="w-full text-center text-xs text-muted-foreground py-10">No scan data available</div>
            ) : (
              analytics.map((run, i) => {
                // Normalize height (assume max bugs ~10 for chart scale)
                const heightPercent = Math.min(100, Math.max(5, (run.bugs / 10) * 100));
                return (
                  <div key={i} className="flex-1 h-full flex flex-col items-center justify-end gap-2 group relative">
                    <div className="absolute -top-8 bg-foreground text-background font-bold text-[10px] py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity z-20 pointer-events-none whitespace-nowrap shadow-md">
                      {run.name}: {run.bugs} bugs
                    </div>
                    <motion.div
                      initial={{ height: 0 }}
                      animate={{ height: `${heightPercent}%` }}
                      transition={{ duration: 1, delay: i * 0.05, ease: "easeOut" }}
                      className="w-full bg-primary/80 rounded-t-sm hover:bg-primary transition-colors cursor-pointer"
                    />
                  </div>
                );
              })
            )}
          </div>
        </motion.div>
      </div>

    </motion.div>
  );
};
