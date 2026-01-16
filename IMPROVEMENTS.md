# UI/UX Improvements

This document tracks UI and design improvements for ShotBuddy.

---

## Aesthetic Improvements

### 1. Modern Button System

**Current:** Buttons have inconsistent styling - dark (#3a3a3a), green (#00c851), and red mixed without clear hierarchy.

**Improvement:** Implement a proper button hierarchy:
- **Primary** (green): Main CTAs like "New Shot +", "Save"
- **Secondary** (outlined): Supporting actions like "Cancel", "Open Folder"
- **Ghost** (transparent): Tertiary actions and icon buttons
- Add subtle hover/active state transitions (scale, shadow)

---

### 2. Improved Modal Design

**Current:** Modals are simple dark boxes with no visual depth or polish.

**Improvement:**
- Add subtle box-shadow for elevation
- Use backdrop blur effect on overlay (`backdrop-filter: blur(4px)`)
- Animate modal entrance (fade + slight scale up)
- Better spacing and typography inside modals
- Add subtle border or glow to distinguish from background

---

### 3. Better Notification Toasts

**Current:** Plain colored boxes that slide in with no icons.

**Improvement:**
- Add icons (checkmark for success, X for error, info circle for info)
- Subtle entrance animation (slide + fade)
- Optional action button for undo/retry
- Progress bar showing auto-dismiss timing

---

### 4. Card-Based Shot Layout

**Current:** Rigid table-like grid that feels like a spreadsheet.

**Improvement:**
- Wrap each shot row in a subtle card with rounded corners
- Add hover state with slight elevation/border highlight
- Better visual separation between shots
- Consider optional "compact" vs "comfortable" view toggle

---

### 5. Refined Color Palette

**Current:** Good dark foundation but limited state colors.

**Improvement:**
- Add subtle color variations for interactive states
- Info blue (#3b82f6) for informational elements
- Warning amber (#f59e0b) for caution states
- Better contrast ratios for accessibility
- Subtle gradient accents for headers/CTAs (optional)

---

### 6. Typography & Spacing Polish

**Current:** Functional but tight spacing, especially in grid columns.

**Improvement:**
- Increase line-height for better readability
- More generous padding in interactive elements
- Consistent spacing scale (4px base: 4, 8, 12, 16, 24, 32...)
- Slightly larger touch targets for buttons

---

### 7. Sidebar Toggle Visibility

**Current:** Toggle arrow is barely visible until hovered.

**Improvement:**
- Add subtle background/border to toggle button
- Icon tooltip showing "Show/Hide References"
- Animate arrow rotation smoothly
- Consider collapsible header for sidebar

---

### 8. Light Mode Option

**Current:** Dark theme only.

**Improvement:**
- Add light mode toggle in settings
- Use CSS custom properties for easy theming
- Respect system preference (`prefers-color-scheme`)

---

## Usability Improvements

### 9. Inline Shot Name Editing

**Current:** Uses browser `prompt()` dialog which feels outdated.

**Improvement:**
- Double-click shot name to enter edit mode
- Show text input directly in place
- Save on Enter, cancel on Escape
- Show subtle edit icon on hover to indicate editability

---

### 10. Expandable Notes Section

**Current:** Notes textarea has fixed max-height (120px), can feel cramped.

**Improvement:**
- Add expand/collapse toggle for notes
- Or: auto-grow textarea that expands with content
- Full-screen note editing modal for longer notes

---

### 11. Better Collapsed Shot UI

**Current:** Collapsed rows have tiny 11px gray text, not obviously clickable.

**Improvement:**
- Increase collapsed row height slightly
- Add hover highlight to indicate clickability
- Show small thumbnail preview even when collapsed
- Chevron icon that clearly indicates expand action

---

### 12. Visual Drag Handles

**Current:** No indication that shots can be reordered via drag-and-drop.

**Improvement:**
- Add grip/drag handle icon on left side of shot rows
- Cursor change to `grab` on hover
- Visual feedback during drag (ghost preview, drop indicators)

---

### 13. Search & Filter

**Current:** No way to search or filter shots.

**Improvement:**
- Add search input in header to filter shots by name
- Filter chips for quick filtering (has image, has video, has notes)
- Highlight matching text in search results

---

### 14. Upload Progress Indicators

**Current:** No visual feedback during file uploads.

**Improvement:**
- Progress bar or spinner during upload
- Show upload percentage for large files
- Success/failure indication on completion

---

### 15. Keyboard Shortcuts

**Current:** No keyboard shortcuts documented or implemented.

**Improvement:**
- `Cmd/Ctrl + N`: New shot
- `Cmd/Ctrl + F`: Focus search
- `Escape`: Close modals
- Arrow keys: Navigate between shots
- Add keyboard shortcut hints in tooltips

---

### 16. Better Version Badge Visibility

**Current:** Small 11px badges positioned on thumbnails, hard to see on dark images.

**Improvement:**
- Add semi-transparent background pill behind version text
- Increase font size slightly (12-13px)
- Position consistently outside thumbnail or with guaranteed contrast

---

### 17. Context Menus

**Current:** No right-click context menus.

**Improvement:**
- Right-click on shot: Rename, Delete, Duplicate, Open Folder
- Right-click on thumbnail: Reveal in Finder, Copy Path, Delete Version
- Right-click on reference image: Rename, Delete, Reveal

---

### 18. Responsive Design

**Current:** Fixed widths that may overflow on smaller screens.

**Improvement:**
- Add breakpoints for tablet/laptop screens
- Collapsible sidebar on narrow viewports
- Horizontal scroll or stacked layout for shot grid on mobile

---

## Implementation Priority

| Priority | Items | Impact |
|----------|-------|--------|
| High | 9, 10, 11, 14 | Core usability wins |
| Medium | 1, 2, 3, 4, 12, 13 | Visual polish + features |
| Low | 5, 6, 7, 8, 15, 16, 17, 18 | Nice-to-have refinements |

---

## Notes

Previous code improvements (duplicate logic, path traversal security, error handling, etc.) have all been completed and removed from this document.
