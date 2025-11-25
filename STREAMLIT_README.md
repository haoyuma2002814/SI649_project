# NBA Shot Evolution Streamlit App

This Streamlit application provides an interactive visualization of NBA shot selection evolution from 2000 to 2025.

## Features

### 📊 Four Main Visualizations

1. **League-wide Shot Distribution Timeline** (2000–2025)
   - Stacked area chart showing how shot selection has evolved across the entire league
   - Toggle key events (rule changes, strategic shifts) overlay
   - Interactive tooltips with detailed statistics

2. **Event-driven Turning Points**
   - Major rule changes and strategic milestones
   - Hand-checking rules (2004-05)
   - "Moreyball" era (2012-13)
   - Curry's MVP season (2015-16)
   - Freedom of movement rules (2018-19)

3. **Player-Level Shot Selection Evolution**
   - Compare shot selection patterns for star players:
     - Stephen Curry
     - James Harden
     - LeBron James
     - Kevin Durant
     - DeMar DeRozan
   - Interactive player selector
   - See how individual playing styles evolved over time

4. **Stephen Curry Shot Chart by Season**
   - Visual shot chart showing exact shot locations
   - Color-coded: Green (made), Red (missed)
   - Season selector to see evolution over time
   - Detailed shooting statistics (FG%, 3PT%, etc.)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install streamlit pandas plotly nba_api
```

2. **Run the application:**

```bash
streamlit run streamlit_app.py
```

The app will automatically open in your default web browser at `http://localhost:8501`

## First Run

### Automatic Data Fetching

On first run, the app will automatically fetch data from the NBA API:

- **League data**: ~25 seasons of shot location data (~2-3 minutes)
- **Player data**: 5 players × 5 seasons (~3-4 minutes)
- **Curry shot chart**: 5 seasons of detailed shot data (~1-2 minutes)

**Total first-run time: ~7-10 minutes**

Progress bars will show the fetching status. All data is cached locally for subsequent runs.

### Cached Data

Once fetched, data is saved to CSV files:
- `league_shot_zones_cache.csv` - League-wide shot data
- `player_shot_zones_cache.csv` - Player shot distribution data
- `curry_shotchart_cache.csv` - Stephen Curry shot locations

**Subsequent runs are instant** - data loads from cache in seconds!

## Usage

### Sidebar Controls

- **Cache Status**: Check which datasets are cached
- **Refresh Data**: Update individual datasets from NBA API
  - Use if you want to include the most recent season
  - Or if you suspect data is outdated

### Interactive Features

- **Hover tooltips**: Detailed information on all charts
- **Legend toggles**: Click legend items to show/hide zones
- **Dropdowns**: Select players and seasons
- **Expandable sections**: View raw data tables

### Key Insights

The app automatically calculates and displays:
- 3-point shot share change over time
- Mid-range shot decline
- Restricted area shot evolution
- Individual shooting percentages

## Data Source

All data is fetched from the [NBA API](https://github.com/swar/nba_api), an unofficial Python API client for NBA.com statistics.

### Rate Limiting

The app includes automatic rate limiting (0.6-1.0 second delays) to respect NBA API servers. This is why initial data fetching takes several minutes.

## Troubleshooting

### "nba_api not installed" error

```bash
pip install nba_api
```

### API timeout or connection errors

- Check your internet connection
- The NBA API may be temporarily unavailable
- Try refreshing the data later

### Cached data seems outdated

Use the sidebar "Refresh Data" buttons to fetch fresh data from the API.

### App runs slowly

- First run is slow due to API fetching - this is normal
- Subsequent runs should be fast (loading from cache)
- If still slow, check if your cache files exist

## Tips

1. **Let the first run complete** - Don't interrupt data fetching or you'll need to restart
2. **Use cached data** - Only refresh when you need updated stats
3. **Explore interactively** - Hover, click, and interact with all visualizations
4. **Compare players** - Switch between players to see different playing styles
5. **Look for trends** - Notice the decline in mid-range shots and rise of 3-pointers

## Differences from Notebook

This Streamlit app provides the same functionality as the Jupyter notebook but with:
- ✅ Better interactivity (dropdowns, toggles, selectors)
- ✅ Automatic data caching
- ✅ Progress indicators
- ✅ Cleaner, more polished UI
- ✅ No code cells to run manually
- ✅ Easy sharing (just share the URL when deployed)

## Future Enhancements

Possible additions:
- More players
- Team-level analysis
- Additional seasons
- Export capabilities
- Advanced filtering options
- Heat map density plots

## Credits

- Data: [NBA API](https://github.com/swar/nba_api)
- Visualization: Plotly
- Framework: Streamlit

---

**Enjoy exploring NBA shot evolution! 🏀**

