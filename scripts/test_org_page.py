"""Organization-page CLI regression tests, using only the standard library."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE_SCRIPT = ROOT / "scripts/org-page.py"


@contextmanager
def page_checkout():
    """A real page and sources, with only an offline GitHub CLI on PATH."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in ("golden-rules", "profile"):
            shutil.copytree(ROOT / name, root / name)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            "assert sys.argv[1:] == ['api', '--paginate', '--slurp', "
            "'orgs/Orchestration-Maestro/repos?per_page=100']\n"
            "print('[[{\"name\": \"maestro-example\", \"description\": "
            "\"Example repository.\", \"visibility\": \"public\", \"archived\": false}]]')\n",
            encoding="utf-8",
        )
        gh.chmod(0o755)
        yield root, {**os.environ, "PATH": str(bin_dir)}


class OrganizationPage(unittest.TestCase):
    def test_renders_and_checks_without_rust_gate_on_path(self):
        with page_checkout() as (root, env):
            self.assertIsNone(shutil.which("rust-gate", path=env["PATH"]))
            command = [sys.executable, str(PAGE_SCRIPT), "--root", str(root)]
            rendered = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            self.assertIn("wrote profile/README.md", rendered.stdout)
            page = root / "profile/README.md"
            content = page.read_text(encoding="utf-8")
            self.assertIn(
                "| [maestro-example](https://github.com/Orchestration-Maestro/maestro-example) "
                "| Example repository |", content,
            )
            checked = subprocess.run(
                [*command, "--check"], env=env, capture_output=True, text=True,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(page.read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
