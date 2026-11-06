import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_preservation as checker  # noqa: E402

SOURCE = "- [ ] FU-REQ-007: `tia-smoke` label 게이트, busy_timeout=5000, 7/9 🟢\n경로 `docs/a.md` 참고 https://x.io/a\n"


def test_identical_text_passes():
    report = checker.build_report(SOURCE, SOURCE, 1.0)
    assert report["missing_count"] == 0
    assert report["over_budget"] is False


def test_reformatted_code_span_is_not_missing():
    edited = SOURCE.replace("`tia-smoke`", "` tia-smoke `")
    assert checker.build_report(SOURCE, edited, None)["missing_count"] == 0


def test_dropped_identifier_and_status_are_reported():
    edited = "FU-REQ-007: 라벨 게이트, busy_timeout=5000\n"
    missing = checker.build_report(SOURCE, edited, None)["missing"]
    assert "`tia-smoke`" in missing["inline_code"]
    assert "🟢" in missing["status_emoji"]
    assert missing["checkbox"] == ["1 checkbox line(s)"]


def test_length_budget_flags_expansion():
    assert checker.build_report("짧다.", "훨씬 더 길게 풀어 쓴 문장이다.", 1.0)["over_budget"] is True


def test_mixed_register_detected():
    counts = checker.register_counts("검증했다. 확인했다. 정리했어요. 반영했어요.")
    assert checker.is_mixed_register(counts) is True


def test_cli_exit_codes(tmp_path):
    source_file = tmp_path / "s.md"
    edited_file = tmp_path / "e.md"
    source_file.write_text(SOURCE, encoding="utf-8")
    edited_file.write_text(SOURCE, encoding="utf-8")
    assert checker.main([str(source_file), str(edited_file)]) == 0
    edited_file.write_text("내용 삭제", encoding="utf-8")
    assert checker.main([str(source_file), str(edited_file)]) == 1
    assert checker.main([str(source_file), str(tmp_path / "none.md")]) == 2


def test_exclude_fenced_ignores_added_diagram_in_length():
    source = "API가 요청을 받아 큐에 넣는다.\n"
    diagram = "```text\n[사용자] --요청--> [API] --적재--> [Queue]\n```\n"
    edited = "API가 요청을 받아 큐에 넣는다.\n\n" + diagram
    assert checker.build_report(source, edited, 1.0)["over_budget"] is True
    assert checker.build_report(source, edited, 1.0, exclude_fenced=True)["over_budget"] is False


def test_exclude_fenced_still_reports_missing_code_tokens():
    source = "설정은 `busy_timeout=5000`이다.\n```text\nA --> B\n```\n"
    edited = "설정을 바꿨다.\n"
    missing = checker.build_report(source, edited, None, exclude_fenced=True)["missing"]
    assert "`busy_timeout=5000`" in missing["inline_code"]


def test_cli_exclude_fenced_flag(tmp_path):
    source_file = tmp_path / "s.md"
    edited_file = tmp_path / "e.md"
    source_file.write_text("A가 B를 호출한다.\n", encoding="utf-8")
    edited_file.write_text("A가 B를 호출한다.\n```text\n[A] --호출--> [B]\n```\n", encoding="utf-8")
    assert checker.main([str(source_file), str(edited_file), "--max-ratio", "1.0"]) == 1
    assert checker.main([str(source_file), str(edited_file), "--max-ratio", "1.0", "--exclude-fenced"]) == 0


def test_pure_hamnida_is_not_mixed():
    counts = checker.register_counts("반영했습니다. 확인했습니다. 정리했습니다.")
    assert counts["handa"] == 0
    assert checker.is_mixed_register(counts) is False
