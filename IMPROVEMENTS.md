# UI/UX Improvements

This document tracks pending UI and design improvements for ShotBuddy.

---

## Aesthetic Improvements

### Refined Color Palette

**Current:** Functional dark theme with green accent, but lacks visual warmth.

**Improvement:**
- Introduce subtle gradient backgrounds (e.g., very subtle radial gradient on main container)
- Add secondary accent color for variety (blue for info states, amber for warnings)
- Soften the pure black backgrounds with slight warmth (#1a1a1c instead of #171717)
- Use color to indicate asset types (subtle tint: images = blue, videos = purple, lipsync = orange)

---

### Typography Hierarchy

**Current:** Limited font weight/size variation.

**Improvement:**
- Increase contrast between header and body text sizes
- Use font-weight 700 for shot names to make them pop
- Add subtle letter-spacing to column headers
- Consider a monospace font for version numbers (v001, v002) for alignment

---

### Thumbnail Polish

**Current:** Basic rectangular thumbnails with overlaid badges.

**Improvement:**
- Add subtle inner shadow/vignette to thumbnails for depth
- Rounded corners with slight border (1px rgba white at 5% opacity)
- Hover state: slight scale (1.02) with shadow lift
- Empty state: use an icon (image/video icon) instead of plain text
- Add subtle gradient overlay at bottom for better badge readability

---

### Micro-interactions & Animations

**Current:** Basic transitions, limited feedback.

**Improvement:**
- Add spring-based easing for more natural feel (`cubic-bezier(0.34, 1.56, 0.64, 1)`)
- Subtle pulse animation on successful upload
- Skeleton shimmer should be smoother and more subtle
- Dropdown menus: add slight scale + fade animation on open
- Version badge: subtle bounce when version changes
- Button press states: slight scale down (0.97) on active

---

### Visual Hierarchy & Spacing

**Current:** Uniform spacing throughout.

**Improvement:**
- Increase padding in header area for breathing room
- Group related elements more tightly (version badge closer to thumbnail edge)
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
- Subtle backdrop blur on header for depth when scrolling
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

### Light Mode Option

**Current:** Dark theme only.

**Improvement:**
- Add light mode toggle in settings
- Use CSS custom properties for easy theming
- Respect system preference (`prefers-color-scheme`)
- Ensure sufficient contrast in both modes

---

### Focus States & Accessibility

**Current:** Basic focus outlines.

**Improvement:**
- Custom focus rings that match the green accent
- Visible focus states on all interactive elements
- Skip-to-content link for keyboard navigation
- Ensure 4.5:1 contrast ratio for all text
- Add `prefers-reduced-motion` support for animations

---

## Usability Improvements

### Expandable Notes Section

**Current:** Notes textarea has fixed max-height (120px), can feel cramped.

**Improvement:**
- Add expand/collapse toggle for notes
- Or: auto-grow textarea that expands with content
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
| High | Expandable notes, Micro-interactions, Thumbnail polish |
| Medium | Search & filter, Typography hierarchy, Visual spacing |
| Low | Light mode, Color palette refinement, Empty states, Accessibility |
