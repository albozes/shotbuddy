        let currentProject = null;
        let shots = [];
        let savedScrollY = 0;
        let savedRowId = null;
        const NEW_SHOT_DROP_TEXT = 'Drop an asset here to create a new shot.';
        document.documentElement.style.setProperty('--new-shot-drop-text', `'${NEW_SHOT_DROP_TEXT}'`);

        // Column visibility configuration
        const COLUMN_CONFIG = [
            { id: 'shot_name', label: 'Shot Name', width: '110px', fixed: true },
            { id: 'image',     label: 'Image',     width: '160px', fixed: false, defaultVisible: true },
            { id: 'video',     label: 'Video',     width: '160px', fixed: false, defaultVisible: true },
            { id: 'lipsync',   label: 'Lip Sync',  width: '160px', fixed: false, defaultVisible: false },
            { id: 'notes',     label: 'Notes',     width: '1fr',   fixed: true },
            { id: 'collapse',  label: '',           width: '50px',  fixed: true },
        ];

        function getVisibleColumnIds() {
            return (typeof currentSettings !== 'undefined' && currentSettings.visible_columns)
                || COLUMN_CONFIG.filter(c => c.fixed || c.defaultVisible).map(c => c.id);
        }

        function getVisibleColumns() {
            const visible = getVisibleColumnIds();
            return COLUMN_CONFIG.filter(c => c.fixed || visible.includes(c.id));
        }

        function applyGridTemplate() {
            const template = getVisibleColumns().map(c => c.width).join(' ');
            document.documentElement.style.setProperty('--grid-columns', template);
        }

        function isColumnVisible(columnId) {
            return getVisibleColumnIds().includes(columnId);
        }

        function renderGridHeader() {
            const header = document.getElementById('main-grid-header');
            if (!header) return;
            header.innerHTML = '';
            for (const col of getVisibleColumns()) {
                const cell = document.createElement('div');
                cell.className = 'grid-header-cell';
                cell.dataset.column = col.id;
                cell.textContent = col.label;
                if (col.id === 'collapse') cell.classList.add('collapse-header');
                header.appendChild(cell);
            }
        }

        // Column context menu functions

        function initColumnContextMenu() {
            const menu = document.getElementById('column-context-menu');

            document.addEventListener('contextmenu', function(e) {
                const header = e.target.closest('.grid-header');
                if (!header) return;
                e.preventDefault();
                showColumnContextMenu(e.clientX, e.clientY);
            });

            document.addEventListener('click', function(e) {
                if (!e.target.closest('#column-context-menu')) {
                    hideColumnContextMenu();
                }
            });

            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') hideColumnContextMenu();
            });

            menu.addEventListener('change', function(e) {
                const checkbox = e.target.closest('input[data-column]');
                if (!checkbox) return;
                toggleColumnVisibility(checkbox.dataset.column, checkbox.checked);
            });
        }

        function showColumnContextMenu(x, y) {
            const menu = document.getElementById('column-context-menu');

            menu.querySelectorAll('input[data-column]').forEach(cb => {
                cb.checked = isColumnVisible(cb.dataset.column);
            });

            menu.style.left = x + 'px';
            menu.style.top = y + 'px';
            menu.style.display = 'block';

            requestAnimationFrame(() => {
                const rect = menu.getBoundingClientRect();
                if (rect.right > window.innerWidth) {
                    menu.style.left = (window.innerWidth - rect.width - 8) + 'px';
                }
                if (rect.bottom > window.innerHeight) {
                    menu.style.top = (window.innerHeight - rect.height - 8) + 'px';
                }
                menu.classList.add('show');
            });
        }

        function hideColumnContextMenu() {
            const menu = document.getElementById('column-context-menu');
            menu.classList.remove('show');
            setTimeout(() => { menu.style.display = 'none'; }, 150);
        }

        async function toggleColumnVisibility(columnId, visible) {
            const toggleable = COLUMN_CONFIG.filter(c => !c.fixed);
            let visibleColumns = currentSettings.visible_columns
                || toggleable.filter(c => c.defaultVisible).map(c => c.id);

            visibleColumns = [...visibleColumns];

            if (visible && !visibleColumns.includes(columnId)) {
                visibleColumns.push(columnId);
            } else if (!visible) {
                visibleColumns = visibleColumns.filter(id => id !== columnId);
            }

            currentSettings.visible_columns = visibleColumns;

            applyGridTemplate();
            renderShots();

            try {
                await fetch('/api/settings/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ visible_columns: visibleColumns })
                });
            } catch (e) {
                console.error('Failed to save column visibility:', e);
            }
        }

        // App bar functions

        function toggleProjectDrawer() {
            const appBar = document.querySelector('.app-bar');
            appBar.classList.toggle('drawer-open');
            if (appBar.classList.contains('drawer-open')) {
                loadRecentProjects();
                document.getElementById('manual-path-input').focus();
            }
        }

        function closeProjectDrawer() {
            document.querySelector('.app-bar').classList.remove('drawer-open');
        }

        async function closeProject() {
            try {
                const response = await fetch('/api/project/close', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    currentProject = null;
                    shots = [];
                    showSetupScreen();
                    showNotification('Project closed');
                } else {
                    showNotification(result.error || 'Failed to close project', 'error');
                }
            } catch (error) {
                console.error('Error closing project:', error);
                showNotification('Unexpected error closing project', 'error');
            }
        }

        async function loadRecentProjects() {
            try {
                const response = await fetch('/api/project/recent');
                const result = await response.json();
                const container = document.getElementById('recent-projects');
                container.innerHTML = '';

                if (result.success && result.data && result.data.length > 0) {
                    const label = document.createElement('span');
                    label.className = 'recent-label';
                    label.textContent = 'Recent';
                    container.appendChild(label);

                    result.data.forEach(project => {
                        const chip = document.createElement('button');
                        chip.className = 'recent-chip';
                        chip.textContent = project.name;
                        chip.title = project.path;
                        chip.addEventListener('click', () => openRecentProject(project.path));
                        container.appendChild(chip);
                    });
                }
            } catch (error) {
                console.error('Failed to load recent projects:', error);
            }
        }

        function openRecentProject(path) {
            document.getElementById('manual-path-input').value = path;
            loadProjectFromManualPath();
        }

        // Close drawer when clicking outside
        document.addEventListener('click', function(e) {
            const appBar = document.querySelector('.app-bar');
            if (appBar.classList.contains('drawer-open') && !e.target.closest('.app-bar')) {
                closeProjectDrawer();
            }
        });

        async function loadProjectFromManualPath() {
            const input = document.getElementById('manual-path-input');
            const path = input.value.trim();

            if (!path) {
                showNotification("Please enter a full path to a project folder.", "error");
                return;
            }

            try {
                const response = await fetch('/api/project/open', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
                });

                const result = await response.json();

                if (result.success) {
                currentProject = result.data;
                showMainInterface();
                loadShots();
                showNotification(`Opened project "${result.data.name}"`);
                } else {
                showNotification(result.error || 'Failed to open project', 'error');
                }
            } catch (error) {
                console.error("Error loading project:", error);
                showNotification("Unexpected error loading project", "error");
            }
        }

        function openCreateProjectModal() {
            const basePath = document.getElementById('manual-path-input').value.trim();
            if (!basePath) {
                showNotification("Please enter a full path to a project folder.", "error");
                return;
            }
            document.getElementById('new-project-name').value = '';
            const modal = document.getElementById('create-project-modal');
            modal.style.display = 'flex';
            // Trigger animation
            requestAnimationFrame(() => {
                modal.classList.add('show');
            });
            document.getElementById('new-project-name').focus();
        }

        function closeCreateProjectModal() {
            const modal = document.getElementById('create-project-modal');
            modal.classList.remove('show');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 200);
        }

        async function confirmCreateProject() {
            const basePath = document.getElementById('manual-path-input').value.trim();
            const projectName = document.getElementById('new-project-name').value.trim();

            if (!basePath) {
                showNotification("Please enter a full path to a project folder.", "error");
                return;
            }
            if (!projectName) {
                showNotification("Please enter a project name.", "error");
                return;
            }

            try {
                const response = await fetch('/api/project/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: basePath, name: projectName })
                });

                const result = await response.json();

                if (result.success) {
                    currentProject = result.data;
                    closeCreateProjectModal();
                    showMainInterface();
                    loadShots();
                    showNotification(`Created project "${result.data.name}"`);
                } else {
                    showNotification(result.error || 'Failed to create project', 'error');
                }
            } catch (error) {
                console.error('Error creating project:', error);
                showNotification('Unexpected error creating project', 'error');
            }
        }

    
        // Initialize app
        document.addEventListener('DOMContentLoaded', function() {
            document.addEventListener('click', handlePromptButtonClick);
            initColumnContextMenu();
            checkForProject();

            // Global drag detection for showing drop zones between shots
            let dragCounter = 0;
            document.addEventListener('dragenter', (e) => {
                dragCounter++;
                if (e.dataTransfer.types.includes('Files')) {
                    document.body.classList.add('dragging-files');
                }
            });
            document.addEventListener('dragleave', (e) => {
                dragCounter--;
                if (dragCounter <= 0 ||
                    e.clientX <= 0 || e.clientY <= 0 ||
                    e.clientX >= window.innerWidth || e.clientY >= window.innerHeight) {
                    dragCounter = 0;
                    document.body.classList.remove('dragging-files');
                }
            });
            document.addEventListener('drop', (e) => {
                dragCounter = 0;
                document.body.classList.remove('dragging-files');
            });
            document.addEventListener('dragend', (e) => {
                dragCounter = 0;
                document.body.classList.remove('dragging-files');
            });

            // Sticky header detection — add 'stuck' class when header is pinned
            const gridHeader = document.getElementById('main-grid-header');
            if (gridHeader) {
                const sentinel = document.createElement('div');
                sentinel.style.height = '1px';
                sentinel.style.width = '100%';
                sentinel.style.pointerEvents = 'none';
                gridHeader.parentNode.insertBefore(sentinel, gridHeader);

                const observer = new IntersectionObserver(([entry]) => {
                    gridHeader.classList.toggle('stuck', !entry.isIntersecting);
                }, { rootMargin: '-49px 0px 0px 0px' });
                observer.observe(sentinel);
            }
        });

        function handlePromptButtonClick(event) {
            const btn = event.target.closest('.prompt-button');
            if (!btn) {
                return;
            }
            event.stopPropagation();
            const shot = btn.dataset.shot;
            const type = btn.dataset.type;
            const version = parseInt(btn.dataset.version, 10);
            openPromptModal(shot, type, version);
        }

        async function checkForProject() {
            try {
                const response = await fetch('/api/project/current');
                const result = await response.json();

                if (result.success && result.data) {
                    currentProject = result.data;
                    showMainInterface();
                    loadShots();
                } else {
                    showSetupScreen();
                }
            } catch (error) {
                console.error('Error checking project:', error);
                showSetupScreen();
            }
        }

        function showSetupScreen() {
            document.getElementById('main-interface').style.display = 'none';
            document.getElementById('setup-screen').style.display = 'flex';
            // Auto-expand the drawer and set placeholder name
            document.getElementById('project-toggle-name').textContent = 'Open a Project';
            document.querySelector('.app-bar').classList.add('drawer-open');
            document.getElementById('app-bar-controls').style.display = 'none';
            document.getElementById('close-project-btn').style.display = 'none';
            loadRecentProjects();
            activateOnboarding();
            setTimeout(() => checkOnboardingTips(), 600);
        }

        function showMainInterface() {
            document.getElementById('setup-screen').style.display = 'none';
            document.getElementById('main-interface').style.display = 'block';
            // Ensure skeleton is visible and shot-grid hidden when transitioning from setup screen
            document.getElementById('skeleton-loading').style.display = 'block';
            document.getElementById('shot-grid').style.display = 'none';
            // Update app bar
            document.getElementById('project-toggle-name').textContent = currentProject.name;
            document.getElementById('app-bar-controls').style.display = '';
            document.getElementById('close-project-btn').style.display = '';
            closeProjectDrawer();
            const input = document.getElementById('manual-path-input');
            if (input && currentProject && currentProject.path) {
                input.value = currentProject.path;
            }
            deactivateOnboarding();
        }

        async function loadShots(rowId = null) {
            captureScroll(rowId);
            // Show skeleton loading, hide actual grid
            document.getElementById('skeleton-loading').style.display = 'block';
            document.getElementById('shot-grid').style.display = 'none';

            // Wait for settings so column visibility is correct before rendering
            await settingsReady;

            const skeletonStart = Date.now();
            const MIN_SKELETON_TIME = 400; // Minimum time to show skeleton (ms)

            try {
                const response = await fetch('/api/shots');
                const result = await response.json();

                if (result.success) {
                    shots = result.data;
                    renderShots();

                    // Ensure skeleton shows for minimum time to avoid jarring flash
                    const elapsed = Date.now() - skeletonStart;
                    const remaining = Math.max(0, MIN_SKELETON_TIME - elapsed);

                    setTimeout(() => {
                        document.getElementById('skeleton-loading').style.display = 'none';
                        document.getElementById('shot-grid').style.display = 'block';
                        restoreScroll();
                        startLazyThumbnailLoading();
                        checkOnboardingTips();

                        // Trigger upload success animation if pending
                        if (window.pendingUploadAnimation) {
                            const { shotName, type } = window.pendingUploadAnimation;
                            const thumbnail = document.querySelector(`#shot-row-${shotName} .drop-zone[ondragover*="${type}"] .preview-thumbnail`);
                            if (thumbnail) {
                                thumbnail.classList.add('upload-success');
                                setTimeout(() => thumbnail.classList.remove('upload-success'), 700);
                            }
                            window.pendingUploadAnimation = null;
                        }
                    }, remaining);

                    loadReferenceImages();
                } else {
                    showNotification(result.error || 'Failed to load shots', 'error');
                    document.getElementById('skeleton-loading').style.display = 'none';
                }
            } catch (error) {
                console.error('Error loading shots:', error);
                showNotification('Error loading shots', 'error');
                document.getElementById('skeleton-loading').style.display = 'none';
            }
        }

        function renderShots() {
            applyGridTemplate();
            renderGridHeader();
            const shotList = document.getElementById("shot-list");
            shotList.innerHTML = "";

            if (shots.length === 0) {
                const emptyState = document.createElement("div");
                emptyState.className = "empty-shots-state";
                emptyState.innerHTML = `
                    <p>No shots yet.</p>
                    <button class="btn btn-primary" onclick="addNewShotAfter(null)">Create First Shot</button>
                `;
                // Add drop zone for empty state
                emptyState.addEventListener("dragover", (e) => handleDropZoneDragOver(e, null));
                emptyState.addEventListener("dragleave", handleDropZoneDragLeave);
                emptyState.addEventListener("drop", (e) => handleDropZoneDrop(e, null));
                shotList.appendChild(emptyState);
                return;
            }

            // Add drop zone before first shot
            const firstDropZone = createDropBetweenZone(null);
            shotList.appendChild(firstDropZone);

            shots.forEach((shot, index) => {
                const shotRow = createShotRow(shot);
                shotList.appendChild(shotRow);

                // Add drop zone after each shot
                const dropZone = createDropBetweenZone(shot.name);
                shotList.appendChild(dropZone);
            });

            restoreScroll();
        }

        function createDropBetweenZone(afterShotName) {
            const zone = document.createElement("div");
            zone.className = "drop-between-zone";
            zone.setAttribute("data-after-shot", afterShotName || "");

            // Add insert button
            const insertBtn = document.createElement("button");
            insertBtn.className = "between-insert-btn";
            insertBtn.title = "Insert new shot";
            insertBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>';
            insertBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                addNewShotAfter(afterShotName);
            });
            zone.appendChild(insertBtn);

            zone.addEventListener("dragover", (e) => handleDropZoneDragOver(e, afterShotName));
            zone.addEventListener("dragleave", handleDropZoneDragLeave);
            zone.addEventListener("drop", (e) => handleDropZoneDrop(e, afterShotName));
            return zone;
        }

        function handleDropZoneDragOver(event, afterShotName) {
            event.preventDefault();
            const types = event.dataTransfer.types;
            if (types && Array.from(types).includes('Files')) {
                event.currentTarget.classList.add('drag-over');
            }
        }

        function handleDropZoneDragLeave(event) {
            event.currentTarget.classList.remove('drag-over');
        }

        async function handleDropZoneDrop(event, afterShotName) {
            event.preventDefault();
            event.currentTarget.classList.remove('drag-over');

            const files = event.dataTransfer.files;
            if (files.length === 0) return;

            try {
                // Create new shot
                const response = await fetch('/api/shots/create-between', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ after_shot: afterShotName || null })
                });

                const result = await response.json();

                if (result.success) {
                    const newShot = result.data;
                    showNotification(`Shot ${newShot.name} created`);

                    // Upload the file to the new shot
                    const file = files[0];
                    const fileType = getFileType(file.name);

                    if (fileType) {
                        await uploadFile(file, newShot.name, fileType);
                    } else {
                        showNotification('Unsupported file type', 'error');
                        loadShots(`shot-row-${newShot.name}`);
                    }
                } else {
                    if (result.error && result.error.includes('shot number would exceed 999')) {
                        showShotLimitModal();
                    } else {
                        showNotification(result.error || 'Failed to create shot', 'error');
                    }
                }
            } catch (error) {
                console.error('Error creating shot:', error);
                showNotification('Error creating shot', 'error');
            }
        }

        function createShotRow(shot) {
            const row = document.createElement('div');
            row.className = 'shot-row';
            row.id = `shot-row-${shot.name}`;

            // Check if shot is collapsed
            const isCollapsed = currentSettings.collapsed_shots && currentSettings.collapsed_shots.includes(shot.name);
            if (isCollapsed) {
                row.classList.add('collapsed');
            }

            // Check if shot is empty (no image, no video, no lipsync)
            const hasLipsync = shot.lipsync && (
                shot.lipsync.driver?.version > 0 ||
                shot.lipsync.target?.version > 0 ||
                shot.lipsync.result?.version > 0 ||
                (shot.lipsync.custom_files && shot.lipsync.custom_files.length > 0)
            );
            const isEmpty = shot.image.version === 0 && shot.video.version === 0 && !hasLipsync;
            const deleteBtn = isEmpty
                ? `<button class="shot-action-btn delete-btn" onclick="deleteShot('${shot.name}')" title="Delete empty shot"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14" height="14"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg></button>`
                : '';

            row.innerHTML = `
                <div class="shot-name" onclick="editShotName(this, '${shot.name}')">${shot.name}</div>
                ${isColumnVisible('image') ? createDropZone(shot, 'image') : ''}
                ${isColumnVisible('video') ? createDropZone(shot, 'video') : ''}
                ${isColumnVisible('lipsync') ? createLipsyncZone(shot) : ''}
                <div class="notes-cell">
                    <textarea class="notes-input"
                              placeholder="Add notes..."
                              onchange="saveNotes('${shot.name}', this.value)"
                              onblur="saveNotes('${shot.name}', this.value)">${shot.notes || ''}</textarea>
                    <button class="notes-expand-btn" onclick="openNotesModal('${shot.name}')" title="Expand notes">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14" height="14"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9m11.25-5.25v4.5m0-4.5h-4.5m4.5 0L15 9m-11.25 11.25v-4.5m0 4.5h4.5m-4.5 0L9 15m11.25 5.25v-4.5m0 4.5h-4.5m4.5 0L15 15" /></svg>
                    </button>
                </div>
                <div class="collapse-cell">
                    <button class="collapse-button"
                            onclick="toggleShotCollapse('${shot.name}')"
                            title="Hide">
                        <span class="collapse-arrow">▼</span>
                    </button>
                </div>
                ${deleteBtn ? `<div class="shot-action-buttons">${deleteBtn}</div>` : ''}
            `;

            return row;
        }

        function createDropZone(shot, type) {
            const file = shot[type];
            const hasFile = file.version > 0;

            if (hasFile) {
                const thumbnailUrl = file.thumbnail ? `${file.thumbnail}?v=${Date.now()}` : null;
                const needsLazyLoad = file.version > 0 && !file.thumbnail;
                const thumbnailStyle = thumbnailUrl ?
                    `background-image: url('${thumbnailUrl}'); background-size: cover; background-position: center;` :
                    'background: var(--color-bg-hover);';

                // Add video preview attributes for video thumbnails
                const videoAttrs = type === 'video' && file.file ?
                    `data-video-src="${file.file}" onmouseenter="showVideoPreview(this)" onmouseleave="hideVideoPreview(this)"` : '';

                // Build version dropdown items (newest first)
                const activeVersion = file.active_version || file.version;
                let versionItems = '';
                for (let v = file.version; v >= 1; v--) {
                    const isCurrent = v === activeVersion;
                    versionItems += `<div class="version-dropdown-item${isCurrent ? ' current' : ''}"
                                         data-shot="${shot.name}"
                                         data-type="${type}"
                                         data-version="${v}"
                                         onclick="selectVersion(event, '${shot.name}', '${type}', ${v})">v${String(v).padStart(3, '0')}</div>`;
                }

                return `
                    <div class="drop-zone"
                         ondragover="handleDragOver(event, '${type}')"
                         ondrop="handleDrop(event, '${shot.name}', '${type}')"
                         ondragleave="handleDragLeave(event)">
                        <div class="file-preview">
                            <div class="preview-thumbnail ${type === 'video' ? 'video-thumbnail' : ''}${needsLazyLoad ? ' loading' : ''}"
                                style="${thumbnailStyle}"
                                ${needsLazyLoad ? `data-lazy-thumb="true" data-shot="${shot.name}" data-asset-type="${type}"` : ''}
                                ${videoAttrs}
                                onclick="revealFile('${file.file}', '${shot.name}', '${type}')"></div>

                            <div class="version-dropdown-container">
                                <div class="version-badge" onclick="toggleShotVersionDropdown(event, this)">v${String(activeVersion).padStart(3, '0')}</div>
                                <div class="version-dropdown-menu">${versionItems}</div>
                            </div>
                            <button class="prompt-button"
                                    title="View and edit prompt"
                                    data-shot="${shot.name}"
                                    data-type="${type}"
                                    data-version="${file.version}">P</button>
                        </div>
                    </div>
                `;
            } else {
                return `
                    <div class="drop-zone empty"
                         onclick="openFileDialog('${shot.name}', '${type}')"
                         ondragover="handleDragOver(event, '${type}')"
                         ondrop="handleDrop(event, '${shot.name}', '${type}')"
                         ondragleave="handleDragLeave(event)">
                        <div class="drop-placeholder">
                            ${type === 'image'
                                ? '<svg class="drop-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" /></svg>'
                                : '<svg class="drop-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" /></svg>'
                            }
                        </div>
                    </div>
                `;
            }
        }

        function createLipsyncZone(shot) {
            const lipsync = shot.lipsync;
            const bestThumb = lipsync.best_thumbnail;
            const hasAudioOnly = lipsync.has_audio_only;
            const customFiles = lipsync.custom_files || [];

            // Count total files
            let totalFiles = customFiles.length;
            for (const part of ['driver', 'target', 'result']) {
                if (lipsync[part] && lipsync[part].version > 0) totalFiles++;
            }
            const hasFiles = totalFiles > 0;

            let defaultContent = '';
            if (hasFiles && bestThumb) {
                const thumbUrl = `${bestThumb}?v=${Date.now()}`;
                defaultContent = `
                    <div class="lipsync-default"
                         style="background-image: url('${thumbUrl}');"
                         onclick="revealLipsyncFolder('${shot.name}')">
                        ${totalFiles > 1 ? `<span class="lipsync-file-count">${totalFiles} files</span>` : ''}
                    </div>`;
            } else if (hasFiles && hasAudioOnly) {
                defaultContent = `
                    <div class="lipsync-default"
                         style="background: var(--color-bg-hover); display: flex; align-items: center; justify-content: center;"
                         onclick="revealLipsyncFolder('${shot.name}')">
                        <svg class="lipsync-audio-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="28" height="28"><path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" /></svg>
                        ${totalFiles > 1 ? `<span class="lipsync-file-count">${totalFiles} files</span>` : ''}
                    </div>`;
            } else if (hasFiles) {
                // Has files but no thumbnail yet (loading)
                defaultContent = `
                    <div class="lipsync-default"
                         style="background: var(--color-bg-hover);"
                         onclick="revealLipsyncFolder('${shot.name}')">
                        <span class="lipsync-file-count">${totalFiles} file${totalFiles > 1 ? 's' : ''}</span>
                    </div>`;
            } else {
                // Empty — show lip sync icon placeholder
                defaultContent = `
                    <div class="lipsync-default empty">
                        <svg class="drop-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" /></svg>
                    </div>`;
            }

            // Quadrant drop overlay (shown on drag, and on hover when empty)
            const quadrantOverlay = `
                <div class="lipsync-drop-overlay">
                    <div class="lipsync-quadrant"
                         onclick="openLipsyncFileDialog('${shot.name}', 'driver')"
                         ondragover="handleLipsyncQuadrantDragOver(event)"
                         ondrop="handleDrop(event, '${shot.name}', 'driver')"
                         ondragleave="handleLipsyncQuadrantDragLeave(event)">
                        <span class="quadrant-label">Driver</span>
                    </div>
                    <div class="lipsync-quadrant"
                         onclick="openLipsyncFileDialog('${shot.name}', 'target')"
                         ondragover="handleLipsyncQuadrantDragOver(event)"
                         ondrop="handleDrop(event, '${shot.name}', 'target')"
                         ondragleave="handleLipsyncQuadrantDragLeave(event)">
                        <span class="quadrant-label">Target</span>
                    </div>
                    <div class="lipsync-quadrant"
                         onclick="openLipsyncFileDialog('${shot.name}', 'result')"
                         ondragover="handleLipsyncQuadrantDragOver(event)"
                         ondrop="handleDrop(event, '${shot.name}', 'result')"
                         ondragleave="handleLipsyncQuadrantDragLeave(event)">
                        <span class="quadrant-label">Result</span>
                    </div>
                    <div class="lipsync-quadrant"
                         onclick="openLipsyncFileDialog('${shot.name}', 'lipsync_custom')"
                         ondragover="handleLipsyncQuadrantDragOver(event)"
                         ondrop="handleLipsyncCustomDrop(event, '${shot.name}')"
                         ondragleave="handleLipsyncQuadrantDragLeave(event)">
                        <span class="quadrant-label">Custom</span>
                    </div>
                </div>`;

            return `<div class="lipsync-cell${hasFiles ? '' : ' hover-active'}"
                         ondragenter="handleLipsyncCellDragEnter(event)"
                         ondragover="handleLipsyncCellDragOver(event)"
                         ondragleave="handleLipsyncCellDragLeave(event)"
                         ondrop="handleLipsyncCellDrop(event)">
                        ${defaultContent}
                        ${quadrantOverlay}
                    </div>`;
        }

        // Lipsync cell drag handlers — show/hide quadrant overlay
        let lipsyncDragCounter = 0;

        function clearAllLipsyncDragState() {
            document.querySelectorAll('.lipsync-cell.drag-active').forEach(c => c.classList.remove('drag-active'));
            lipsyncDragCounter = 0;
        }

        function handleLipsyncCellDragEnter(event) {
            event.preventDefault();
            const cell = event.currentTarget;
            if (!cell.classList.contains('drag-active')) {
                clearAllLipsyncDragState();
            }
            lipsyncDragCounter++;
            cell.classList.add('drag-active');
        }

        function handleLipsyncCellDragOver(event) {
            event.preventDefault();
        }

        function handleLipsyncCellDragLeave(event) {
            lipsyncDragCounter--;
            if (lipsyncDragCounter <= 0) {
                lipsyncDragCounter = 0;
                event.currentTarget.classList.remove('drag-active');
            }
        }

        function handleLipsyncCellDrop(event) {
            clearAllLipsyncDragState();
        }

        // Quadrant-level drag handlers
        function handleLipsyncQuadrantDragOver(event) {
            event.preventDefault();
            event.stopPropagation();
            event.currentTarget.classList.add('drag-over');
        }

        function handleLipsyncQuadrantDragLeave(event) {
            event.currentTarget.classList.remove('drag-over');
        }

        function openLipsyncFileDialog(shotName, fileType) {
            // Driver and Result only accept video/audio; Target and Custom accept images too
            const acceptsImages = (fileType !== 'driver' && fileType !== 'result');
            const accept = acceptsImages ? 'video/*,audio/*,image/*' : 'video/*,audio/*';

            const input = document.createElement('input');
            input.type = 'file';
            input.accept = accept;
            input.style.display = 'none';
            input.addEventListener('change', () => {
                if (input.files && input.files[0]) {
                    if (fileType === 'lipsync_custom') {
                        pendingCustomLipsyncFile = input.files[0];
                        pendingCustomLipsyncShot = shotName;
                        openLipsyncCustomModal();
                    } else {
                        uploadFile(input.files[0], shotName, fileType);
                    }
                }
                input.remove();
            });
            document.body.appendChild(input);
            input.click();
        }

        // Custom lipsync drop — stores file temporarily and shows label modal
        let pendingCustomLipsyncFile = null;
        let pendingCustomLipsyncShot = null;

        function handleLipsyncCustomDrop(event, shotName) {
            event.preventDefault();
            event.currentTarget.classList.remove('drag-over');
            clearAllLipsyncDragState();

            const files = event.dataTransfer.files;
            if (files.length === 0) return;

            pendingCustomLipsyncFile = files[0];
            pendingCustomLipsyncShot = shotName;
            openLipsyncCustomModal();
        }

        function openLipsyncCustomModal() {
            const modal = document.getElementById('lipsync-custom-modal');
            const input = document.getElementById('lipsync-custom-label-input');
            modal.style.display = 'flex';
            input.value = '';
            requestAnimationFrame(() => {
                modal.classList.add('show');
                input.focus();
            });

            // Enter key to confirm
            input.onkeydown = function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    confirmLipsyncCustomLabel();
                }
            };
        }

        function closeLipsyncCustomModal() {
            const modal = document.getElementById('lipsync-custom-modal');
            modal.classList.remove('show');
            setTimeout(() => { modal.style.display = 'none'; }, 200);
            pendingCustomLipsyncFile = null;
            pendingCustomLipsyncShot = null;
        }

        async function confirmLipsyncCustomLabel() {
            const input = document.getElementById('lipsync-custom-label-input');
            const label = input.value.trim();
            if (!label) {
                input.focus();
                return;
            }
            if (!pendingCustomLipsyncFile || !pendingCustomLipsyncShot) return;

            const formData = new FormData();
            formData.append('file', pendingCustomLipsyncFile);
            formData.append('shot_name', pendingCustomLipsyncShot);
            formData.append('file_type', 'lipsync_custom');
            formData.append('custom_label', label);

            closeLipsyncCustomModal();

            try {
                const response = await fetch('/api/shots/upload', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                if (result.success) {
                    showNotification(`Uploaded custom lipsync file`);
                    await loadShots();
                } else {
                    showNotification(result.error || 'Upload failed', 'error');
                }
            } catch (e) {
                showNotification('Upload failed: ' + e.message, 'error');
            }
        }

        async function revealLipsyncFolder(shotName) {
            try {
                await fetch('/api/shots/open-folder', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ shot_name: shotName, subfolder: 'lipsync' })
                });
            } catch (e) {
                console.error('Failed to open lipsync folder:', e);
            }
        }

        async function addNewShot() {
            try {
                const response = await fetch('/api/shots', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });

                const result = await response.json();

                if (result.success) {
                    shots.push(result.data);
                    captureScroll(`shot-row-${result.data.name}`);
                    renderShots();
                    restoreScroll();
                    showNotification(`Shot ${result.data.name} created`);
                } else {
                    if (result.error && result.error.includes('shot number would exceed 999')) {
                        showShotLimitModal();
                    } else {
                        showNotification(result.error || 'Failed to create shot', 'error');
                    }
                }
            } catch (error) {
                console.error('Error creating shot:', error);
                showNotification('Error creating shot', 'error');
            }
        }

        async function addNewShotAfter(afterShot) {
            try {
                const response = await fetch('/api/shots/create-between', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ after_shot: afterShot || null })
                });

                const result = await response.json();

                if (result.success) {
                    const index = afterShot ? shots.findIndex(s => s.name === afterShot) + 1 : 0;
                    shots.splice(index, 0, result.data);
                    captureScroll(`shot-row-${result.data.name}`);
                    renderShots();
                    restoreScroll();
                    showNotification(`Shot ${result.data.name} created`);
                } else {
                    if (result.error && result.error.includes('shot number would exceed 999')) {
                        showShotLimitModal();
                    } else {
                        showNotification(result.error || 'Failed to create shot', 'error');
                    }
                }
            } catch (error) {
                console.error('Error creating shot:', error);
                showNotification('Error creating shot', 'error');
            }
        }

        async function deleteShot(shotName) {
            try {
                const response = await fetch('/api/shots/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ shot_name: shotName })
                });

                const result = await response.json();

                if (result.success) {
                    const index = shots.findIndex(s => s.name === shotName);
                    if (index !== -1) {
                        shots.splice(index, 1);
                    }
                    renderShots();
                    showNotification(`Shot ${shotName} deleted`);
                } else {
                    showNotification(result.error || 'Failed to delete shot', 'error');
                }
            } catch (error) {
                console.error('Error deleting shot:', error);
                showNotification('Error deleting shot', 'error');
            }
        }

        // Drag and drop handlers
        function handleDragOver(event, fileType) {
            event.preventDefault();
            event.currentTarget.classList.add('drag-over');
        }

        function handleDragLeave(event) {
            event.currentTarget.classList.remove('drag-over');
        }

        async function handleDrop(event, shotName, expectedType) {
            event.preventDefault();
            event.currentTarget.classList.remove('drag-over');

            const files = event.dataTransfer.files;
            if (files.length === 0) {
                showNotification('No files dropped', 'error');
                return;
            }

            const file = files[0];

            // Driver and Result only accept video/audio, not images
            const imageExts = ['.jpg', '.jpeg', '.png', '.webp'];
            if ((expectedType === 'driver' || expectedType === 'result') &&
                imageExts.some(ext => file.name.toLowerCase().endsWith(ext))) {
                showNotification(`${expectedType.charAt(0).toUpperCase() + expectedType.slice(1)} does not accept image files`, 'error');
                return;
            }

            await uploadFile(file, shotName, expectedType);
        }

        async function uploadFile(file, shotName, fileType) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('shot_name', shotName);
            formData.append('file_type', fileType);

            try {
                showNotification('Uploading file...');
                
                const response = await fetch('/api/shots/upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    showNotification(`${file.name} uploaded successfully!`);
                    // Store upload target for animation after reload
                    window.pendingUploadAnimation = { shotName, type: fileType };
                    loadShots(`shot-row-${shotName}`); // Refresh and keep scroll
                } else {
                    showNotification(result.error || 'Upload failed', 'error');
                }
            } catch (error) {
                console.error('Upload error:', error);
                showNotification('Upload failed', 'error');
            }
        }

        function showNotification(message, type = 'success') {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = `notification ${type}`;
            notification.classList.add('show');

            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        }

        function captureScroll(rowId = null) {
            savedScrollY = window.pageYOffset;
            savedRowId = rowId;
        }

        function restoreScroll() {
            if (savedRowId) {
                const el = document.getElementById(savedRowId);
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    savedRowId = null;
                    return;
                }
            }
            window.scrollTo({ top: savedScrollY });
            savedRowId = null;
        }

        function getFileType(filename) {
            const ext = filename.toLowerCase().split('.').pop();
            const imageExts = ['jpg', 'jpeg', 'png', 'webp'];
            const videoExts = ['mp4', 'mov'];

            if (imageExts.includes(ext)) return 'image';
            if (videoExts.includes(ext)) return 'video';
            return null;
        }

        function openFileDialog(shotName, fileType) {
            const input = document.createElement('input');
            input.type = 'file';
            if (fileType === 'image') {
                input.accept = 'image/*';
            } else if (fileType === 'video') {
                input.accept = 'video/*';
            }
            input.style.display = 'none';
            input.addEventListener('change', () => {
                if (input.files && input.files[0]) {
                    uploadFile(input.files[0], shotName, fileType);
                }
                input.remove();
            });
            document.body.appendChild(input);
            input.click();
        }

        async function saveNotes(shotName, notes) {
            const shot = shots.find(s => s.name === shotName);
            if (shot) {
                shot.notes = notes;
            }

            try {
                const response = await fetch('/api/shots/notes', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        shot_name: shotName,
                        notes: notes
                    })
                });
                
                const result = await response.json();
                
                if (!result.success) {
                    showNotification(result.error || 'Failed to save notes', 'error');
                }
                // Don't show success notification for notes to avoid spam
            } catch (error) {
                console.error('Error saving notes:', error);
                showNotification('Error saving notes', 'error');
            }
        }

