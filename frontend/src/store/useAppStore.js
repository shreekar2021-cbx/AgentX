import { create } from 'zustand'

export const useAppStore = create((set) => ({
  language: 'en',
  selectedCrop: 'Tomato',
  notificationsOpen: false,
  setLanguage: (language) => set({ language }),
  setSelectedCrop: (selectedCrop) => set({ selectedCrop }),
  toggleNotifications: () => set((state) => ({ notificationsOpen: !state.notificationsOpen })),
}))
