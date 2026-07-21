import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  autoMode: boolean;
  autoPR: boolean;
  autoRetry: boolean;
  scanType: 'quick' | 'deep';
  maxScans: number;
  notifyComplete: boolean;
  notifyPR: boolean;
  notifyFail: boolean;
  notifySync: boolean;
  animations: boolean;
  compact: boolean;
  
  // Actions
  setAutoMode: (v: boolean) => void;
  setAutoPR: (v: boolean) => void;
  setAutoRetry: (v: boolean) => void;
  setScanType: (v: 'quick' | 'deep') => void;
  setMaxScans: (v: number) => void;
  setNotifyComplete: (v: boolean) => void;
  setNotifyPR: (v: boolean) => void;
  setNotifyFail: (v: boolean) => void;
  setNotifySync: (v: boolean) => void;
  setAnimations: (v: boolean) => void;
  setCompact: (v: boolean) => void;
  
  // API Sync
  fetchSettings: () => Promise<void>;
  saveSettings: (settings: Partial<SettingsState>) => Promise<void>;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      autoMode: true,
      autoPR: true,
      autoRetry: false,
      scanType: 'deep',
      maxScans: 3,
      notifyComplete: true,
      notifyPR: true,
      notifyFail: true,
      notifySync: false,
      animations: true,
      compact: false,
      
      setAutoMode: (v) => { set({ autoMode: v }); get().saveSettings({ autoMode: v }); },
      setAutoPR: (v) => { set({ autoPR: v }); get().saveSettings({ autoPR: v }); },
      setAutoRetry: (v) => { set({ autoRetry: v }); get().saveSettings({ autoRetry: v }); },
      setScanType: (v) => { set({ scanType: v }); get().saveSettings({ scanType: v }); },
      setMaxScans: (v) => { set({ maxScans: v }); get().saveSettings({ maxScans: v }); },
      setNotifyComplete: (v) => { set({ notifyComplete: v }); get().saveSettings({ notifyComplete: v }); },
      setNotifyPR: (v) => { set({ notifyPR: v }); get().saveSettings({ notifyPR: v }); },
      setNotifyFail: (v) => { set({ notifyFail: v }); get().saveSettings({ notifyFail: v }); },
      setNotifySync: (v) => { set({ notifySync: v }); get().saveSettings({ notifySync: v }); },
      setAnimations: (v) => { set({ animations: v }); get().saveSettings({ animations: v }); },
      setCompact: (v) => { set({ compact: v }); get().saveSettings({ compact: v }); },
      
      fetchSettings: async () => {
        const token = localStorage.getItem('rover_jwt_token');
        if (!token) return;
        try {
          const res = await fetch('/api/v1/users/settings', {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            if (Object.keys(data).length > 0) {
              set(data);
            }
          }
        } catch (e) {
          console.error('Failed to fetch settings from backend', e);
        }
      },
      
      saveSettings: async (newSettings) => {
        const token = localStorage.getItem('rover_jwt_token');
        if (!token) return;
        
        // We merge with current state to send the full object
        const fullSettings = { ...get(), ...newSettings };
        // Remove functions from the object before sending
        const { fetchSettings, saveSettings, setAutoMode, setAutoPR, setAutoRetry, setScanType, setMaxScans, setNotifyComplete, setNotifyPR, setNotifyFail, setNotifySync, setAnimations, setCompact, ...dataToSave } = fullSettings as any;
        
        try {
          await fetch('/api/v1/users/settings', {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(dataToSave)
          });
        } catch (e) {
          console.error('Failed to sync settings to backend', e);
        }
      }
    }),
    {
      name: 'rover-settings-storage',
    }
  )
);

