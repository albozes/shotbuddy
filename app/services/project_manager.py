# project_manager.py

from datetime import datetime
from pathlib import Path
import json
import logging

from ..config.constants import PROJECTS_FILE

logger = logging.getLogger(__name__)

class ProjectManager:
    def __init__(self):
        self.projects_file = Path(PROJECTS_FILE).resolve()
        self.projects = {
            'current_project': None,
            'recent_projects': [],
            'last_scanned': {},
            'settings': {
                'thumbnail_click_behavior': 'latest_folder',  # 'latest_folder' or 'version_folder'
                'color_theme': 'default',
                'color_mode': 'dark',  # 'dark' or 'light'
                'file_naming_pattern': '{shot}'  # Template for file naming
            }
        }
        self.ensure_config_dir()
        self.load_projects()

    def ensure_config_dir(self):
        config_dir = self.projects_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)

    def load_projects(self):
        if self.projects_file.exists():
            try:
                with self.projects_file.open('r') as f:
                    self.projects = json.load(f)
                    if self.projects.get('current_project'):
                        self.projects['current_project'] = str(Path(self.projects['current_project']).resolve())
                    self.projects['recent_projects'] = [
                        str(Path(p).resolve()) for p in self.projects.get('recent_projects', [])
                    ]
                    loaded_scanned = self.projects.get('last_scanned', {})
                    self.projects['last_scanned'] = {
                        str(Path(p).resolve()): ts for p, ts in loaded_scanned.items()
                    }
                    # Ensure settings exist with defaults
                    if 'settings' not in self.projects:
                        self.projects['settings'] = {}
                    if 'thumbnail_click_behavior' not in self.projects['settings']:
                        self.projects['settings']['thumbnail_click_behavior'] = 'latest_folder'
                    if 'color_theme' not in self.projects['settings']:
                        self.projects['settings']['color_theme'] = 'default'
                    if 'color_mode' not in self.projects['settings']:
                        self.projects['settings']['color_mode'] = 'dark'
                    if 'file_naming_pattern' not in self.projects['settings']:
                        self.projects['settings']['file_naming_pattern'] = '{shot}'
            except Exception as e:
                logger.warning("Failed to load projects.json: %s", e)
        logger.info("Loaded current project: %s", self.projects.get('current_project'))

    def save_projects(self):
        try:
            with self.projects_file.open('w') as f:
                json.dump(self.projects, f, indent=2)
            logger.info("Saved current project: %s", self.projects.get('current_project'))
        except Exception as e:
            logger.warning("Failed to save projects.json: %s", e)

    def create_project(self, project_path, project_name):
        from ..utils import sanitize_path
        project_dir = sanitize_path(project_path).resolve() / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        shots_dir = project_dir / 'shots'
        shots_dir.mkdir(exist_ok=True)
        (shots_dir / 'wip').mkdir(parents=True, exist_ok=True)
        (shots_dir / 'latest_images').mkdir(exist_ok=True)
        (shots_dir / 'latest_videos').mkdir(exist_ok=True)
        (project_dir / '_legacy').mkdir(exist_ok=True)

        resolved_dir = project_dir.resolve()
        project_info = {
            'name': project_name,
            'path': str(resolved_dir),
            'created': datetime.now().isoformat(),
            'shots': []
        }

        self.set_current_project(project_dir)
        return project_info

    def set_current_project(self, path: Path):
        from ..utils import sanitize_path
        path = sanitize_path(path).resolve()
        path_str = str(path)
        self.projects['current_project'] = path_str
        if path_str not in self.projects['recent_projects']:
            self.projects['recent_projects'].insert(0, path_str)
            self.projects['recent_projects'] = self.projects['recent_projects'][:5]
        self.save_projects()

    def clear_current_project(self):
        self.projects['current_project'] = None
        self.save_projects()

    def get_current_project(self):
        project_path = self.projects.get('current_project')
        if not project_path:
            logger.warning("No current project path set.")
            return None
        from ..utils import sanitize_path
        project_path = sanitize_path(project_path).resolve()
        shots_dir = project_path / 'shots'

        if shots_dir.exists():
            created = datetime.fromtimestamp(project_path.stat().st_ctime).isoformat()
            return {
                'name': project_path.name,
                'path': str(project_path),
                'created': created,
                'shots': []
            }

        for recent in self.projects.get('recent_projects', []):
            recent_path = sanitize_path(recent).resolve()
            if (recent_path / 'shots').exists():
                logger.info("Falling back to recent project: %s", recent_path)
                self.set_current_project(recent_path)
                created = datetime.fromtimestamp(recent_path.stat().st_ctime).isoformat()
                return {
                    'name': recent_path.name,
                    'path': str(recent_path),
                    'created': created,
                    'shots': []
                }

        logger.error("No valid project found.")
        return None

    def get_project_settings_file(self):
        """Get path to project-specific settings file."""
        project = self.get_current_project()
        if not project:
            return None
        project_path = Path(project['path'])
        return project_path / '.shotbuddy_settings.json'

    def load_project_settings(self):
        """Load project-specific settings from the project directory."""
        settings_file = self.get_project_settings_file()
        if settings_file and settings_file.exists():
            try:
                with settings_file.open('r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load project settings: %s", e)
        return {}

    def save_project_settings(self, project_settings):
        """Save project-specific settings to the project directory."""
        settings_file = self.get_project_settings_file()
        if settings_file:
            try:
                with settings_file.open('w') as f:
                    json.dump(project_settings, f, indent=2)
                logger.info("Saved project settings to: %s", settings_file)
            except Exception as e:
                logger.warning("Failed to save project settings: %s", e)

    def get_shared_project_file(self):
        """Get path to shared project data file (.shotbuddy_project.json)."""
        project = self.get_current_project()
        if not project:
            return None
        project_path = Path(project['path'])
        return project_path / '.shotbuddy_project.json'

    def load_shared_project_data(self):
        """Load shared project data (artists, shot_artists) from .shotbuddy_project.json."""
        shared_file = self.get_shared_project_file()
        if shared_file and shared_file.exists():
            try:
                with shared_file.open('r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load shared project data: %s", e)

        # Migration: check if artists/shot_artists exist in old settings file
        old_settings = self.load_project_settings()
        migrated = {}
        for key in ('artists', 'shot_artists'):
            if key in old_settings:
                migrated[key] = old_settings.pop(key)
        if migrated:
            self.save_shared_project_data(migrated)
            self.save_project_settings(old_settings)
            logger.info("Migrated artist data from settings to shared project file")
            return migrated

        return {}

    def save_shared_project_data(self, shared_data):
        """Save shared project data to .shotbuddy_project.json."""
        shared_file = self.get_shared_project_file()
        if shared_file:
            try:
                with shared_file.open('w') as f:
                    json.dump(shared_data, f, indent=2)
                logger.info("Saved shared project data to: %s", shared_file)
            except Exception as e:
                logger.warning("Failed to save shared project data: %s", e)

    def get_settings(self):
        """Get user settings (global + project-specific + shared project data)."""
        global_settings = self.projects.get('settings', {
            'thumbnail_click_behavior': 'latest_folder',
            'color_theme': 'default',
            'color_mode': 'dark'
        })
        project_settings = self.load_project_settings()
        shared_data = self.load_shared_project_data()

        # Merge global, local project, and shared project settings
        return {
            'thumbnail_click_behavior': global_settings.get('thumbnail_click_behavior', 'latest_folder'),
            'color_theme': global_settings.get('color_theme', 'default'),
            'color_mode': global_settings.get('color_mode', 'dark'),
            'file_naming_pattern': global_settings.get('file_naming_pattern', '{shot}'),
            'collapsed_shots': project_settings.get('collapsed_shots', []),
            'visible_columns': project_settings.get('visible_columns', ['image', 'video']),
            'artists': shared_data.get('artists', []),
            'shot_artists': shared_data.get('shot_artists', {})
        }

    def update_settings(self, settings_dict):
        """Update user settings and save (handles global, local project, and shared project settings)."""
        global_settings_keys = ['thumbnail_click_behavior', 'color_theme', 'color_mode', 'file_naming_pattern']
        project_settings_keys = ['collapsed_shots', 'visible_columns']
        shared_project_keys = ['artists', 'shot_artists']

        # Update global settings
        if 'settings' not in self.projects:
            self.projects['settings'] = {}

        for key in global_settings_keys:
            if key in settings_dict:
                self.projects['settings'][key] = settings_dict[key]

        if any(key in settings_dict for key in global_settings_keys):
            self.save_projects()

        # Update local project settings (per-user UI preferences)
        project_settings = self.load_project_settings()
        for key in project_settings_keys:
            if key in settings_dict:
                project_settings[key] = settings_dict[key]

        if any(key in settings_dict for key in project_settings_keys):
            self.save_project_settings(project_settings)

        # Update shared project data (artists, shot_artists)
        shared_data = self.load_shared_project_data()
        for key in shared_project_keys:
            if key in settings_dict:
                shared_data[key] = settings_dict[key]

        if any(key in settings_dict for key in shared_project_keys):
            self.save_shared_project_data(shared_data)

        return self.get_settings()

