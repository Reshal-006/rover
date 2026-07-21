import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, Wrench, CheckCircle2, FileCode, Cpu, Sparkles, AlertTriangle } from 'lucide-react';
import { MonacoDiffViewer } from '../components/MonacoDiffViewer';
import { Finding } from '../types';
import { toast } from 'sonner';
import { GlobalLoader } from '../components/GlobalLoader';

export const BugExplorer: React.FC = () => {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [isFixing, setIsFixing] = useState<boolean>(false);

  useEffect(() => {
    const token = localStorage.getItem('rover_jwt_token');
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

    fetch('/api/v1/findings', { headers })
      .then(res => res.json())
      .then(data => {
        const list = data.findings || [];
        
        const severityWeight: Record<string, number> = {
          'critical': 4,
          'high': 3,
          'medium': 2,
          'low': 1
        };

        list.sort((a: Finding, b: Finding) => {
          const weightA = severityWeight[a.severity?.toLowerCase()] || 0;
          const weightB = severityWeight[b.severity?.toLowerCase()] || 0;
          return weightB - weightA;
        });

        setFindings(list);
        if (list.length > 0) setSelectedFinding(list[0]);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleTriggerFix = async () => {
    if (!selectedFinding) return;
    setIsFixing(true);
    toast.info(`Initializing AI fix pipeline for ${selectedFinding.title}...`);

    try {
      const token = localStorage.getItem('rover_jwt_token');
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const targetRepoUrl = selectedFinding.repository_url || 'https://github.com/Reshal-006/rover';
      const res = await fetch(`/api/v1/fixes/${selectedFinding.id}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          repository_url: targetRepoUrl,
          title: selectedFinding.title,
          description: selectedFinding.description
        })
      });
      const data = await res.json();
      if (res.ok) {
        toast.success(`Autonomous PR trigger launched! Fix ID: ${data.fix_id}`);
      } else {
        toast.error(data.detail || 'Fix pipeline failed');
      }
    } catch (err) {
      toast.error('Failed to connect to backend API');
    } finally {
      setIsFixing(false);
    }
  };


  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
          <ShieldAlert className="w-6 h-6 text-primary" />
          <span>Bug Explorer & AI Patch Generator</span>
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Inspect AST static analysis findings for your most recently scanned repository.
          {findings.length > 0 && findings[0].repository_url && (
            <span className="block mt-1 font-mono text-primary font-bold">
              Target Repo: {findings[0].repository_url.replace('https://github.com/', '')}
            </span>
          )}
        </p>
      </div>

      {loading ? (
        <GlobalLoader text="Loading AST static analysis findings..." />
      ) : findings.length === 0 ? (
        <div className="glass-panel p-12 rounded-3xl border border-border bg-card text-center max-w-xl mx-auto my-8 space-y-4">
          <ShieldAlert className="w-10 h-10 text-green-500 mx-auto" />
          <h3 className="text-base font-bold text-foreground">Zero Vulnerabilities Discovered</h3>
          <p className="text-xs text-muted-foreground">Your connected GitHub App repositories are clean. Run a scan from the Dashboard to analyze code.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Findings List */}
          <div className="lg:col-span-5 space-y-3">
            {findings.map((finding, idx) => (
              <motion.div
                key={finding.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: idx * 0.08 }}
                onClick={() => setSelectedFinding(finding)}
                className={`relative p-4 rounded-2xl border cursor-pointer transition-all duration-300 group overflow-hidden ${
                  selectedFinding?.id === finding.id
                    ? 'bg-muted border-border shadow-md ring-1 ring-border'
                    : 'bg-card border-border bg-gradient-to-br from-primary/5 via-transparent to-transparent hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-0.5'
                }`}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                <div className="flex items-center justify-between mb-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wider ${
                    finding.severity === 'critical' ? 'bg-red-500/10 text-red-500 border border-red-500/20' : 'bg-orange-500/10 text-orange-500 border border-orange-500/20'
                  }`}>
                    {finding.severity}
                  </span>
                  <span className="text-[11px] font-mono text-muted-foreground">{finding.filepath}:{finding.line_number}</span>
                </div>
                <h3 className={`text-xs font-bold mb-1 leading-snug ${finding.is_fixed ? 'text-muted-foreground line-through' : 'text-foreground'}`}>{finding.title}</h3>
                <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">{finding.description}</p>
              </motion.div>
            ))}
          </div>

          {/* Right Patch Preview & Diff */}
          <div className="lg:col-span-7 space-y-5">
            {selectedFinding && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className="relative p-6 rounded-2xl space-y-5 bg-card border border-border bg-gradient-to-br from-primary/5 via-transparent to-transparent transition-all duration-300 hover:shadow-2xl hover:shadow-primary/5 hover:-translate-y-1 backdrop-blur-xl group overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h2 className={`text-base font-bold tracking-tight ${selectedFinding.is_fixed ? 'text-muted-foreground line-through' : 'text-foreground'}`}>{selectedFinding.title}</h2>
                    <p className="text-xs font-mono text-primary mt-0.5">{selectedFinding.filepath}</p>
                  </div>
                  <button
                    onClick={handleTriggerFix}
                    disabled={isFixing}
                    className={`font-bold text-xs px-5 py-2.5 rounded-xl flex items-center justify-center gap-2 shadow-md transition-all duration-150 active:scale-[0.98] disabled:opacity-50 shrink-0 ${
                      selectedFinding.is_fixed 
                        ? 'bg-muted hover:bg-muted/80 text-foreground border border-border' 
                        : 'bg-primary hover:opacity-90 text-primary-foreground border border-transparent'
                    }`}
                  >
                    <Wrench className="w-3.5 h-3.5" />
                    <span>
                      {isFixing 
                        ? 'Generating Patch...' 
                        : selectedFinding.is_fixed 
                          ? 'You want to fix it again?' 
                          : 'Auto-Fix & Open PR'}
                    </span>
                  </button>
                </div>

                <div className="text-xs text-foreground leading-relaxed bg-primary/10 p-4 rounded-xl border border-primary/20 shadow-sm space-y-1 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-primary/50"></div>
                  <div className="flex items-center gap-2 text-primary font-bold mb-1 pl-2">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>AI Diagnostic Reasoning</span>
                  </div>
                  <p className="text-foreground pl-2">{selectedFinding.reasoning}</p>
                </div>

                {/* Monaco Diff Viewer */}
                <div className="pt-2">
                  <div className="bg-[#1e1e1e] border border-[#333] rounded-t-lg p-2 flex items-center justify-between shadow-md">
                     <div className="flex gap-1.5 ml-2">
                        <div className="w-2.5 h-2.5 rounded-full bg-red-500/80"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-orange-500/80"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-green-500/80"></div>
                     </div>
                     <span className="text-[10px] text-muted-foreground font-mono tracking-wider px-4 uppercase">rover-diff-agent</span>
                  </div>
                  <div className="border border-[#333] border-t-0 rounded-b-lg overflow-hidden shadow-2xl">
                    <MonacoDiffViewer
                      originalCode={selectedFinding.code_snippet || ''}
                      modifiedCode={selectedFinding.suggested_fix || ''}
                      filename={selectedFinding.filepath}
                    />
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
