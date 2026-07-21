import { create } from 'zustand';
import { ScanResult, Finding, Repository } from '../types';

interface RoverState {
  activeScanId: string | null;
  latestScan: ScanResult | null;
  selectedFinding: Finding | null;
  activeRepository: Repository | null;
  repositories: Repository[];
  isScanning: boolean;
  
  setActiveScanId: (id: string | null) => void;
  setLatestScan: (scan: ScanResult | null) => void;
  setSelectedFinding: (finding: Finding | null) => void;
  setActiveRepository: (repo: Repository | null) => void;
  setRepositories: (repos: Repository[]) => void;
  setIsScanning: (scanning: boolean) => void;
}

export const useRoverStore = create<RoverState>((set) => ({
  activeScanId: null,
  latestScan: null,
  selectedFinding: null,
  activeRepository: null,
  repositories: [],
  isScanning: false,

  setActiveScanId: (id) => set({ activeScanId: id }),
  setLatestScan: (scan) => set({ latestScan: scan }),
  setSelectedFinding: (finding) => set({ selectedFinding: finding }),
  setActiveRepository: (repo) => set({ activeRepository: repo }),
  setRepositories: (repos) => set({ repositories: repos }),
  setIsScanning: (scanning) => set({ isScanning: scanning }),
}));
