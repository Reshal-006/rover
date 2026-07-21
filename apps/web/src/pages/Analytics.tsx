import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BarChart3 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar } from 'recharts';

export const Analytics: React.FC = () => {
  const [scanData, setScanData] = useState<any[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('rover_jwt_token');
    fetch('/api/v1/analytics', {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    })
      .then(res => res.json())
      .then(data => setScanData(data.scan_analytics || []))
      .catch(() => {});
  }, []);


  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-black text-foreground tracking-tight flex items-center gap-3">
          <BarChart3 className="w-8 h-8 text-primary" />
          <span>Performance & Remediation Velocity Analytics</span>
        </h1>
        <p className="text-xs text-muted-foreground mt-1">Diagnostic execution runtimes, security velocity, and LLM token efficiency trends.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="p-6 rounded-2xl space-y-4 relative bg-card border border-border bg-gradient-to-br from-primary/5 via-transparent to-transparent hover:from-primary/10 transition-all duration-300 hover:shadow-2xl hover:shadow-primary/5 hover:-translate-y-1 backdrop-blur-xl group overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-muted-foreground" />
            <span>Execution Duration (Seconds)</span>
          </h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={scanData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="name" stroke="#64748B" fontSize={11} />
                <YAxis stroke="#64748B" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', fontSize: '11px', color: '#F8FAFC' }} />
                <Line type="monotone" dataKey="duration" stroke="#06b6d4" strokeWidth={3} dot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.1 }}
          className="p-6 rounded-2xl space-y-4 relative bg-card border border-border bg-gradient-to-br from-primary/5 via-transparent to-transparent hover:from-primary/10 transition-all duration-300 hover:shadow-2xl hover:shadow-primary/5 hover:-translate-y-1 backdrop-blur-xl group overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-muted-foreground" />
            <span>Files Analyzed per Scan</span>
          </h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scanData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="name" stroke="#64748B" fontSize={11} />
                <YAxis stroke="#64748B" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', fontSize: '11px', color: '#F8FAFC' }} />
                <Bar dataKey="bugs" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>
    </div>
  );
};
