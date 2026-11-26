import { create } from "zustand";

/** What the Agenda panel is showing. "closed" means the drawer is hidden. */
export type PanelView = "closed" | "list" | "create" | "details" | "edit";

interface UiState {
  panelView: PanelView;
  /** Event shown in "details" / "edit"; null in the other views. */
  activeEventId: string | null;
  isDeleteModalOpen: boolean;
  /** "Did you really finish it?" dialog of the active event. */
  isCompleteModalOpen: boolean;
  openAgenda: () => void;
  openCreateForm: () => void;
  openEventDetails: (eventId: string) => void;
  editActiveEvent: () => void;
  /** Leaves a form or the details view: back to details from edit, otherwise to the list. */
  goBack: () => void;
  closePanel: () => void;
  setDeleteModalOpen: (open: boolean) => void;
  setCompleteModalOpen: (open: boolean) => void;
}

export const useUiStore = create<UiState>()((set) => ({
  panelView: "closed",
  activeEventId: null,
  isDeleteModalOpen: false,
  isCompleteModalOpen: false,
  openAgenda: () => set({ panelView: "list", activeEventId: null, isDeleteModalOpen: false, isCompleteModalOpen: false }),
  openCreateForm: () => set({ panelView: "create", activeEventId: null, isDeleteModalOpen: false, isCompleteModalOpen: false }),
  openEventDetails: (eventId) =>
    set({ panelView: "details", activeEventId: eventId, isDeleteModalOpen: false, isCompleteModalOpen: false }),
  editActiveEvent: () => set((state) => (state.activeEventId ? { panelView: "edit" } : state)),
  goBack: () =>
    set((state) =>
      state.panelView === "edit"
        ? { panelView: "details" }
        : { panelView: "list", activeEventId: null, isDeleteModalOpen: false, isCompleteModalOpen: false },
    ),
  closePanel: () => set({ panelView: "closed", activeEventId: null, isDeleteModalOpen: false, isCompleteModalOpen: false }),
  setDeleteModalOpen: (isDeleteModalOpen) => set({ isDeleteModalOpen }),
  setCompleteModalOpen: (isCompleteModalOpen) => set({ isCompleteModalOpen }),
}));
