from hbg_free_material.cli import build_parser


def test_cli_parses_image_search():
    args = build_parser().parse_args(["search", "tea shop", "--platform", "all", "--json"])
    assert args.command == "search"
    assert args.query == "tea shop"
    assert args.json is True


def test_cli_parses_video_quality():
    args = build_parser().parse_args(["video", "search", "cat", "--quality", "small"])
    assert args.command == "video"
    assert args.video_command == "search"
    assert args.quality == "small"
