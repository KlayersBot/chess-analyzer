import json
import pytest
from tools import initialize_game_analysis, GAME_STATE

def test_initialize_game_invalid_user():
    res = initialize_game_analysis("this_is_a_fake_user_name_123456789")
    data = json.loads(res)
    assert "error" in data

def test_initialize_game_valid_user():
    res = initialize_game_analysis("hikaru")
    data = json.loads(res)
    assert data.get("status") == "ready"
    assert "total_moves" in data
    assert data["total_moves"] > 0
    assert GAME_STATE.board is not None
