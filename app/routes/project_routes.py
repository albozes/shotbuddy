from flask import Blueprint, request, jsonify, render_template, current_app
from pathlib import Path
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from app.services.shot_manager import get_shot_manager, clear_shot_manager_cache
from app.services.file_handler import FileHandler

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
            file_handler = FileHandler(project["path"])
            file_handler.clear_thumbnail_cache()
            clear_shot_manager_cache()
            get_shot_manager(project["path"]).get_shots()
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
            project_file = Path(project_path) / 'project.json'
            if project_file.exists():
                with project_file.open('r') as f:
                    recent_projects.append(json.load(f))
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
        from app.utils import sanitize_path
        project_path = sanitize_path(project_path).resolve()
        path_str = str(project_path)
        project_file = project_path / "project.json"
        shots_dir = project_path / "shots"

        logger.debug("Received raw path from frontend: %s", request.get_json())
        logger.debug("Looking at path: %s", project_path)
        logger.debug("Expecting project.json at: %s", project_file)
        logger.debug("shots/ folder exists? %s", shots_dir.exists())

        if project_file.exists():
            try:
                with project_file.open('r') as f:
                    project_info = json.load(f)
                # Ensure the stored path reflects the actual location
                if project_info.get("path") != path_str:
                    project_info["path"] = path_str
                    with project_file.open('w') as wf:
                        json.dump(project_info, wf, indent=2)
            except Exception as e:
                return jsonify({"success": False, "error": f"project.json exists but failed to load: {e}"}), 400
        elif shots_dir.exists():
            project_info = {
                "name": project_path.name,
                "path": path_str,
                "created": datetime.now().isoformat(),
                "shots": []
            }
            with project_file.open('w') as f:
                json.dump(project_info, f, indent=2)
        else:
            return jsonify({"success": False, "error": "No recognizable project structure"}), 400

        # Ensure new folder layout exists
        (shots_dir / "wip").mkdir(parents=True, exist_ok=True)
        (shots_dir / "latest_images").mkdir(exist_ok=True)
        (shots_dir / "latest_videos").mkdir(exist_ok=True)

        # Update project manager state
        path_str = str(project_path)
        project_manager.projects['current_project'] = path_str
        if path_str not in project_manager.projects['recent_projects']:
            project_manager.projects['recent_projects'].insert(0, path_str)
            project_manager.projects['recent_projects'] = project_manager.projects['recent_projects'][:5]

        project_manager.save_projects()

        # When switching projects, clear cached thumbnails and reset any
        # cached ShotManager instances to ensure thumbnails are regenerated
        # for the current project only.
        file_handler = FileHandler(path_str)
        file_handler.clear_thumbnail_cache()
        clear_shot_manager_cache()

        # Generate fresh thumbnails for the newly opened project
        shot_manager = get_shot_manager(path_str)
        shot_manager.get_shots()

        return jsonify({"success": True, "data": project_info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_bp.route("/api/project/create", methods=["POST"])
def create_project():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        data = request.get_json()
        project_name = data.get("name", "Untitled Project")
        selected_folder = data.get("path", ".")
        from app.utils import sanitize_path
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

        # Write the project file first
        with (project_dir / "project.json").open('w') as f:
            json.dump(project_info, f, indent=2)

        # Defensive state update
        path_str = str(resolved_dir)
        project_manager.projects['current_project'] = path_str
        project_manager.projects['recent_projects'] = [path_str]
        project_manager.save_projects()

        # Optional: sanity check (useful in dev)
        assert project_manager.get_current_project() is not None

        return jsonify({"success": True, "data": project_info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