let _notesModalTimeout = null;

function openNotesModal(shotName) {
    if (_notesModalTimeout) {
        clearTimeout(_notesModalTimeout);
        _notesModalTimeout = null;
    }
    const modal = document.getElementById('notes-modal');
    modal.dataset.shot = shotName;
    document.getElementById('notes-modal-title').textContent = `${shotName} — Notes`;
    const shot = shots.find(s => s.name === shotName);
    const textarea = document.getElementById('notes-modal-text');
    textarea.value = shot ? (shot.notes || '') : '';
    modal.style.display = 'flex';
    requestAnimationFrame(() => {
        modal.classList.add('show');
        textarea.focus();
    });
}

function closeNotesModal() {
    const modal = document.getElementById('notes-modal');
    modal.classList.remove('show');
    _notesModalTimeout = setTimeout(() => {
        modal.style.display = 'none';
        _notesModalTimeout = null;
    }, 200);
}

function saveNotesModal() {
    const modal = document.getElementById('notes-modal');
    const shotName = modal.dataset.shot;
    const notes = document.getElementById('notes-modal-text').value;
    const row = document.querySelector(`.shot-row[data-shot="${CSS.escape(shotName)}"]`);
    if (row) {
        const inlineTextarea = row.querySelector('.notes-input');
        if (inlineTextarea) inlineTextarea.value = notes;
    }
    saveNotes(shotName, notes);
    closeNotesModal();
}

