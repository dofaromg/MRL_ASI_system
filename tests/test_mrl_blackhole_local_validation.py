# origin_signature: MrLiouWord
import pytest
from mrl_blackhole.local_validation import public_summary, validate_destination

def test_authorized_dl580_directory():
    path = validate_destination(r"D:\MRL_Mother\Blackhole\validation_20261013", "nt", "WIN-PBVUI7VK2A6")
    assert path.drive == "D:"

@pytest.mark.parametrize("path,platform,host", [
    (r"C:\MRL_Mother\Blackhole", "nt", "WIN-PBVUI7VK2A6"),
    (r"D:relative", "nt", "WIN-PBVUI7VK2A6"),
    (r"D:\MRL_Mother\..\elsewhere", "nt", "WIN-PBVUI7VK2A6"),
    (r"D:\elsewhere\test", "nt", "WIN-PBVUI7VK2A6"),
    (r"D:\MRL_Mother\test", "posix", "WIN-PBVUI7VK2A6"),
    (r"D:\MRL_Mother\test", "nt", "different-host"),
])
def test_other_destinations_are_rejected(path, platform, host):
    with pytest.raises(ValueError):
        validate_destination(path, platform, host)

def test_summary_never_contains_captured_content_or_credentials():
    receipt = {"status": "HOLD", "captured": 0, "runtime_acceptance": "HOLD",
               "snapshot": {"private_text": "do not export"}, "NOTION_TOKEN": "secret",
               "error": "private response body", "files": []}
    result = public_summary(receipt)
    assert result["runtime_acceptance"] == "HOLD"
    assert not {"snapshot", "NOTION_TOKEN", "error"} & result.keys()
