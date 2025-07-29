# project_manager.py

from pathlib import Path
import json
from datetime import datetime
import logging
from app.config.constants import PROJECTS_FILE

logger = logging.getLogger(__name__)

class ProjectManager:
    def __init__(self):
        self.projects_file = Path(PROJECTS_FILE).resolve()
        self.projects = {
            'current_project': None,
            'recent_projects': []
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
        from app.utils import sanitize_path
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
        from app.utils import sanitize_path
        path = sanitize_path(path).resolve()
        path_str = str(path)
        self.projects['current_project'] = path_str
        if path_str not in self.projects['recent_projects']:
            self.projects['recent_projects'].insert(0, path_str)
            self.projects['recent_projects'] = self.projects['recent_projects'][:5]
        self.save_projects()

    def get_current_project(self):
        project_path = self.projects.get('current_project')
        if not project_path:
            logger.warning("No current project path set.")
            return None
        from app.utils import sanitize_path
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