function editShotName(element, currentName) {
    // Prevent editing if already in edit mode
    if (element.querySelector('.shot-name-input')) {
        return;
    }

    // Store original text and clear element
    const originalText = element.textContent;
    element.textContent = '';

    // Create input field
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'shot-name-input';
    input.value = currentName;

    // Add input to element
    element.appendChild(input);

    // Focus and select all text
    input.focus();
    input.select();

    // Track if we've already processed the edit (to prevent double-save)
    let editProcessed = false;

    function saveEdit() {
        if (editProcessed) return;
        editProcessed = true;

        const newName = input.value.trim();
        element.textContent = newName || originalText;

        // Update onclick to use new name
        if (newName && newName !== currentName) {
            element.setAttribute('onclick', `editShotName(this, '${newName}')`);
            renameShot(currentName, newName);
        }
    }

    function cancelEdit() {
        if (editProcessed) return;
        editProcessed = true;
        element.textContent = originalText;
    }

    // Handle Enter and Escape keys
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveEdit();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelEdit();
        }
    });

    // Save on blur (clicking outside)
    input.addEventListener('blur', () => {
        // Small delay to allow keydown handlers to fire first
        setTimeout(() => {
            if (!editProcessed) {
                saveEdit();
            }
        }, 0);
    });
}

