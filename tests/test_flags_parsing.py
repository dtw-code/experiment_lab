from learnloop import flags


def test_parse_lesson_length_returns_defaults_for_invalid_json():
    assert flags.parse_lesson_length("not json") == {"minutes": 10, "cards": 8}


def test_parse_lesson_length_updates_provided_fields_from_valid_json_string():
    assert flags.parse_lesson_length('{"minutes": 5, "cards": 4}') == {"minutes": 5, "cards": 4}


def test_parse_lesson_length_accepts_preparsed_dictionary():
    assert flags.parse_lesson_length({"minutes": 15, "cards": 12}) == {"minutes": 15, "cards": 12}


def test_parse_lesson_length_preserves_defaults_when_keys_are_missing():
    assert flags.parse_lesson_length('{"minutes": 25}') == {"minutes": 25, "cards": 8}
    assert flags.parse_lesson_length('{"cards": 3}') == {"minutes": 10, "cards": 3}


def test_parse_lesson_length_handles_none_and_non_dict_json():
    assert flags.parse_lesson_length(None) == {"minutes": 10, "cards": 8}
    assert flags.parse_lesson_length("[1, 2, 3]") == {"minutes": 10, "cards": 8}
    assert flags.parse_lesson_length(42) == {"minutes": 10, "cards": 8}


def test_lesson_arm_formats_duration_as_minute_suffix():
    assert flags.lesson_arm({"minutes": 5, "cards": 4}) == "5min"
    assert flags.lesson_arm({"minutes": 10, "cards": 8}) == "10min"


def test_parse_quiz_timer_converts_positive_integer_string():
    assert flags.parse_quiz_timer("60") == 60
    assert flags.parse_quiz_timer(" 30 ") == 30


def test_parse_quiz_timer_converts_positive_int_directly():
    assert flags.parse_quiz_timer(45) == 45


def test_parse_quiz_timer_returns_none_for_none_string():
    assert flags.parse_quiz_timer("none") is None
    assert flags.parse_quiz_timer("NONE") is None


def test_parse_quiz_timer_returns_none_for_zero_or_negative_values():
    assert flags.parse_quiz_timer(0) is None
    assert flags.parse_quiz_timer("0") is None
    assert flags.parse_quiz_timer(-10) is None
    assert flags.parse_quiz_timer("-5") is None


def test_parse_quiz_timer_returns_none_for_invalid_input_types():
    assert flags.parse_quiz_timer("") is None
    assert flags.parse_quiz_timer("   ") is None
    assert flags.parse_quiz_timer("unlimited") is None
    assert flags.parse_quiz_timer(None) is None


def test_parse_int_converts_valid_numeric_string_with_whitespace():
    assert flags.parse_int(" 42 ", default=10) == 42
    assert flags.parse_int(100, default=10) == 100


def test_parse_int_falls_back_to_default_on_non_numeric_input():
    assert flags.parse_int("abc", default=20) == 20
    assert flags.parse_int(None, default=20) == 20
    assert flags.parse_int("", default=20) == 20
