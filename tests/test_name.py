from mcp_preflight.checks.name import check_name


def test_name_detects_case_collision():
    report = check_name("HubSpot")
    rules = {f.rule for f in report.findings}
    assert "case_collision" in rules


def test_name_clean():
    report = check_name("my-new-mcp")
    assert report.band == "GREEN"


def test_name_similarity():
    report = check_name("mcp-scanr")
    rules = {f.rule for f in report.findings}
    assert "mcp_name_similarity" in rules or "brand_similarity" in rules