async function renameShot(oldName, newName) {
    try {
        const response = await fetch('/api/shots/rename', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_name: oldName, new_name: newName })
        });
        const result = await response.json();
        if (result.success) {
            showNotification(`Renamed to ${newName}`);
            loadShots(`shot-row-${newName}`);
        } else {
            showNotification(result.error || 'Rename failed', 'error');
        }
    } catch (error) {
        console.error('Rename failed:', error);
        showNotification('Rename failed', 'error');
    }
}

async function revealFile(relPath, shotName, assetType) {
            try {
                const response = await fetch('/api/shots/reveal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        path: relPath,
                        shot_name: shotName,
                        asset_type: assetType
                    })
                });
                const result = await response.json();
                if (!result.success) {
                    showNotification(result.error || 'Failed to reveal file', 'error');
                }
            } catch (e) {
                console.error("Reveal failed:", e);
                showNotification('Reveal failed', 'error');
    }
}

async function fetchPrompt(shotName, assetType, version) {
    try {
        const resp = await fetch(`/api/shots/prompt?shot_name=${encodeURIComponent(shotName)}&asset_type=${assetType}&version=${version}`);
        const data = await resp.json();
        if (data.success) {
            return data.data || '';
        }
    } catch (e) {
        console.error('Failed to load prompt:', e);
    }
    return '';
}

