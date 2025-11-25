# NBA Shot Evolution Streamlit App

This Streamlit application provides an interactive visualization of NBA shot selection evolution from 2000 to 2025.

## Features

### 📊 Two Main Interactive Visualizations

1. **Shot Distribution Evolution** (2000–2025)
   - **Interactive View Switching**: Seamlessly toggle between "League Average" and individual Star Players (Stephen Curry, LeBron James, etc.) to compare career arcs against league trends.
   - **Full History**: Visualizes the complete timeline (2000–2025) for all views, allowing you to see exactly when players entered the league and how their style shifted.
   - **League Context**: When viewing League Average, key historical events (rule changes, strategic shifts) are overlaid on the chart.
   - **Dynamic Insights**: Automatically calculates key metrics (3-Point Share, Mid-Range Share, Restricted Area Share) and their change over time for the selected entity.

2. **Stephen Curry 3D Shot Chart** (Interactive Map)
   - **3D Heatmap**: Uses **PyDeck** to create a stunning 3D hexagonal heatmap of Stephen Curry's shot locations.
   - **Height = Frequency**: The height of each hexagonal tower represents the volume of shots taken from that zone.
   - **Court Overlay**: A detailed NBA half-court layout is drawn directly on the map for precise context.
   - **All-Time View**: Select any specific season from his career (2009–2025) or view his **"All Seasons"** combined shot chart.
   - **Interactive Exploration**: Pan, tilt, rotate, and zoom around the court to analyze shooting patterns from any angle.

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
pip install streamlit pandas plotly nba_api pydeck
```

2. **Run the application:**

```bash
streamlit run streamlit_app.py
```

The app will automatically open in your default web browser at `http://localhost:8501`

## First Run & Data

### Automatic Data Fetching

On first run, the app will automatically fetch data from the NBA API:

- **League data**: 25 seasons of shot location data (~2-3 minutes)
- **Player data**: Full career data for 5 star players (2000-2025) (~3-5 minutes)
- **Curry shot chart**: Full career detailed shot data (2009-2025) (~2-3 minutes)

**Total first-run time: ~7-12 minutes**

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
- **Refresh Data**: Update individual datasets from NBA API. 
  - *Note: If you want to see the full history update, click these buttons to fetch the complete dataset.*

### Interactive Features

- **Hover tooltips**: Detailed information on all charts
- **Legend toggles**: Click legend items to show/hide zones
- **Dropdowns**: Select players and seasons
- **3D Navigation**:
  - **Left Click + Drag**: Rotate and Tilt
  - **Right Click + Drag**: Pan
  - **Scroll**: Zoom

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

### Cached data seems outdated or sparse

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

## Credits

- Data: [NBA API](https://github.com/swar/nba_api)
- Visualization: Plotly & PyDeck
- Framework: Streamlit

---

**Enjoy exploring NBA shot evolution! 🏀**
