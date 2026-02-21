# UI/UX Improvements

This document tracks pending UI and design improvements for ShotBuddy.

### Visual Hierarchy & Spacing

**Current:** Uniform spacing throughout.

**Improvement:**
- Add visual dividers between shot groups (every 5 or 10 shots)
- Increase gap between thumbnail columns and notes column
- Consider alternating row backgrounds (very subtle, 2% opacity difference)

---

### Header & Navigation

**Current:** Functional but plain header with dropdown menu.

**Improvement:**
- Add subtle bottom border with gradient fade
- Project name could have an icon or colored dot indicator
- Add breadcrumb-style path display for deep project folders
- Add project health indicator (e.g., "12 shots, 8 with images, 4 with videos")

---

### Empty States & Onboarding

**Current:** Basic "No project" message.

**Improvement:**
- Illustrated empty state (simple line art of a clapperboard or film strip)
- Animated arrow pointing to File menu
- Quick-start tips that fade after first use
- "Recent Projects" list for quick access

---

## Usability Improvements

### Expandable Notes Section

**Current:** Notes textarea has fixed max-height (120px), can feel cramped.

**Improvement:**
- Full-screen note editing modal for longer notes

---

### Search & Filter

**Current:** No way to search or filter shots.

**Improvement:**
- Add search input in header to filter shots by name
- Filter chips for quick filtering (has image, has video, has notes)
- Highlight matching text in search results

---

## Implementation Priority

| Priority | Items |
|----------|-------|
| High | Expandable notes |
| Medium | Search & filter, Visual spacing |
| Low | Light mode, Color palette refinement, Empty states, Header & Navigation |