function buildVersionDropdown(versions, currentVersion) {
    const btn = document.getElementById('version-dropdown-btn');
    const menu = document.getElementById('version-dropdown-menu');
    menu.innerHTML = '';
    versions.sort((a, b) => b - a); // descending
    versions.forEach(v => {
        const item = document.createElement('div');
        item.className = 'dropdown-item';
        item.dataset.version = v;
        item.textContent = `v${String(v).padStart(3, '0')}`;
        item.onclick = () => selectPromptVersion(v);
        menu.appendChild(item);
    });
    btn.textContent = `v${String(currentVersion).padStart(3, '0')} \u25BE`;
}

function toggleVersionDropdown() {
    const menu = document.getElementById('version-dropdown-menu');
    menu.classList.toggle('show');
}

async function selectPromptVersion(v) {
    const modal = document.getElementById('prompt-modal');
    const shotName = modal.dataset.shot;
    const assetType = modal.dataset.type;
    const prevVersion = parseInt(modal.dataset.version, 10);
    if (prevVersion && prevVersion !== v) {
        const prevPromptText = document.getElementById('prompt-text').value;
        try {
            await fetch('/api/shots/prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shot_name: shotName,
                    asset_type: assetType,
                    version: prevVersion,
                    prompt: prevPromptText
                })
            });
        } catch (e) {
            console.error('Auto-save failed:', e);
        }
    }
    modal.dataset.version = v;
    const versions = JSON.parse(modal.dataset.versions || '[]');
    buildVersionDropdown(versions, v);
    let prompt = await fetchPrompt(shotName, assetType, v);

    const copyBtn = document.getElementById('copy-prompt-btn');
    copyBtn.style.display = 'none';
    modal.dataset.prevPrompt = '';

    if (!prompt && v === parseInt(modal.dataset.assetVersion, 10)) {
        const prevPrompt = await fetchPrompt(shotName, assetType, v - 1);
        if (prevPrompt) {
            modal.dataset.prevPrompt = prevPrompt;
            copyBtn.style.display = 'inline-block';
        }
    }
    document.getElementById('prompt-text').value = prompt;
    toggleVersionDropdown();
}

async function openPromptModal(shotName, assetType, version) {
    const modal = document.getElementById('prompt-modal');
    modal.dataset.shot = shotName;
    modal.dataset.type = assetType;

    const typeLabel = assetType.charAt(0).toUpperCase() + assetType.slice(1);
    document.getElementById('prompt-modal-title').textContent = `${shotName} ${typeLabel} Prompt`;
    const versions = Array.from({ length: version }, (_, i) => i + 1);
    modal.dataset.versions = JSON.stringify(versions);
    modal.dataset.assetVersion = version;
    buildVersionDropdown(versions, version);

    let prompt = await fetchPrompt(shotName, assetType, version);
    const copyBtn = document.getElementById('copy-prompt-btn');
    copyBtn.style.display = 'none';
    modal.dataset.prevPrompt = '';

    if (!prompt && version > 1) {
        const prevPrompt = await fetchPrompt(shotName, assetType, version - 1);
        if (prevPrompt) {
            modal.dataset.prevPrompt = prevPrompt;
            copyBtn.style.display = 'inline-block';
        }
    }
    modal.dataset.version = version;
    document.getElementById('prompt-text').value = prompt;

    modal.style.display = 'flex';
    requestAnimationFrame(() => {
        modal.classList.add('show');
    });
    document.getElementById('prompt-text').focus();
}

function closePromptModal() {
    const modal = document.getElementById('prompt-modal');
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 200);
}
function copyToNewPromptVersion() {
    const modal = document.getElementById('prompt-modal');
    const prevPrompt = modal.dataset.prevPrompt || '';
    if (prevPrompt) {
        document.getElementById('prompt-text').value = prevPrompt;
    }
    document.getElementById('copy-prompt-btn').style.display = 'none';
}

async function savePrompt() {
    const modal = document.getElementById('prompt-modal');
    const shotName = modal.dataset.shot;
    const assetType = modal.dataset.type;
    const version = modal.dataset.version;
    const promptText = document.getElementById('prompt-text').value;
    try {
        const response = await fetch('/api/shots/prompt', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ shot_name: shotName, asset_type: assetType, version: parseInt(version, 10), prompt: promptText })
        });
        const result = await response.json();
        if (!result.success) {
            showNotification(result.error || 'Failed to save prompt', 'error');
        } else {
            const shot = shots.find(s => s.name === shotName);
            if (shot) {
                if (assetType === 'image' || assetType === 'video') {
                    shot[assetType].prompt = promptText;
                } else if (shot.lipsync && shot.lipsync[assetType]) {
                    shot.lipsync[assetType].prompt = promptText;
                }
            }
        }
    } catch (e) {
        console.error('Error saving prompt:', e);
        showNotification('Error saving prompt', 'error');
    }
    closePromptModal();
}

async function openShotsFolder() {
    if (!currentProject) {
        showNotification('No project open', 'error');
        return;
    }
    try {
        const response = await fetch('/api/shots/open-folder', {
            method: 'POST'
        });
        const result = await response.json();
        if (!result.success) {
            showNotification(result.error || 'Failed to open folder', 'error');
        }
    } catch (e) {
        console.error('Open folder failed:', e);
        showNotification('Failed to open folder', 'error');
    }
}

function showShotLimitModal() {
    const modal = document.getElementById('shot-limit-modal');
    modal.style.display = 'flex';
    requestAnimationFrame(() => {
        modal.classList.add('show');
    });
}

function closeShotLimitModal() {
    const modal = document.getElementById('shot-limit-modal');
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 200);
}

// Settings Modal Functions
let currentSettings = {
    thumbnail_click_behavior: 'version_folder'
};
let _settingsResolve;
const settingsReady = new Promise(resolve => { _settingsResolve = resolve; });

async function loadSettings() {
    try {
        const response = await fetch('/api/settings/');
        const result = await response.json();
        if (result.success && result.settings) {
            currentSettings = result.settings;
            // Validate theme against known values, fallback to default
            const validThemes = ['default', 'cinema-gold', 'midnight-blue', 'coral-sunset', 'ocean-depths'];
            if (!validThemes.includes(currentSettings.color_theme)) {
                currentSettings.color_theme = 'default';
            }
            // Apply saved theme and mode
            applyTheme(currentSettings.color_theme);
            applyMode(currentSettings.color_mode || 'dark');
            // Apply column visibility
            applyGridTemplate();
            renderGridHeader();
        }
    } catch (e) {
        console.error('Failed to load settings:', e);
    } finally {
        _settingsResolve();
    }
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
}

function previewTheme(theme) {
    applyTheme(theme);
}

