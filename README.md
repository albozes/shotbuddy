# Shotbuddy
An application for managing AI-driven image-to-video filmmaking workflows, supporting structured organization, versioning, and annotation of generated stills and videos.

## Project folder layout

Each project contains a `shots` directory with the following structure:

```
shots/
    wip/              # per-shot folders
        SH###/
            images/   # versioned stills
            videos/   # versioned videos
            lipsync/  # lipsync clips (not implemented yet)
    latest_images/    # latest image for each shot
    latest_videos/    # latest video for each shot
```

The application automatically manages the latest versions in `latest_images` and `latest_videos` while keeping all historical versions inside the `wip` shot folders.

## Installation

Follow these steps to get the application running on any operating system. The
only prerequisite is that `git` is already installed on your machine.

1. **Install Python 3** – Download and install the latest version of Python 3
   from [python.org](https://www.python.org/downloads/) or use your operating
   system's package manager.
2. **Clone the repository**

   ```bash
   git clone https://github.com/albozes/shotbuddy.git
   ```
   ```bash
   cd shotbuddy
   ```
3. **Create and activate a virtual environment**

   Windows
   ```bash
   python -m venv venv
   ```
   ```bash
   venv\Scripts\activate
   ```
   Linux/macOS
   ```bash
   python3 -m venv venv
   ```
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
5. **Run the development server**

   ```bash
   python run.py
   ```
6. **Open your browser**

   By default, Shotbuddy will be available at https://127.0.0.1:5001/

## Configuration

Server settings can be defined in the `shotbuddy.cfg` file located in the
repository root. The file uses INI syntax and contains a `[server]` section with
`host` and `port` keys:

```ini
[server]
host = 0.0.0.0
port = 5001
```

Values specified via environment variables override those in `shotbuddy.cfg`.
Available variables are:

- `SHOTBUDDY_UPLOAD_FOLDER` – directory used for temporary uploads (default:
  `uploads`).
- `SHOTBUDDY_HOST` – address the Flask server binds to (default: `127.0.0.1`).
- `SHOTBUDDY_PORT` – port number for the development server (default: `5001`).
- `SHOTBUDDY_DEBUG` – set to `1` to enable Flask debug mode.
