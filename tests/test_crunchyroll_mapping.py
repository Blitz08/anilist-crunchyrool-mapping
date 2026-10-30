import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crunchyroll_mapping import build_database


class BuildDatabaseTests(unittest.TestCase):
    def test_normalizes_episode_series_season_and_versions(self):
        database = build_database(
            [
                {
                    "data": [
                        {
                            "id": "episode-1",
                            "identifier": "EPI.123",
                            "series_id": "series-1",
                            "season_id": "season-1",
                            "season_number": 1,
                            "episode_number": 4,
                            "sequence_number": 4,
                            "title": "Der rote Shanks und sein Hut",
                            "episode_air_date": "1999-12-08",
                            "duration_ms": 1484953,
                            "next_episode_id": "episode-2",
                            "streams_link": "/content/v2/cms/videos/episode-1/streams",
                            "versions": [
                                {
                                    "audio_locale": "ja-JP",
                                    "subtitle_locale": "de-DE",
                                    "is_subbed": True,
                                    "is_dubbed": False,
                                }
                            ],
                        }
                    ]
                },
                {
                    "data": [
                        {
                            "id": "series-1",
                            "title": "One Piece",
                            "episode_count": 1223,
                            "season_count": 22,
                            "media_count": 1436,
                            "year": 1999,
                        }
                    ]
                },
                {
                    "data": [
                        {
                            "id": "season-1",
                            "series_id": "series-1",
                            "title": "East Blue",
                            "season_number": 1,
                        }
                    ]
                },
            ]
        )

        self.assertEqual(database["series"][0]["episode_count"], 1223)
        self.assertEqual(database["seasons"][0]["title"], "East Blue")
        episode = database["episodes"][0]
        self.assertEqual(episode["sequence_number"], 4)
        self.assertEqual(episode["air_date"], "1999-12-08")
        self.assertEqual(episode["versions"][0]["subtitle_locale"], "de-DE")
        self.assertEqual(episode["versions"][0]["is_dubbed"], False)
        self.assertNotIn("streams", episode)

    def test_combines_paginated_pages_and_deduplicates_episodes(self):
        database = build_database(
            [
                {
                    "data": [
                        {
                            "id": "a-episode-2",
                            "series_id": "series-1",
                            "episode_number": 2,
                            "sequence_number": 2,
                        }
                    ],
                    "next_cursor": "page-2",
                },
                {
                    "data": [
                        {
                            "id": "z-episode-1",
                            "series_id": "series-1",
                            "episode_number": 1,
                            "sequence_number": 1,
                        },
                        {
                            "id": "a-episode-2",
                            "series_id": "series-1",
                            "title": "Episode two",
                        },
                    ],
                    "next_cursor": "page-3",
                },
            ]
        )

        self.assertEqual(
            [episode["id"] for episode in database["episodes"]],
            ["z-episode-1", "a-episode-2"],
        )
        self.assertEqual(database["episodes"][1]["episode_number"], 2)
        self.assertEqual(database["episodes"][1]["title"], "Episode two")
        self.assertEqual(database["next_cursors"], ["page-2", "page-3"])

    def test_cli_writes_normalized_json(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "episode.json"
            output_path = Path(directory) / "mapping.json"
            input_path.write_text(
                json.dumps(
                    {
                        "data": [
                            {
                                "id": "episode-1",
                                "series_id": "series-1",
                                "episode_number": 1,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve().parents[1] / "crunchyroll_mapping.py"),
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8"))["episodes"][0]["id"],
                "episode-1",
            )

    def test_rejects_records_without_an_id(self):
        with self.assertRaisesRegex(ValueError, "missing its ID"):
            build_database([{"data": [{"episode_number": 1}]}])


if __name__ == "__main__":
    unittest.main()
