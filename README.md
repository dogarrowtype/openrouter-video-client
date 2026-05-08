# OpenRouter Video Client

A small terminal client for generating videos through the [OpenRouter](https://openrouter.ai) video API. It walks you through prompt + options, submits the job, polls until it's ready, and downloads the result.

## Quick start (Linux)

```bash
./launch.sh
```

That's it. On first run the script will:

1. Find a suitable Python 3 (3.9+).
2. Create a virtualenv in `.venv/`.
3. Install dependencies from `requirements.txt`.
4. Create an `output/` directory.
5. Generate a `config.toml` template if one doesn't exist, then exit so you can fill in your API key.

Edit `config.toml`:

```toml
api_key = "sk-or-v1-..."        # from https://openrouter.ai/keys
model   = "google/veo-3.1"      # or any other OpenRouter video model
```

Then re-run `./launch.sh` and follow the prompts.

## Prerequisites

- Python 3.9 or newer with `venv` support
  - Debian/Ubuntu: `sudo apt install python3 python3-venv python3-pip`
  - Fedora: `sudo dnf install python3 python3-pip`
  - Arch: `sudo pacman -S python python-pip`
- An OpenRouter API key with access to a video model

## Usage

```bash
./launch.sh                       # save videos to ./output/
OUTPUT_DIR=/path/to/dir ./launch.sh   # save somewhere else
```

You'll be asked for:

- **Prompt** (multi-line — press Esc then Enter to submit)
- **Aspect ratio** — `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `21:9`, `9:21`
- **Resolution** — `480p`, `720p`, `1080p`, `1K`, `2K`, `4K`
- **Duration** in seconds (blank uses the model default)
- **Audio** on/off
- **Seed** (blank for random)

Generated videos are saved as `output/<timestamp>.mp4`.

## Files

- `client.py` — the actual client
- `launch.sh` — Linux setup + run wrapper
- `config.toml` — your API key and model (created on first run)
- `requirements.txt` — Python dependencies
- `output/` — generated videos
- `*.md` (create-videos, list-models, poll-status, download-video) — OpenRouter API reference notes

## Running directly

If you'd rather skip the wrapper:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python client.py ./output
```
