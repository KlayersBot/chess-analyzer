import json
import pytest
from tools import generate_game_report

def test_generate_game_invalid_user():
    res = generate_game_report("this_is_a_fake_user_name_123456789")
    data = json.loads(res)
    assert "error" in data
