"""Offline checks for the PC-local mailman; never contact DeepSeek."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
MAILMAN = ROOT / "mailman.py"
if MAILMAN.exists():
    spec = importlib.util.spec_from_file_location("mailman_under_test", MAILMAN)
    mailman = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mailman)


@unittest.skipUnless(MAILMAN.exists(), "mailman.py is PC-local and deliberately untracked")
class BriefingTests(unittest.TestCase):
    def test_real_files_are_in_actual_request_payload(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "offline test"}}]}).encode()
        with patch.object(mailman.urllib.request, "urlopen", return_value=response) as network:
            mailman.ask("Offline verification only", "fake-test-key", "fake-test-model")
        payload = json.loads(network.call_args.args[0].data)
        briefing = payload["messages"][0]["content"]
        positions = []
        for name in ("CONTEXT.md", "STATUS.md", "BOARD.md"):
            positions.append(briefing.index(f"=== {name} ==="))
            self.assertIn((ROOT / name).read_text(encoding="utf-8-sig").strip(), briefing)
        self.assertEqual(positions, sorted(positions))

    def test_required_files_fail_before_network(self):
        read = Path.read_text
        for name in ("CONTEXT.md", "STATUS.md", "BOARD.md"):
            for missing in (False, True):
                def fake_read(path, *args, **kwargs):
                    if path.name == name:
                        if missing:
                            raise FileNotFoundError(name)
                        return "   "
                    return read(path, *args, **kwargs)
                with self.subTest(name=name, missing=missing), \
                        patch.object(Path, "read_text", fake_read), \
                        patch.object(mailman.urllib.request, "urlopen") as network:
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        mailman.ask("Do not send", "fake-test-key", "fake-test-model")
                    network.assert_not_called()

    def test_board_is_read_fresh_for_each_question(self):
        read = Path.read_text
        for marker in ("first revision", "second revision"):
            def fake_read(path, *args, **kwargs):
                return marker if path.name == "BOARD.md" else read(path, *args, **kwargs)
            with patch.object(Path, "read_text", fake_read):
                self.assertIn(f"=== BOARD.md ===\n{marker}", mailman.briefing())


if __name__ == "__main__":
    unittest.main()