function applyMode(mode) {
    document.documentElement.setAttribute('data-mode', mode);
    const toggle = document.getElementById('mode-toggle');
    if (toggle) {
        toggle.querySelector('.mode-icon-dark').style.display = mode === 'dark' ? 'none' : '';
        toggle.querySelector('.mode-icon-light').style.display = mode === 'dark' ? '' : 'none';
    }
}

function toggleColorMode() {
    const current = document.documentElement.getAttribute('data-mode') || 'dark';
    const newMode = current === 'dark' ? 'light' : 'dark';
    applyMode(newMode);
    currentSettings.color_mode = newMode;
    fetch('/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ color_mode: newMode })
    });
}

function initThemeSwatches() {
    const grid = document.getElementById('theme-swatch-grid');
    if (!grid) return;
    grid.addEventListener('click', function(e) {
        const swatch = e.target.closest('.theme-swatch');
        if (!swatch) return;
        grid.querySelectorAll('.theme-swatch').forEach(s => s.classList.remove('active'));
        swatch.classList.add('active');
        previewTheme(swatch.dataset.theme);
    });
}

async function openSettingsModal() {
    await loadSettings();

    const thumbnailDropdown = document.getElementById('thumbnail-click-behavior');
    thumbnailDropdown.value = currentSettings.thumbnail_click_behavior || 'version_folder';

    // Set active theme swatch
    const activeTheme = currentSettings.color_theme || 'default';
    const grid = document.getElementById('theme-swatch-grid');
    grid.querySelectorAll('.theme-swatch').forEach(s => {
        s.classList.toggle('active', s.dataset.theme === activeTheme);
    });

    const namingInput = document.getElementById('file-naming-pattern');
    namingInput.value = currentSettings.file_naming_pattern || '{shot}';
    updateNamingPreview();

    fetchVersion();

    const modal = document.getElementById('settings-modal');
    modal.style.display = 'flex';
    requestAnimationFrame(() => {
        modal.classList.add('show');
    });
}

function closeSettingsModal() {
    // Revert to saved theme if cancelled
    applyTheme(currentSettings.color_theme || 'default');

    const modal = document.getElementById('settings-modal');
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 200);
}

async function fetchVersion() {
    const el = document.getElementById('app-version');
    try {
        const res = await fetch('/api/settings/version');
        const data = await res.json();
        el.textContent = data.success ? `${data.commit} (${data.date})` : 'unknown';
    } catch {
        el.textContent = 'unknown';
    }
}

function copyVersion() {
    const text = document.getElementById('app-version').textContent;
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Version copied to clipboard', 'success');
    });
}

function insertNamingVar(varName) {
    const input = document.getElementById('file-naming-pattern');
    const start = input.selectionStart;
    const end = input.selectionEnd;
    const value = input.value;
    input.value = value.substring(0, start) + varName + value.substring(end);
    input.selectionStart = input.selectionEnd = start + varName.length;
    input.focus();
    updateNamingPreview();
}

function updateNamingPreview() {
    const input = document.getElementById('file-naming-pattern');
    const preview = document.getElementById('naming-preview');
    const pattern = input.value.trim() || '{shot}';
    const projectName = currentProject ? currentProject.name : 'ProjectName';
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const resolved = pattern
        .replace(/\{project\}/g, projectName)
        .replace(/\{shot\}/g, 'SH010')
        .replace(/\{date\}/g, today);
    preview.textContent = 'Preview: ' + resolved + '_v001.jpg';
}

function _getNamingPatternFromInput() {
    const input = document.getElementById('file-naming-pattern');
    const pattern = input.value.trim() || '{shot}';
    if (!pattern.includes('{shot}')) {
        showNotification('Naming pattern must include {shot}', 'error');
        return null;
    }
    return pattern;
}

async function confirmApplyNaming() {
    const pattern = _getNamingPatternFromInput();
    if (!pattern) return;
    try {
        const response = await fetch('/api/settings/rename-files-preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pattern })
        });
        const result = await response.json();
        if (!result.success) {
            showNotification(result.error || 'Failed to check files', 'error');
            return;
        }
        if (result.file_count === 0) {
            showNotification('All files already match this naming pattern', 'info');
            return;
        }
        document.getElementById('rename-file-count').textContent = result.file_count;
        document.getElementById('rename-shot-count').textContent = result.shot_count;
        const modal = document.getElementById('rename-files-modal');
        modal.style.display = 'flex';
        requestAnimationFrame(() => modal.classList.add('show'));
    } catch (e) {
        console.error('Failed to preview rename:', e);
        showNotification('Failed to check files', 'error');
    }
}

function closeRenameModal() {
    const modal = document.getElementById('rename-files-modal');
    modal.classList.remove('show');
    setTimeout(() => { modal.style.display = 'none'; }, 200);
}

async function executeApplyNaming() {
    const pattern = _getNamingPatternFromInput();
    if (!pattern) return;
    closeRenameModal();
    showNotification('Renaming files...', 'info');
    try {
        const response = await fetch('/api/settings/apply-naming', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pattern })
        });
        const result = await response.json();
        if (result.success) {
            const msg = `Renamed ${result.renamed} files` +
                (result.errors > 0 ? ` (${result.errors} errors)` : '');
            showNotification(msg, result.errors > 0 ? 'warning' : 'success');
            currentSettings.file_naming_pattern = pattern;
            closeSettingsModal();
            if (typeof loadShots === 'function') loadShots();
        } else {
            showNotification(result.error || 'Failed to rename files', 'error');
        }
    } catch (e) {
        console.error('Failed to apply naming:', e);
        showNotification('Failed to rename files', 'error');
    }
}

async function saveSettings() {
    const thumbnailDropdown = document.getElementById('thumbnail-click-behavior');
    const namingInput = document.getElementById('file-naming-pattern');
    const namingPattern = namingInput.value.trim() || '{shot}';

    if (!namingPattern.includes('{shot}')) {
        showNotification('Naming pattern must include {shot}', 'error');
        return;
    }

    const activeSwatch = document.querySelector('.theme-swatch.active');
    const selectedTheme = activeSwatch ? activeSwatch.dataset.theme : 'default';

    const newSettings = {
        thumbnail_click_behavior: thumbnailDropdown.value,
        color_theme: selectedTheme,
        color_mode: currentSettings.color_mode || 'dark',
        file_naming_pattern: namingPattern
    };

    try {
        const response = await fetch('/api/settings/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newSettings)
        });
        const result = await response.json();

        if (result.success) {
            // Merge new settings with server response to ensure color_theme persists
            currentSettings = { ...result.settings, ...newSettings };
            showNotification('Settings saved successfully', 'success');
            closeSettingsModal();
        } else {
            showNotification(result.error || 'Failed to save settings', 'error');
        }
    } catch (e) {
        console.error('Failed to save settings:', e);
        showNotification('Failed to save settings', 'error');
    }
}

window.refreshThumbnails = async function() {
    if (!confirm('This will regenerate all thumbnails for the current project. This may take a while. Continue?')) {
        return;
    }

    closeSettingsModal();
    showNotification('Refreshing thumbnails...', 'info');

    try {
        const response = await fetch('/api/shots/refresh-thumbnails', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
            // Reload shots to show new thumbnails
            loadShots();
        } else {
            showNotification(result.error || 'Failed to refresh thumbnails', 'error');
        }
    } catch (e) {
        console.error('Failed to refresh thumbnails:', e);
        showNotification('Failed to refresh thumbnails', 'error');
    }
};

// ===== SHOT ROW VERSION DROPDOWN =====

function toggleShotVersionDropdown(event, badgeElement) {
    event.stopPropagation();

    const container = badgeElement.parentElement;
    const menu = container.querySelector('.version-dropdown-menu');

    // Close all other open dropdowns first
    document.querySelectorAll('.version-dropdown-menu.show').forEach(m => {
        if (m !== menu) m.classList.remove('show');
    });

    menu.classList.toggle('show');
}

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
    if (!e.target.closest('.version-dropdown-container')) {
        document.querySelectorAll('.version-dropdown-menu.show').forEach(m => {
            m.classList.remove('show');
        });
    }
});

async function selectVersion(event, shotName, assetType, selectedVersion) {
    event.stopPropagation();

    const dropdownItem = event.target.closest('.version-dropdown-item');
    const container = dropdownItem.closest('.version-dropdown-container');
    const badge = container.querySelector('.version-badge');
    const menu = container.querySelector('.version-dropdown-menu');
    const filePreview = container.closest('.file-preview');
    const thumbnail = filePreview.querySelector('.preview-thumbnail');

    // Close the dropdown
    menu.classList.remove('show');

    // Update badge immediately
    badge.textContent = `v${String(selectedVersion).padStart(3, '0')}`;

    // Update dropdown item styles
    menu.querySelectorAll('.version-dropdown-item').forEach(item => {
        item.classList.remove('current');
    });
    dropdownItem.classList.add('current');

    // Clear thumbnail immediately to show it's loading
    thumbnail.style.backgroundImage = 'none';

    try {
        const response = await fetch('/api/shots/restore-version', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                shot_name: shotName,
                asset_type: assetType,
                version: selectedVersion
            })
        });

        const result = await response.json();

        if (result.success) {
            // Force reload thumbnail with cache-busting
            if (result.thumbnail) {
                const img = new Image();
                img.onload = () => {
                    thumbnail.style.backgroundImage = `url('${result.thumbnail}?t=${Date.now()}')`;
                };
                img.src = `${result.thumbnail}?t=${Date.now()}`;
            }

            // For videos, update the preview source with cache buster
            if (assetType === 'video' && result.file_path) {
                thumbnail.dataset.videoSrc = result.file_path;
                thumbnail.dataset.videoCacheBuster = Date.now();

                // If video preview is currently playing, refresh it
                const existingPreview = thumbnail.querySelector('.video-preview-container');
                if (existingPreview) {
                    hideVideoPreview(thumbnail);
                    showVideoPreview(thumbnail);
                }
            }

            showNotification(`Restored v${String(selectedVersion).padStart(3, '0')} to Latest folder`);
        } else {
            showNotification(result.error || 'Failed to restore version', 'error');
        }
    } catch (error) {
        console.error('Error restoring version:', error);
        showNotification('Error restoring version', 'error');
    }
}

