# anilist-crunchyrool-mapping

Normalize saved Crunchyroll CMS responses into a JSON mapping database. The
parser reads local response files; it does not fetch API endpoints or access
video streams.

```sh
python3 crunchyroll_mapping.py episode.json series.json seasons.json \
  episodes-page-1.json episodes-page-2.json --output mapping.json
```

Each input can be a single object response or a response with a `data` object or
array. Pass every saved episode-list page to combine its episodes; IDs are
deduplicated and any `next_cursor` values are recorded in the output as a cue
for retrieving subsequent pages. The output contains normalized `series`,
`seasons`, and `episodes` arrays. Episode records include sequence numbers,
titles, air dates, duration, next-episode and stream-link references, and
available audio/subtitle locale metadata.

Run the focused tests with:

```sh
python3 -m unittest discover -s tests
```
