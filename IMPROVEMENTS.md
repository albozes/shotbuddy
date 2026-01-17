# UI/UX Improvements

This document tracks pending UI and design improvements for ShotBuddy.

---

## Aesthetic Improvements

### Card-Based Shot Layout

**Current:** Rigid table-like grid that feels like a spreadsheet.

**Improvement:**
- Wrap each shot row in a subtle card with rounded corners
- Add hover state with slight elevation/border highlight
- Better visual separation between shots
- Consider optional "compact" vs "comfortable" view toggle

---

### Light Mode Option

**Current:** Dark theme only.

**Improvement:**
- Add light mode toggle in settings
- Use CSS custom properties for easy theming
- Respect system preference (`prefers-color-scheme`)

---

## Usability Improvements

### Inline Shot Name Editing

**Current:** Uses browser `prompt()` dialog which feels outdated.

**Improvement:**
- Double-click shot name to enter edit mode
- Show text input directly in place
- Save on Enter, cancel on Escape
- Show subtle edit icon on hover to indicate editability

---

### Expandable Notes Section

**Current:** Notes textarea has fixed max-height (120px), can feel cramped.

**Improvement:**
- Add expand/collapse toggle for notes
- Or: auto-grow textarea that expands with content
- Full-screen note editing modal for longer notes

---

### Better Collapsed Shot UI

**Current:** Collapsed rows have tiny 11px gray text, not obviously clickable.

**Improvement:**
- Increase collapsed row height slightly
- Add hover highlight to indicate clickability
- Show small thumbnail preview even when collapsed
- Chevron icon that clearly indicates expand action

---

### Visual Drag Handles

**Current:** No indication that shots can be reordered via drag-and-drop.

**Improvement:**
- Add grip/drag handle icon on left side of shot rows
- Cursor change to `grab` on hover
- Visual feedback during drag (ghost preview, drop indicators)

---

### Search & Filter

**Current:** No way to search or filter shots.

**Improvement:**
- Add search input in header to filter shots by name
- Filter chips for quick filtering (has image, has video, has notes)
- Highlight matching text in search results

---

### Upload Progress Indicators

**Current:** No visual feedback during file uploads.

**Improvement:**
- Progress bar or spinner during upload
- Show upload percentage for large files
- Success/failure indication on completion

---

### Keyboard Shortcuts

**Current:** No keyboard shortcuts documented or implemented.

**Improvement:**
- `Cmd/Ctrl + N`: New shot
- `Cmd/Ctrl + F`: Focus search
- `Escape`: Close modals
- Arrow keys: Navigate between shots
- Add keyboard shortcut hints in tooltips

---

### Better Version Badge Visibility

**Current:** Small 11px badges positioned on thumbnails, hard to see on dark images.

**Improvement:**
- Add semi-transparent background pill behind version text
- Increase font size slightly (12-13px)
- Position consistently outside thumbnail or with guaranteed contrast

---

### Context Menus

**Current:** No right-click context menus.

**Improvement:**
- Right-click on shot: Rename, Delete, Duplicate, Open Folder
- Right-click on thumbnail: Reveal in Finder, Copy Path, Delete Version
- Right-click on reference image: Rename, Delete, Reveal

---

### Responsive Design

**Current:** Fixed widths that may overflow on smaller screens.

**Improvement:**
- Add breakpoints for tablet/laptop screens
- Collapsible sidebar on narrow viewports
- Horizontal scroll or stacked layout for shot grid on mobile

---

## Implementation Priority

| Priority | Items |
|----------|-------|
| High | Inline editing, Expandable notes, Collapsed UI, Upload progress |
| Medium | Card layout, Drag handles, Search & filter |
| Low | Light mode, Keyboard shortcuts, Version badges, Context menus, Responsive |