// ===== VIDEO PREVIEW ON HOVER =====

window.showVideoPreview = function(element) {
    const videoSrc = element.dataset.videoSrc;
    if (!videoSrc) return;

    // Create video preview container
    const container = document.createElement('div');
    container.className = 'video-preview-container';

    const video = document.createElement('video');
    video.className = 'video-preview';

    // Add cache buster to force reload after version changes
    const cacheBuster = element.dataset.videoCacheBuster || '';
    const cacheParam = cacheBuster ? `&t=${cacheBuster}` : '';
    video.src = `/api/shots/serve-video?path=${encodeURIComponent(videoSrc)}${cacheParam}`;
    video.muted = true;
    video.loop = true;
    video.playsInline = true;

    container.appendChild(video);
    element.appendChild(container);

    // Start playing when video is ready
    video.play().catch(err => {
        console.warn('Video autoplay failed:', err);
    });
};

window.hideVideoPreview = function(element) {
    const container = element.querySelector('.video-preview-container');
    if (container) {
        const video = container.querySelector('video');
        if (video) {
            video.pause();
            video.src = ''; // Stop loading
        }
        container.remove();
    }
};

// Apply default theme and mode immediately, then load saved settings
applyTheme('default');
applyMode('dark');
loadSettings();
initThemeSwatches();

// Toggle shot collapse/expand
async function toggleShotCollapse(shotName) {
    const row = document.getElementById(`shot-row-${shotName}`);
    if (!row) return;

    const isCurrentlyCollapsed = row.classList.contains('collapsed');

    if (isCurrentlyCollapsed) {
        // Expanding: add expanding class, remove collapsed, then clean up after animation
        row.classList.add('expanding');
        row.classList.remove('collapsed');

        // Remove expanding class after animation completes (0.2s fade delay + 0.5s animation)
        setTimeout(() => {
            row.classList.remove('expanding');
        }, 700);
    } else {
        // Collapsing: animate with collapsing class, then swap to static collapsed state
        row.classList.add('collapsing');
        setTimeout(() => {
            row.classList.remove('collapsing');
            row.classList.add('collapsed');
        }, 700);
    }

    // Update the collapsed_shots array
    if (!currentSettings.collapsed_shots) {
        currentSettings.collapsed_shots = [];
    }

    if (isCurrentlyCollapsed) {
        // Remove from collapsed list
        currentSettings.collapsed_shots = currentSettings.collapsed_shots.filter(name => name !== shotName);
    } else {
        // Add to collapsed list
        if (!currentSettings.collapsed_shots.includes(shotName)) {
            currentSettings.collapsed_shots.push(shotName);
        }
    }

    // Save to backend
    try {
        const response = await fetch('/api/settings/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ collapsed_shots: currentSettings.collapsed_shots })
        });
        const result = await response.json();
        if (result.success) {
            currentSettings = result.settings;
        }
    } catch (e) {
        console.error('Failed to save collapsed state:', e);
    }
}

// Allow clicking on collapsed row to expand it
document.addEventListener('click', function(e) {
    const collapsedRow = e.target.closest('.shot-row.collapsed');
    if (collapsedRow && !e.target.closest('.collapse-button')) {
        const shotName = collapsedRow.id.replace('shot-row-', '');
        toggleShotCollapse(shotName);
    }
});

// Sidebar toggle functionality
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    const container = document.querySelector('.container');

    sidebar.classList.toggle('open');
    toggleBtn.classList.toggle('open');
    container.classList.toggle('sidebar-open');
}

// Reference Images Functionality
let referenceImages = [];

async function loadReferenceImages() {
    try {
        const response = await fetch('/api/reference/');
        const result = await response.json();

        if (result.success) {
            referenceImages = result.data;
            renderReferenceImages();
        } else {
            console.error('Failed to load reference images:', result.error);
        }
    } catch (error) {
        console.error('Error loading reference images:', error);
    }
}

function renderReferenceImages() {
    const grid = document.getElementById('ref-images-grid');
    grid.innerHTML = '';

    // Render existing images
    referenceImages.forEach(img => {
        const item = createReferenceImageElement(img);
        grid.appendChild(item);
    });

    // Add the empty drop zone at the end
    const emptyZone = document.createElement('div');
    emptyZone.className = 'ref-image-item ref-drop-zone empty';
    emptyZone.ondragover = handleRefDragOver;
    emptyZone.ondrop = handleRefDrop;
    emptyZone.ondragleave = handleRefDragLeave;
    emptyZone.onclick = openRefImageDialog;
    emptyZone.innerHTML = `
        <div class="ref-drop-placeholder">
            <div class="ref-drop-text">+ Add Image</div>
        </div>
    `;
    grid.appendChild(emptyZone);
}

function createReferenceImageElement(img) {
    const item = document.createElement('div');
    item.className = 'ref-image-item';

    const truncatedName = img.filename.length > 50
        ? img.filename.substring(0, 50) + '...'
        : img.filename;

    // Use thumbnail URL if available, otherwise fall back to full image
    const imageUrl = img.thumbnail
        ? `${img.thumbnail}?v=${Date.now()}`
        : `/api/reference/image/${encodeURIComponent(img.filename)}?v=${Date.now()}`;

    // Escape single quotes in filename for onclick attribute
    const escapedFilename = img.filename.replace(/'/g, "\\'");

    item.innerHTML = `
        <div class="ref-drop-zone">
            <img src="${imageUrl}"
                 class="ref-image-preview"
                 alt="${img.filename}"
                 title="${img.filename}"
                 onclick="revealRefImage('${escapedFilename}')">
        </div>
        <div class="ref-image-filename"
             onclick="editRefImageName('${escapedFilename}')"
             title="${img.filename}">
            ${truncatedName}
        </div>
    `;

    return item;
}

function handleRefDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
}

function handleRefDragLeave(event) {
    event.currentTarget.classList.remove('drag-over');
}

async function handleRefDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');

    const files = event.dataTransfer.files;
    if (files.length === 0) {
        showNotification('No files dropped', 'error');
        return;
    }

    const file = files[0];
    const ext = file.name.toLowerCase().split('.').pop();

    if (!['jpg', 'jpeg', 'png'].includes(ext)) {
        showNotification('Only JPG and PNG images are allowed', 'error');
        return;
    }

    await uploadReferenceImage(file);
}

function openRefImageDialog() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/jpeg,image/jpg,image/png';
    input.style.display = 'none';
    input.addEventListener('change', () => {
        if (input.files && input.files[0]) {
            uploadReferenceImage(input.files[0]);
        }
        input.remove();
    });
    document.body.appendChild(input);
    input.click();
}

async function uploadReferenceImage(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        showNotification('Uploading reference image...');

        const response = await fetch('/api/reference/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showNotification(`${file.name} uploaded successfully!`);
            loadReferenceImages();
        } else {
            showNotification(result.error || 'Upload failed', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showNotification('Upload failed', 'error');
    }
}

function editRefImageName(currentName) {
    // Get the extension
    const lastDotIndex = currentName.lastIndexOf('.');
    const extension = lastDotIndex !== -1 ? currentName.substring(lastDotIndex) : '';
    const nameWithoutExt = lastDotIndex !== -1 ? currentName.substring(0, lastDotIndex) : currentName;

    // Prompt for new name without extension
    const newNameWithoutExt = prompt('Enter new filename', nameWithoutExt);
    if (!newNameWithoutExt || newNameWithoutExt === nameWithoutExt) {
        return;
    }

    // Add extension back
    const newName = newNameWithoutExt + extension;
    renameReferenceImage(currentName, newName);
}

async function renameReferenceImage(oldName, newName) {
    try {
        const response = await fetch('/api/reference/rename', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_name: oldName, new_name: newName })
        });

        const result = await response.json();

        if (result.success) {
            showNotification(`Renamed to ${newName}`);
            loadReferenceImages();
        } else {
            showNotification(result.error || 'Rename failed', 'error');
        }
    } catch (error) {
        console.error('Rename failed:', error);
        showNotification('Rename failed', 'error');
    }
}

async function revealRefImage(filename) {
    try {
        const response = await fetch('/api/reference/reveal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });

        const result = await response.json();

        if (!result.success) {
            showNotification(result.error || 'Failed to reveal file', 'error');
        }
    } catch (error) {
        console.error('Reveal failed:', error);
        showNotification('Failed to reveal file', 'error');
    }
}

// ===== LAZY THUMBNAIL LOADING =====

// Track if batch loading is in progress
let batchLoadingInProgress = false;

async function loadAllMissingThumbnails() {
    // Collect all thumbnails that need loading
    const lazyThumbs = document.querySelectorAll('[data-lazy-thumb="true"]');

    if (lazyThumbs.length === 0 || batchLoadingInProgress) {
        return;
    }

    batchLoadingInProgress = true;

    // Build batch request
    const items = [];
    const elementMap = new Map(); // key -> element

    lazyThumbs.forEach(el => {
        const shotName = el.dataset.shot;
        const assetType = el.dataset.assetType;
        const key = `${shotName}-${assetType}`;

        items.push({ shot_name: shotName, asset_type: assetType });
        elementMap.set(key, el);
    });

    try {
        const response = await fetch('/api/shots/generate-thumbnails-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items })
        });

        const result = await response.json();

        if (result.success && result.thumbnails) {
            // Apply all thumbnails
            for (const [key, thumbnailUrl] of Object.entries(result.thumbnails)) {
                const element = elementMap.get(key);
                if (element && thumbnailUrl) {
                    element.style.backgroundImage = `url('${thumbnailUrl}?v=${Date.now()}')`;
                    element.style.backgroundSize = 'cover';
                    element.style.backgroundPosition = 'center';
                    element.classList.remove('loading');
                    element.removeAttribute('data-lazy-thumb');
                }
            }

            // Remove loading state from any remaining elements (no thumbnail available)
            lazyThumbs.forEach(el => {
                if (el.hasAttribute('data-lazy-thumb')) {
                    el.classList.remove('loading');
                    el.removeAttribute('data-lazy-thumb');
                }
            });
        }
    } catch (error) {
        console.error('Failed to load thumbnails batch:', error);
        // Remove loading state on error
        lazyThumbs.forEach(el => el.classList.remove('loading'));
    } finally {
        batchLoadingInProgress = false;
    }
}

