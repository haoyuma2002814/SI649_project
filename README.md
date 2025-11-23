# NBA Shot Evolution Dashboard

This project recreates the visualization plan outlined in the prompt by combining
NBA Stats shot-location data with Altair-powered visuals. The script
`nba_shot_evolution.py` builds four coordinated charts: league-wide shot share
timeline, annotated rule/strategy timeline, player shot-mix explorer, and an
interactive shot-chart heatmap.

## Requirements

- Python 3.10+
- pip (or another package manager)

### Python packages

Install the project requirements in one shot:

```
pip install altair pandas nba_api
```

`nba_api` pulls in `requests` and `numpy` automatically; no extra manual installs
are needed.

## Running the Script

1. (Optional) Create and activate a virtual environment.
2. Install dependencies (see above).
3. Execute:

   ```
   python nba_shot_evolution.py
   ```

The script downloads NBA shot data (seasons 2000–2024 by default), caches raw
tables in `data_cache/`, and writes the final interactive report to
`nba_shot_evolution.html`. Open the HTML file in any modern browser to explore
the visuals.

## Customization

- **Player list**: Edit `DEFAULT_PLAYERS` near the top of the script to change
  the dropdown options.
- **Season window**: Pass `start_year` and `end_year` to `main()` if you want a
  narrower range.
- **Output path**: Supply a different `output_html` value when calling `main()`
  or modify the default inside the script.

## Data Sources & References

- NBA shot-trend reporting: https://www.nba.com/news/5-standout-stats-2024-25-season
- Shot-zone API reference: https://hexdocs.pm/nba_api_ex/NBA.Stats.LeagueDashTeamShotLocations.html
- Altair gallery/examples for normalized stacks, interactions, heatmaps:
  https://altair-viz.github.io

