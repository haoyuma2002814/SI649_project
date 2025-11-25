# Stephen Curry and the Three-Point Revolution
**NBA Shot Evolution Analysis (2000–2025)**

**Authors:** Haoyu Ma, Qihang Sun (University of Michigan)

This Streamlit application tells the story of how modern NBA offense — especially the 3-point shot — evolved from 2000 to today, and how Stephen Curry’s shooting style helped reshape the league.

## 📖 The Narrative

Stephen Curry is widely regarded as the greatest shooter in basketball history. When the NBA first adopted the 3-point line in 1979, teams averaged only about 2.8 three-point attempts per game. By 2024–25, that number has exploded to roughly 37–38. This project visualizes this "Three-Point Revolution" through data.

## 🚀 Features

### 1️⃣ Shot Distribution Evolution (2000–2025)
*   **The Shift**: Visualize the massive league-wide shift from mid-range jumpers to 3-point shots.
*   **Interactive Comparison**: Toggle between "League Average" and individual stars like Stephen Curry, LeBron James, and James Harden.
*   **Contextual Timeline**: Key events (rule changes, "Moreyball" era) are overlaid to explain *why* the game changed.

### 2️⃣ The Curry Effect: Trend Comparison
*   **3PAR Analysis**: Compare the 3-Point Attempt Rate (3PAR) of Curry against the league average and other superstars.
*   **Efficiency at Scale**: See how Curry maintained elite efficiency even as his volume broke records.

### 3️⃣ 3D Shot Map: Reshaping the Game
*   **Interactive 3D Map**: Explore a 3D hexagonal heatmap of Curry's shots on an NBA half-court (mapped to Chase Center coordinates).
*   **Spatial Analysis**: See exactly where Curry bends defenses—pulling them out to 30+ feet.
*   **Season Selector**: Filter by specific seasons or view his career aggregate.

## 🛠️ Installation & Usage

### Prerequisites
*   Python 3.8+
*   pip

### Setup

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Or manually:*
    ```bash
    pip install streamlit pandas plotly nba_api pydeck
    ```

2.  **Run the application:**
    ```bash
    streamlit run streamlit_app.py
    ```

The app will open in your browser at `http://localhost:8501`.

## 📦 Data & Caching

The app fetches real-time data from the [NBA API](https://github.com/swar/nba_api).

*   **First Run**: May take **7–12 minutes** to fetch 25 years of league data and player career stats (due to API rate limiting).
*   **Subsequent Runs**: Data is cached locally (`*.csv` files), making the app load instantly.
*   **Refresh**: Use the sidebar buttons to force a data refresh.

## 📚 Data Sources

*   **Statistics**: [NBA API](https://github.com/swar/nba_api) (unofficial client for NBA.com stats).
*   **Narrative Sources**: FiveThirtyEight, NBA.com, WBUR, Wikipedia.

---
*Built with [Streamlit](https://streamlit.io) 🎈*