// Call this after rendering shots
function startLazyThumbnailLoading() {
    // Small delay to let the UI render first, then load all thumbnails
    setTimeout(() => loadAllMissingThumbnails(), 50);
}

// ===== ONBOARDING TIPS =====

const ONBOARDING_TIPS = [
    {
        id: 'tip-project',
        text: 'Start by opening an existing project or creating a new one. Enter a folder path and hit Open.',
        target: '#project-toggle',
        placement: 'bottom',
        condition: () => !currentProject,
    },
    {
        id: 'tip-create-shot',
        text: 'Create your first shot to get started. You can also drag & drop a file anywhere here.',
        target: '.empty-shots-state .btn-primary',
        placement: 'bottom',
        condition: () => currentProject && shots.length === 0,
    },
    {
        id: 'tip-upload-asset',
        text: 'Drag an image or video onto these areas, or click to browse. Each shot has an image and video slot.',
        target: '.shot-row .drop-zone.empty',
        placement: 'bottom',
        condition: () => shots.length > 0 && document.querySelector('.shot-row .drop-zone.empty'),
    },
    {
        id: 'tip-notes',
        text: 'Add production notes for each shot. Notes are saved automatically when you click away.',
        target: '.shot-row .notes-input',
        placement: 'left',
        condition: () => shots.length > 0 && document.querySelector('.shot-row .notes-input'),
    },
    {
        id: 'tip-locate',
        text: 'Click any thumbnail to open the file in your file browser.',
        target: '.preview-thumbnail',
        placement: 'bottom',
        condition: () => document.querySelector('.preview-thumbnail'),
    },
    {
        id: 'tip-insert-between',
        text: 'Hover below or above shots to reveal the + button. Click it to insert a new shot at that position.',
        target: '.drop-between-zone',
        placement: 'bottom',
        condition: () => shots.length >= 1 && document.querySelector('.drop-between-zone'),
    },
    {
        id: 'tip-prompt',
        text: 'Click the P button on any asset to write or view prompts for that asset.',
        target: '.prompt-button',
        placement: 'top',
        condition: () => document.querySelector('.prompt-button'),
    },
    {
        id: 'tip-reference',
        text: 'Open the reference panel to pin inspiration images. Drag images here or click + Add Image.',
        target: '#sidebar-toggle',
        placement: 'left',
        condition: () => currentProject !== null,
    },
];

const ONBOARDING_STORAGE_KEY = 'shotbuddy_onboarding';

function getOnboardingState() {
    try {
        const stored = localStorage.getItem(ONBOARDING_STORAGE_KEY);
        return stored ? JSON.parse(stored) : null;
    } catch (e) {
        return null;
    }
}

function activateOnboarding() {
    if (!getOnboardingState()) {
        saveOnboardingState({ activated: true, dismissed: [] });
    }
}

function deactivateOnboarding() {
    if (!getOnboardingState()) {
        saveOnboardingState({ activated: false, dismissed: [] });
    }
}

function saveOnboardingState(state) {
    try {
        localStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
        console.warn('Could not save onboarding state:', e);
    }
}

function getNextTip() {
    const state = getOnboardingState();
    if (!state || !state.activated) return null;
    for (const tip of ONBOARDING_TIPS) {
        if (state.dismissed.includes(tip.id)) continue;
        if (tip.condition && !tip.condition()) continue;
        const targetEl = document.querySelector(tip.target);
        if (!targetEl) continue;
        if (targetEl.offsetParent === null && getComputedStyle(targetEl).position !== 'fixed') continue;
        return tip;
    }
    return null;
}

function showOnboardingTip(tip) {
    const tipEl = document.getElementById('onboarding-tip');
    const textEl = document.getElementById('onboarding-tip-text');
    const stepEl = document.getElementById('onboarding-tip-step');
    const targetEl = document.querySelector(tip.target);

    if (!tipEl || !textEl || !targetEl) return;

    // Remove previous highlight
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
        el.classList.remove('onboarding-highlight');
    });

    // Set content
    textEl.textContent = tip.text;

    // Store current tip id
    tipEl.dataset.tipId = tip.id;
    tipEl.dataset.placement = tip.placement;

    // Add highlight to target
    targetEl.classList.add('onboarding-highlight');

    // Position the tip
    tipEl.style.display = 'block';
    positionTip(tipEl, targetEl, tip.placement);

    // Show with animation
    requestAnimationFrame(() => {
        tipEl.classList.add('show');
    });
}

function positionTip(tipEl, targetEl, placement) {
    const rect = targetEl.getBoundingClientRect();
    const tipWidth = 280;
    const tipHeight = tipEl.offsetHeight;
    const gap = 12;
    const arrowOffsetH = 24; // arrow's left offset for top/bottom placements
    const arrowOffsetV = 16; // arrow's top offset for left/right placements
    const targetCenterX = rect.left + rect.width / 2;
    const targetCenterY = rect.top + rect.height / 2;

    let top, left;

    switch (placement) {
        case 'bottom':
            top = rect.bottom + gap;
            left = targetCenterX - arrowOffsetH - 6; // center arrow (6 = half of 12px arrow)
            break;
        case 'top':
            top = rect.top - gap - tipHeight;
            left = targetCenterX - arrowOffsetH - 6;
            break;
        case 'left':
            top = targetCenterY - arrowOffsetV - 6;
            left = rect.left - tipWidth - gap;
            break;
        case 'right':
            top = targetCenterY - arrowOffsetV - 6;
            left = rect.right + gap;
            break;
    }

    // Clamp to viewport
    left = Math.max(12, Math.min(left, window.innerWidth - tipWidth - 12));
    top = Math.max(12, top);

    tipEl.style.top = top + 'px';
    tipEl.style.left = left + 'px';
}

function dismissOnboardingTip() {
    const tipEl = document.getElementById('onboarding-tip');
    if (!tipEl) return;

    const tipId = tipEl.dataset.tipId;

    // Hide with animation
    tipEl.classList.remove('show');
    setTimeout(() => {
        tipEl.style.display = 'none';
    }, 300);

    // Remove highlight
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
        el.classList.remove('onboarding-highlight');
    });

    // Save dismissed state
    if (tipId) {
        const state = getOnboardingState();
        if (!state.dismissed.includes(tipId)) {
            state.dismissed.push(tipId);
            saveOnboardingState(state);
        }
    }

    // Auto-advance to next tip
    setTimeout(() => {
        checkOnboardingTips();
    }, 800);
}

function skipAllOnboardingTips() {
    const tipEl = document.getElementById('onboarding-tip');

    // Mark all tips as dismissed
    const state = { activated: true, dismissed: ONBOARDING_TIPS.map(t => t.id) };
    saveOnboardingState(state);

    // Hide current tip
    if (tipEl) {
        tipEl.classList.remove('show');
        setTimeout(() => {
            tipEl.style.display = 'none';
        }, 300);
    }

    // Remove highlights
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
        el.classList.remove('onboarding-highlight');
    });
}

function hideOnboardingTip() {
    const tipEl = document.getElementById('onboarding-tip');
    if (!tipEl) return;
    tipEl.classList.remove('show');
    setTimeout(() => {
        tipEl.style.display = 'none';
    }, 300);
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
        el.classList.remove('onboarding-highlight');
    });
}

function checkOnboardingTips() {
    const tip = getNextTip();
    if (tip) {
        showOnboardingTip(tip);
    } else {
        hideOnboardingTip();
    }
}

function resetOnboarding() {
    saveOnboardingState({ activated: true, dismissed: [] });
    showNotification('Quick-start tips reset. They will appear as you use the app.');
    closeSettingsModal();
    setTimeout(() => checkOnboardingTips(), 500);
}

// Reposition on resize/scroll
let onboardingRepositionTimer = null;

function repositionActiveTip() {
    const tipEl = document.getElementById('onboarding-tip');
    if (!tipEl || tipEl.style.display === 'none') return;

    const tipId = tipEl.dataset.tipId;
    const tip = ONBOARDING_TIPS.find(t => t.id === tipId);
    if (!tip) return;

    const targetEl = document.querySelector(tip.target);
    if (!targetEl || targetEl.offsetParent === null) {
        hideOnboardingTip();
        return;
    }

    positionTip(tipEl, targetEl, tip.placement);
}

window.addEventListener('resize', () => {
    clearTimeout(onboardingRepositionTimer);
    onboardingRepositionTimer = setTimeout(repositionActiveTip, 100);
});

window.addEventListener('scroll', () => {
    clearTimeout(onboardingRepositionTimer);
    onboardingRepositionTimer = setTimeout(repositionActiveTip, 50);
}, { passive: true });

