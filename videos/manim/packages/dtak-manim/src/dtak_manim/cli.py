"""`dtak`: build tool for DTAK manim videos ("episodes").

    uv run dtak list
    uv run dtak new 01-my-topic            # new episode, copied from 00-lorem-ipsum
    uv run dtak docs 01                    # STORYBOARD.md + SCRIPT.md from beats/*.yaml
    uv run dtak check 01                   # beats coverage + layout checks + timing (no video)
    uv run dtak render 01                  # 480p15 preview of the whole episode (the default)
    uv run dtak render 01 --only 2         # some sections
    uv run dtak render 01 --voice gtts     # synthetic speech instead of the silent draft
    uv run dtak render 01 --sections       # also one clip per beat
    uv run dtak render 01 -q h             # 1080p60: slow, only for the final version
    uv run dtak sheet media/…/video.mp4    # contact sheet of frames, for review
    uv run dtak capture 01                 # re-run the episode's capture.sh (if any)

Episodes are folders under episodes/ with an episode.yaml; "01" matches
"01-my-topic". Output goes to media/<episode>/.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

QUALITY = {"l": "480p15", "m": "720p30", "h": "1080p60", "k": "2160p60"}


def repo_root() -> Path:
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "episodes").is_dir():
            return p
    sys.exit("run dtak inside the repository (no episodes/ folder found)")


def find_episode_dir(name: str) -> Path:
    root = repo_root() / "episodes"
    hits = [p for p in sorted(root.iterdir()) if p.name.startswith(name) and (p / "episode.yaml").exists()]
    if len(hits) != 1:
        sys.exit(f"episode {name!r}: {'not found' if not hits else 'ambiguous: ' + ', '.join(h.name for h in hits)}")
    return hits[0]


def load_episode(name: str):
    """Import the episode package (it loads its Episode with its facts)."""
    import yaml

    d = find_episode_dir(name)
    package = yaml.safe_load((d / "episode.yaml").read_text())["scenes"][0]["module"].split(".")[0]
    return importlib.import_module(package).EPISODE


def scene_file(module: str) -> str:
    return importlib.util.find_spec(module).origin


def manim(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "manim", *args], cwd=repo_root(), env={**os.environ, **(env or {})},
                          capture_output=True, text=True)


# -- commands ------------------------------------------------------------------
def cmd_list(_):
    for d in sorted((repo_root() / "episodes").iterdir()):
        status = "episode.yaml" if (d / "episode.yaml").exists() else "planned (README only)"
        print(f"{d.name:28} {status}")


def cmd_docs(a):
    from dtak_manim.docs import write_docs

    for p in write_docs(load_episode(a.episode)):
        print("wrote", p)


def timing_path(ep) -> Path:
    return repo_root() / "media" / ep.slug / "timing.json"


def cmd_check(a):
    ep = load_episode(a.episode)
    media = repo_root() / "media" / ep.slug / "check"
    failed = False
    for s in ep.sections:
        if a.only and s.number not in a.only:
            continue
        r = manim(["-ql", "-s", "--dry_run", "--media_dir", str(media), scene_file(s.module), s.scene],
                  env={"DTAK_CHECK": "1", "DTAK_VOICE": "silent", "DTAK_TIMING": str(timing_path(ep))})
        issues = re.findall(r"^LAYOUT: (.*)$", r.stdout + r.stderr, flags=re.M)
        if r.returncode != 0:
            failed = True
            print(f"✗ {s.number} {s.scene}: manim failed\n{(r.stdout + r.stderr)[-3000:]}")
        elif issues:
            failed = True
            print(f"✗ {s.number} {s.scene}: {len(issues)} layout issue(s)")
            for i in dict.fromkeys(issues):
                print("   ", i)
        else:
            print(f"✓ {s.number} {s.scene}: {len(s.beats)} beats, layout ok")
    sys.exit(1 if failed else 0)


def _duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def _srt_shift(text: str, offset: float, start_index: int) -> tuple[str, int]:
    def ts(t):
        h, m = divmod(int(t), 3600)
        m, s = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{int(round((t - int(t)) * 1000)):03d}"

    def parse(x):
        h, m, rest = x.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    blocks, i = [], start_index
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        a, b = lines[1].split(" --> ")
        blocks.append(f"{i}\n{ts(parse(a) + offset)} --> {ts(parse(b) + offset)}\n" + "\n".join(lines[2:]))
        i += 1
    return "\n\n".join(blocks), i


def cmd_render(a):
    ep = load_episode(a.episode)
    media = repo_root() / "media" / ep.slug
    if not timing_path(ep).exists():
        print("no timing.json yet: running `dtak check` first to measure the beats")
        try:
            cmd_check(argparse.Namespace(episode=a.episode, only=None))
        except SystemExit as e:
            if e.code:
                sys.exit("fix the check errors above before rendering")
    env = {"DTAK_TIMING": str(timing_path(ep))}
    if a.voice:
        env["DTAK_VOICE"] = a.voice
    clips = []
    for s in ep.sections:
        if a.only and s.number not in a.only:
            continue
        module_file = scene_file(s.module)
        args = [f"-q{a.quality}", "--media_dir", str(media), module_file, s.scene]
        if a.sections:
            args.append("--save_sections")
        print(f"→ {s.number} {s.scene}", flush=True)
        r = manim(args, env=env)
        if r.returncode != 0:
            sys.exit((r.stdout + r.stderr)[-4000:])
        clips.append(media / "videos" / Path(module_file).stem / QUALITY[a.quality] / f"{s.scene}.mp4")
    if len(clips) < 2:
        print("✔", clips[0] if clips else "nothing rendered")
        return
    out = media / f"{ep.slug}_{QUALITY[a.quality]}.mp4"
    listing = media / "concat.txt"
    listing.write_text("".join(f"file '{c}'\n" for c in clips))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(out)],
                   check=True)
    # merge the per-scene subtitles (manim-voiceover writes one .srt per scene)
    offset, index, parts = 0.0, 1, []
    for c in clips:
        srt = c.with_suffix(".srt")
        if srt.exists():
            text, index = _srt_shift(srt.read_text(), offset, index)
            parts.append(text)
        offset += _duration(c)
    if parts:
        out.with_suffix(".srt").write_text("\n\n".join(parts) + "\n")
    print(f"✔ {out}  ({offset / 60:.1f} min)")


def cmd_sheet(a):
    out = Path(a.out or Path(a.video).with_suffix(".sheet.png"))
    dur = _duration(Path(a.video))
    every = a.every or max(dur / (a.cols * a.rows), 1)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.video, "-vf",
                    f"fps=1/{every},scale=640:-1,tile={a.cols}x{a.rows}:padding=4:color=gray", "-frames:v", "1", str(out)],
                   check=True)
    print("wrote", out)


def cmd_capture(a):
    d = find_episode_dir(a.episode)
    scripts = sorted(d.glob("capture.sh")) + sorted(d.glob("*/capture.sh"))
    if not scripts:
        sys.exit(f"{d.name} has no capture.sh (an episode only needs one if it shows captured data)")
    subprocess.run([str(scripts[0])], check=True)


TEMPLATE = "00-lorem-ipsum"
TEMPLATE_PACKAGE = "lorem"


def cmd_new(a):
    """Copy the demo episode into episodes/<name>, renaming its package."""
    import shutil

    root = repo_root()
    if not re.fullmatch(r"\d\d-[a-z0-9-]+", a.name):
        sys.exit("name must look like 01-my-topic (two digits, dash, lowercase words)")
    package = a.package or re.sub(r"[^a-z0-9]", "", a.name.split("-", 1)[1])
    src, dst = root / "episodes" / TEMPLATE, root / "episodes" / a.name
    if dst.exists():
        sys.exit(f"{dst} already exists")
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "STORYBOARD.md", "SCRIPT.md"))
    (dst / "src" / TEMPLATE_PACKAGE).rename(dst / "src" / package)
    for f in [p for p in dst.rglob("*") if p.is_file() and p.suffix in {".py", ".toml", ".yaml", ".md"}]:
        text = f.read_text()
        text = text.replace(TEMPLATE, a.name)
        # only code references to the package (imports, module paths, project name), not content words
        text = re.sub(rf"(\bfrom |\bimport |src/)({TEMPLATE_PACKAGE})\b", rf"\g<1>{package}", text)
        text = re.sub(rf"\b{TEMPLATE_PACKAGE}(\.scenes|\.data)\b", rf"{package}\1", text)
        text = text.replace(f'name = "{TEMPLATE_PACKAGE}"', f'name = "{package}"').replace(f'["src/{TEMPLATE_PACKAGE}"]', f'["src/{package}"]')
        f.write_text(text)
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text()
    text = text.replace('members = [', f'members = ["episodes/{a.name}", ', 1)
    text = text.replace("[tool.uv.sources]\n", f"[tool.uv.sources]\n{package} = {{ workspace = true }}\n", 1)
    text = text.replace('dependencies = [\n', f'dependencies = [\n    "{package}",\n', 1)
    pyproject.write_text(text)
    print(f"created {dst} (package `{package}`). Next:\n"
          f"  uv sync && uv run dtak docs {a.name[:2]} && uv run dtak check {a.name[:2]} && uv run dtak render {a.name[:2]}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dtak", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    p = sub.add_parser("new")
    p.add_argument("name", help="e.g. 01-my-topic")
    p.add_argument("--package", help="python package name (default: derived from the name)")
    p.set_defaults(fn=cmd_new)
    p = sub.add_parser("docs")
    p.add_argument("episode")
    p.set_defaults(fn=cmd_docs)
    p = sub.add_parser("check")
    p.add_argument("episode")
    p.add_argument("--only", type=int, nargs="+")
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("render")
    p.add_argument("episode")
    p.add_argument("-q", "--quality", choices=QUALITY, default="l",
                   help="l (480p15, default: use it while working), m, h (1080p60, final), k")
    p.add_argument("--only", type=int, nargs="+", help="section numbers")
    p.add_argument("--voice", choices=["silent", "gtts", "recorder"])
    p.add_argument("--sections", action="store_true", help="also save one clip per beat")
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("sheet")
    p.add_argument("video")
    p.add_argument("--every", type=float)
    p.add_argument("--cols", type=int, default=3)
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("-o", "--out")
    p.set_defaults(fn=cmd_sheet)
    p = sub.add_parser("capture")
    p.add_argument("episode")
    p.set_defaults(fn=cmd_capture)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
