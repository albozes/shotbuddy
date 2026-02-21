# Manual Testing Guide

How to verify ShotBuddy features after updates. Run through each section to confirm nothing is broken.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Start the server: `python run.py`
3. Open `http://127.0.0.1:5001/` in a browser

---

## Project Management

- **Create project** — Click "Create New Project at Path", enter a base path and name. Verify the project directory is created with `shots/`, `shots/wip/`, `shots/latest_images/`, `shots/latest_videos/`, `_legacy/` subdirectories.
- **Open project** — Click "Load Project from Path", enter a valid project path. Shots should load and display.
- **Invalid path** — Enter a non-existent or invalid path. An error message should appear.
- **Recent projects** — Open several projects, then check that previously opened projects appear in the recent list.

## Shot Management

- **Create shot** — Click "New Shot +". A new shot (SH010, SH020, etc.) appears at the end of the list.
- **Create between shots** — Drag a file onto the dropzone between two existing shots. A new shot is inserted between them with the correct number.
- **Rename shot** — Click a shot name, type a new name, press Enter. All versioned files, prompts, and thumbnails should rename.
- **Cancel rename** — Press Escape during rename. The name reverts.
- **Delete empty shot** — Delete button is only visible on shots with no image and no video. Clicking it removes the shot and its directory.
- **Shot limit** — Creating shots past SH999 should show a "Project is Full" modal.

## File Upload

- **Drag and drop** — Drag an image (jpg/png/webp) or video (mp4/mov) onto a shot's drop zone. The file uploads and a thumbnail appears.
- **Click to upload** — Click an empty drop zone, select a file from the dialog.
- **Version numbering** — Upload a second file to the same slot. Version badge should update (v001 → v002). Check `shots/wip/<shot>/images/` or `videos/` for versioned files.
- **Unsupported file type** — Try uploading a .txt or .exe. An error should appear.
- **PNG metadata** — Upload a PNG with embedded prompt metadata. The prompt should auto-extract and save.

## Version Management

- **Version badge** — After multiple uploads, the badge shows the latest version number.
- **Restore previous version** — Click the version badge dropdown, select an older version. The latest folder updates to that version, thumbnail regenerates, and a success notification shows.

## Prompts

- **Open prompt modal** — Click the "P" button on any image/video with a version. The modal shows shot name, asset type, version dropdown, and a textarea.
- **Save prompt** — Type text, click "Save & Close". A prompt file is created (e.g. `SH010_image_prompt.txt`).
- **Switch versions** — Use the version dropdown in the modal. Prompt content loads for the selected version.
- **Copy from previous version** — On v002+, click "Copy prompt from previous version". Content from the prior version fills in.

## Reference Images

- **Upload** — Drag an image onto the "+ Add Image" zone in the right sidebar, or click to select. The image appears in the grid.
- **Rename** — Click the filename, enter a new name. File and thumbnail rename.
- **Delete** — Delete a reference image. It is removed from the grid and the filesystem.
- **Reveal** — Click a reference image to reveal it in the file browser.

## Thumbnails

- **Auto-generation** — Uploading an asset generates a thumbnail automatically.
- **Batch loading** — Loading a project with many shots fires a batch thumbnail request. Thumbnails appear together.
- **Refresh thumbnails** — Open Settings, click "Refresh Thumbnails". All thumbnails regenerate and a count notification appears.

## Video Preview

- **Hover preview** — Hover over a video thumbnail. A video preview plays (muted, looping). Moving the mouse away hides it.

## Reveal in File Browser

- **Thumbnail click** — Click a thumbnail to reveal the file in the OS file browser.
- **Behavior setting** — In Settings, "Thumbnail click behavior" switches between revealing the file in the latest folder vs the specific versioned file in wip/.

## Settings

- **Color theme** — Open Settings, select a theme (forest-green, cinema-gold, midnight-blue, coral-sunset, ocean-depths). Colors update immediately. Save and reload to verify persistence.
- **Thumbnail click behavior** — Change the setting, save, then click a thumbnail to confirm the correct file opens.
- **Persistence** — Settings survive page reload and project re-open.

## Collapse / Expand

- **Collapse shot** — Click the collapse button on a shot row. Content hides, only the name is visible.
- **Expand shot** — Click anywhere on the collapsed row. Content reappears.
- **Persistence** — Reload the page. Collapsed shots stay collapsed.

## Quick-Start Onboarding Tips

- **First launch** — Clear `localStorage` (`localStorage.removeItem('shotbuddy_onboarding')`) and reload. Tip 1 should appear pointing at the project toggle button.
- **Tip progression** — Dismiss each tip with "Got it". The next applicable tip appears after a short delay.
- **Skip all** — Click "Skip all" on any tip. All remaining tips should disappear and not come back.
- **Persistence** — Dismiss a few tips, reload the page. Dismissed tips should not reappear.
- **Reset tips** — Open Settings, click "Reset Quick-Start Tips". Tips restart from the beginning.
- **Full flow** — Walk through the entire user journey (no project → open project → create shot → upload asset). Each tip should appear at the right moment targeting the correct UI element.

## UI & Interactions

- **Notifications** — Successful actions show green toast, errors show red. They disappear after a few seconds.
- **Sidebar toggle** — Click the arrow on the right sidebar to collapse/expand the reference images panel.
- **Scroll position memory** — Scroll down, upload a file or rename a shot (page reloads). The page scrolls back to the same position.
- **Skeleton loading** — On initial load, skeleton placeholders appear before shots render.

## Error Cases

- **Invalid project path** — Entering a bad path shows an error.
- **Unsupported file type** — Uploading a non-image/video shows an error.
- **Duplicate shot name** — Renaming to an existing shot name shows an error.
- **Empty project** — A project with no shots shows a "No shots yet" state with a create button.

---

## Quick Smoke Test Checklist

- [ ] App starts and loads at `http://127.0.0.1:5001/`
- [ ] Create a new project
- [ ] Create 3 shots
- [ ] Upload an image to the first shot
- [ ] Upload a video to the second shot
- [ ] Upload a second image version to the first shot (version badge shows v002)
- [ ] Rename the third shot
- [ ] Delete the third shot (empty)
- [ ] Add a reference image
- [ ] Open the prompt modal for the first shot's image, save a prompt
- [ ] Change color theme in Settings
- [ ] Collapse and expand a shot row
- [ ] Reload the page — settings, collapsed state, and scroll position should persist
