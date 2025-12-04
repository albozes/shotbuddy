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
            lipsync/  # lipsync clips (manual storage for lipsync assets)
    latest_images/    # latest image for each shot
    latest_videos/    # latest video for each shot
ref-images/           # reference images
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
   Windows
   ```bash
   python run.py
   ```
   Linux/macOS
   ```bash
   python3 run.py
   ```
7. **Open your browser**

   By default, Shotbuddy will be available at http://127.0.0.1:5001/

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

## Functionality
Shotbuddy has a straightforward interface, similar to existing shotlist applications, but optimized for AI filmmakers.

![SB_001](https://github.com/user-attachments/assets/aa549433-df68-4ea8-b8c4-c3d1e9bd4059)

Create new shots and iterate versions with simple drag and drop. Generated images and videos are automatically copied into a clean folder structure and renamed to the correct shot. New shots can be added before or in-between existing ones, due to the flexible three-digit shot naming convention. Should there be a need for even more (between SH011 and SH012, for example), naming continues with an underscore (e.g. SH011_050). 

![SB_002](https://github.com/user-attachments/assets/27cecc3e-c7bb-4617-90f0-515f8de489d3)
![SB_003](https://github.com/user-attachments/assets/d00cc329-0428-4112-b509-4ba5d052a42b)

Click on an asset's thumbnail and be taken to the folder with all previous versions. You can change this behavior in settings and instead view all the most recent versions of assets in the "latest" folder.

![SB_004](https://github.com/user-attachments/assets/28e8ed6c-676f-47ce-9f9b-83f28fa56569)

Via the "P" button on each asset thumbnail, prompts can be documented. A version history is available via the dropdown on the top right of the window.

![SB_005](https://github.com/user-attachments/assets/dbe8f713-2306-4128-885a-19d9b06b08a4)

Rename shots by clicking on their name. This automatically renames all previous versions and their folder name in the file system.

![SB_006](https://github.com/user-attachments/assets/3522f4df-3bf7-42fb-a6c7-5352e80d5756)

Save reference images in the collapsible sidebar to the right of the UI! These can also be renamed with a click on their names.

![SB_007](https://github.com/user-attachments/assets/85a56a9f-04ea-4210-83d2-9f63d01eb793)

## License
This project is licensed under the [MIT License](./LICENSE.md).
Some third-party assets (e.g., icons) are included under their own licenses, as detailed in the [THIRD_PARTY_LICENSES](./THIRD_PARTY_LICENSES.md) file.
