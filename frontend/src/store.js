import { create } from 'zustand'

export const useAppStore = create((set) => ({
  tab: 'guide',
  setTab: (tab) => set({ tab }),

  health: null,
  setHealth: (health) => set({ health }),

  messages: [],
  addMessage: (message) => set((s) => ({ messages: [...s.messages, message] })),

  costResult: null,
  setCostResult: (costResult) => set({ costResult }),

  docResult: null,
  setDocResult: (docResult) => set({ docResult }),
}))
