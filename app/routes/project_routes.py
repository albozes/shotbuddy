from datetime import datetime
from pathlib import Path
import logging

from flask import Blueprint, request, jsonify, render_template, current_app

from ..services.shot_manager import get_shot_manager, clear_shot_manager_cache

logger = logging.getLogger(__name__)

project_bp = Blueprint('project', __name__)

@project_bp.route("/")
def index():
    return render_template("index.html")

@project_bp.route("/api/project/current")
def get_current_project():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if project:
            project_path = Path(project["path"])
            path_str = str(project_path)

            # Update last scanned timestamp
            folder_mtime = project_path.stat().st_mtime
            project_manager.projects.setdefault("last_scanned", {})[path_str] = (
                datetime.fromtimestamp(folder_mtime).isoformat()
            )
            project_manager.save_projects()
            return jsonify({"success": True, "data": project})
        return jsonify({"success": False, "error": "No current project"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@project_bp.route("/api/project/recent")
def get_recent_projects():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        recent_projects = []
        for project_path in project_manager.projects.get('recent_projects', []):
            p = Path(project_path)
            shots_dir = p / 'shots'
            if shots_dir.exists():
                created = datetime.fromtimestamp(p.stat().st_ctime).isoformat()
                recent_projects.append({
                    "name": p.name,
                    "path": str(p.resolve()),
                    "created": created,
                    "shots": []
                })
        return jsonify({"success": True, "data": recent_projects})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@project_bp.route("/api/project/open", methods=["POST"])
def open_project():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        data = request.get_json()
        project_path = data.get("path")
        if not project_path:
            return jsonify({"success": False, "error": "Project path required"}), 400
        from ..utils import sanitize_path
        project_path = sanitize_path(project_path).resolve()
        path_str = str(project_path)
        shots_dir = project_path / "shots"

        logger.debug("Received raw path from frontend: %s", request.get_json())
        logger.debug("Looking at path: %s", project_path)
        logger.debug("shots/ folder exists? %s", shots_dir.exists())

        if not shots_dir.exists():
            return jsonify({"success": False, "error": "No recognizable project structure"}), 400

        project_info = {
            "name": project_path.name,
            "path": path_str,
            "created": datetime.fromtimestamp(project_path.stat().st_ctime).isoformat(),
            "shots": []
        }

        # Ensure new folder layout exists
        (shots_dir / "wip").mkdir(parents=True, exist_ok=True)
        (shots_dir / "latest_images").mkdir(exist_ok=True)
        (shots_dir / "latest_videos").mkdir(exist_ok=True)

        # Only clear ShotManager cache when switching to a different project
        previous_project = project_manager.projects.get('current_project')
        if previous_project != path_str:
            clear_shot_manager_cache()

        # Update project manager state
        path_str = str(project_path)
        project_manager.projects['current_project'] = path_str
        if path_str not in project_manager.projects['recent_projects']:
            project_manager.projects['recent_projects'].insert(0, path_str)
            project_manager.projects['recent_projects'] = project_manager.projects['recent_projects'][:5]

        # Update last scanned timestamp
        folder_mtime = project_path.stat().st_mtime
        project_manager.projects.setdefault('last_scanned', {})[path_str] = (
            datetime.fromtimestamp(folder_mtime).isoformat()
        )
        project_manager.save_projects()

        # Sync latest folders to ensure consistency with WIP
        try:
            shot_manager = get_shot_manager(path_str)
            shot_manager.sync_latest_folders()
        except Exception as e:
            logger.warning("Failed to sync latest folders on project open: %s", e)

        return jsonify({"success": True, "data": project_info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_bp.route("/api/project/close", methods=["POST"])
def close_project():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project_manager.clear_current_project()
        clear_shot_manager_cache()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_bp.route("/api/project/create", methods=["POST"])
def create_project():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        data = request.get_json()
        project_name = data.get("name", "Untitled Project")
        selected_folder = data.get("path", ".")
        from ..utils import sanitize_path
        folder_path = sanitize_path(selected_folder).resolve()

        project_dir = folder_path / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        shots_dir = project_dir / "shots"
        shots_dir.mkdir(exist_ok=True)
        (shots_dir / "wip").mkdir(parents=True, exist_ok=True)
        (shots_dir / "latest_images").mkdir(exist_ok=True)
        (shots_dir / "latest_videos").mkdir(exist_ok=True)
        (project_dir / "_legacy").mkdir(exist_ok=True)

        resolved_dir = project_dir.resolve()
        project_info = {
            "name": project_name,
            "path": str(resolved_dir),
            "created": datetime.now().isoformat(),
            "shots": []
        }

        # Defensive state update
        path_str = str(resolved_dir)
        project_manager.projects['current_project'] = path_str
        project_manager.projects['recent_projects'] = [path_str]
        project_manager.save_projects()

        # Clear ShotManager cache for fresh state with the new project
        clear_shot_manager_cache()

        # Verify project was set correctly
        if project_manager.get_current_project() is None:
            logger.error("Project state inconsistency: project not set after creation")
            return jsonify({"success": False, "error": "Failed to set project state"}), 500

        return jsonify({"success": True, "data": project_info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
