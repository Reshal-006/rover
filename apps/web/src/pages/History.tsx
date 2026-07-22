import React, { useState, useEffect } from 'react';
import { History as HistoryIcon } from 'lucide-react';
import { GlobalLoader } from '../components/GlobalLoader';
import { Timeline } from '../components/Timeline';

export const History: React.FC = () => {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const token = localStorage.getItem('rover_jwt_token');
    fetch('/api/v1/history', {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    })
      .then(res => res.json())
      .then(data => setHistory(data.history || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Map API response to Timeline events
  const timelineEvents = history.map((h, i) => ({
    id: h.scan_id || `scan-${i}`,
    repo: h.repo,
    title: h.bugs > 0 ? `Scan Discovered ${h.bugs} Vulnerabilities` : 'Clean Scan Completed',
    description: `AST symbol trees and syntax graphs built. Telemetry logged. Duration: ${h.duration}`,
    date: h.date,
    type: (h.bugs > 0 ? 'vulnerability' : 'scan') as "scan" | "vulnerability" | "fix" | "pr",
    status: 'completed' as "completed" | "running" | "failed"
  }));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-black text-foreground tracking-tight flex items-center gap-3">
          <HistoryIcon className="w-8 h-8 text-primary" />
          <span>Activity Timeline</span>
        </h1>
        <p className="text-sm text-muted-foreground mt-2 max-w-2xl">Audit log of indexed repositories, AST symbol trees, vulnerability snapshots, and autonomous agent fixes.</p>
      </div>

      {loading ? (
        <GlobalLoader text="Loading timeline..." />
      ) : history.length === 0 ? (
        <div className="glass-panel p-12 rounded-3xl border border-border bg-card text-center max-w-xl mx-auto my-8 space-y-4">
          <HistoryIcon className="w-10 h-10 text-muted-foreground mx-auto" />
          <h3 className="text-base font-bold text-foreground">No Timeline Events Available</h3>
          <p className="text-xs text-muted-foreground">Trigger a codebase scan to start recording the autonomous agent's activity.</p>
        </div>
      ) : (
        <div className="py-6">
          <Timeline events={timelineEvents} />
        </div>
      )}
    </div>
  );
};
