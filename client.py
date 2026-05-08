#!/usr/bin/env python3
"""OpenRouter video generation terminal client."""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # Python <3.11 fallback

import questionary
import requests
from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.spinner import Spinner
from rich.table import Table

API_BASE = "https://openrouter.ai/api/v1"
ASPECT_RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "9:21"]
RESOLUTIONS = ["480p", "720p", "1080p", "1K", "2K", "4K"]
POLL_INTERVAL_SECONDS = 5

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.toml"
CONFIG_TEMPLATE = '''# OpenRouter video client config
api_key = "sk-or-v1-REPLACE_ME"
model = "google/veo-3.1"
'''

console = Console()


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(CONFIG_TEMPLATE)
        console.print(
            f"[yellow]Created template config at {CONFIG_PATH}.\n"
            f"Fill in your api_key and model, then re-run.[/yellow]"
        )
        sys.exit(1)
    with CONFIG_PATH.open("rb") as f:
        cfg = tomllib.load(f)
    api_key = cfg.get("api_key", "")
    model = cfg.get("model", "")
    if not api_key or "REPLACE_ME" in api_key:
        console.print(f"[red]Set a valid api_key in {CONFIG_PATH}[/red]")
        sys.exit(1)
    if not model:
        console.print(f"[red]Set a model in {CONFIG_PATH}[/red]")
        sys.exit(1)
    return cfg


def _required(value):
    if value is None:
        sys.exit(0)
    return value


def collect_options(model: str) -> dict:
    console.rule(f"[bold cyan]OpenRouter Video Generation — {model}[/bold cyan]")
    console.print("[dim]Tip: in multiline prompts, press Esc then Enter to submit.[/dim]\n")

    prompt = _required(questionary.text(
        "Prompt:",
        multiline=True,
        validate=lambda x: True if x.strip() else "Prompt cannot be empty",
    ).ask())

    aspect_ratio = _required(questionary.select(
        "Aspect ratio:",
        choices=ASPECT_RATIOS,
        default="16:9",
    ).ask())

    resolution = _required(questionary.select(
        "Resolution:",
        choices=RESOLUTIONS,
        default="720p",
    ).ask())

    duration_str = _required(questionary.text(
        "Duration in seconds (blank for model default):",
        validate=lambda x: True if x == "" or (x.isdigit() and int(x) > 0)
            else "Must be a positive integer or blank",
    ).ask())

    generate_audio = _required(questionary.confirm(
        "Generate audio?",
        default=True,
    ).ask())

    seed_str = _required(questionary.text(
        "Seed (blank for random):",
        validate=lambda x: True if x == "" or x.lstrip("-").isdigit()
            else "Must be an integer or blank",
    ).ask())

    payload = {
        "model": model,
        "prompt": prompt.strip(),
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "generate_audio": generate_audio,
    }
    if duration_str:
        payload["duration"] = int(duration_str)
    if seed_str:
        payload["seed"] = int(seed_str)

    table = Table(title="Request", show_header=False, title_style="bold")
    for k, v in payload.items():
        display = v if k != "prompt" else (v[:80] + "…" if len(v) > 80 else v)
        table.add_row(k, str(display))
    console.print(table)

    if not _required(questionary.confirm("Submit?", default=True).ask()):
        sys.exit(0)

    return payload


def submit_job(api_key: str, payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    r = requests.post(f"{API_BASE}/videos", json=payload, headers=headers, timeout=60)
    if r.status_code not in (200, 202):
        console.print(f"[red]Submit failed ({r.status_code}): {r.text}[/red]")
        sys.exit(1)
    return r.json()


def poll_job(api_key: str, job_id: str) -> dict:
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{API_BASE}/videos/{job_id}"
    spinner = Spinner("dots", text="Starting…")
    started = time.monotonic()

    with Live(spinner, console=console, refresh_per_second=10, transient=True):
        while True:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code != 200:
                console.print(f"[red]Poll failed ({r.status_code}): {r.text}[/red]")
                sys.exit(1)
            data = r.json()
            status = data.get("status", "unknown")
            elapsed = int(time.monotonic() - started)
            spinner.update(text=f"Status: [bold]{status}[/bold]  ({elapsed}s elapsed)")
            if status == "completed":
                return data
            if status in ("failed", "cancelled", "expired"):
                console.print(
                    f"[red]Job {status}: {data.get('error') or '(no error message)'}[/red]"
                )
                sys.exit(1)
            time.sleep(POLL_INTERVAL_SECONDS)


def download_video(api_key: str, job_id: str, output_path: Path) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{API_BASE}/videos/{job_id}/content"
    with requests.get(url, headers=headers, stream=True, timeout=300) as r:
        if r.status_code != 200:
            console.print(f"[red]Download failed ({r.status_code}): {r.text}[/red]")
            sys.exit(1)
        total = int(r.headers.get("Content-Length", 0)) or None
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading", total=total)
            with output_path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenRouter video generation terminal client"
    )
    parser.add_argument("output_dir", help="Directory to save the generated video")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    if not output_dir.is_dir():
        console.print(f"[red]Output directory does not exist: {output_dir}[/red]")
        sys.exit(1)

    cfg = load_config()
    payload = collect_options(cfg["model"])

    console.print("[cyan]Submitting job…[/cyan]")
    submit = submit_job(cfg["api_key"], payload)
    job_id = submit.get("id")
    if not job_id:
        console.print(f"[red]Submit response missing job id: {submit}[/red]")
        sys.exit(1)
    console.print(f"[green]Job submitted:[/green] {job_id}")

    try:
        result = poll_job(cfg["api_key"], job_id)
    except KeyboardInterrupt:
        console.print(
            f"\n[yellow]Interrupted. Job {job_id} may still be running on the server.[/yellow]"
        )
        sys.exit(130)

    console.print("[green]Generation complete![/green]")
    usage = result.get("usage") or {}
    if usage.get("cost") is not None:
        console.print(f"Cost: ${usage['cost']:.4f}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{timestamp}.mp4"
    download_video(cfg["api_key"], job_id, output_path)
    console.print(f"[green]Saved to[/green] {output_path}")


if __name__ == "__main__":
    main()
