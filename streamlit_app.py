import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import pydeck as pdk
import os
import time
import math
from datetime import datetime

# Page config
st.set_page_config(
    page_title="NBA Shot Evolution Analysis",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import NBA API (conditionally)
try:
    from nba_api.stats.endpoints import (
        LeagueDashTeamShotLocations,
        ShotChartDetail,
        PlayerCareerStats
    )
    from nba_api.stats.static import players as static_players
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False
    st.error("⚠️ nba_api not installed. Install it with: `pip install nba_api`")

# Helper functions
def season_str(start_year: int) -> str:
    """Return NBA season string like '2000-01' from starting year int."""
    return f"{start_year}-{str(start_year + 1)[-2:]}"

def get_season_list(start=2000, end=2024):
    """Return list of season strings from start to end inclusive."""
    return [season_str(y) for y in range(start, end + 1)]

def find_player_by_name(name: str):
    """Use nba_api static players to resolve a player's ID by full or partial name."""
    if not NBA_API_AVAILABLE:
        return []
    all_players = static_players.get_players()
    matches = [p for p in all_players if name.lower() in p['full_name'].lower()]
    return matches

# Constants
SEASONS = get_season_list(2000, 2024)
LEAGUE_CACHE_FILE = 'league_shot_zones_cache.csv'
PLAYER_CACHE_FILE = 'player_shot_zones_cache.csv'
CURRY_CACHE_FILE = 'curry_shotchart_cache.csv'

ZONE_ORDER = [
    'Restricted Area',
    'In The Paint (Non-RA)',
    'Mid-Range',
    'Left Corner 3',
    'Right Corner 3',
    'Above the Break 3',
    'Backcourt'
]

ZONE_COLORS = {
    'Restricted Area': '#1f77b4',
    'In The Paint (Non-RA)': '#ff7f0e',
    'Mid-Range': '#2ca02c',
    'Left Corner 3': '#d62728',
    'Right Corner 3': '#9467bd',
    'Above the Break 3': '#8c564b',
    'Backcourt': '#e377c2'
}

# Key events data
EVENTS_DATA = [
    {'SEASON': '2004-05', 'event': 'Hand-checking rules enforced on perimeter'},
    {'SEASON': '2012-13', 'event': 'Peak "Moreyball" era in Houston (3PT emphasis)'},
    {'SEASON': '2015-16', 'event': 'Stephen Curry unanimous MVP, pull-up 3 revolution'},
    {'SEASON': '2018-19', 'event': 'Freedom of movement rules emphasize spacing'},
]

# Player names of interest
PLAYER_NAMES = [
    'Stephen Curry',
    'James Harden',
    'LeBron James',
    'Kevin Durant',
    'DeMar DeRozan'
]

# ============================================================================
# DATA FETCHING AND CACHING FUNCTIONS
# ============================================================================

@st.cache_data(show_spinner=False)
def fetch_league_shot_data():
    """Fetch league-wide shot distribution by season from NBA API."""
    if not NBA_API_AVAILABLE:
        return None
    
    zone_frames = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, season in enumerate(SEASONS):
        status_text.text(f'Fetching league data for {season}...')
        progress_bar.progress((i + 1) / len(SEASONS))
        
        try:
            resp = LeagueDashTeamShotLocations(
                season=season,
                season_type_all_star='Regular Season',
                distance_range='By Zone'
            )
            df = resp.get_data_frames()[0]
            df['SEASON'] = season
            zone_frames.append(df)
            time.sleep(1.0)  # Rate limiting
        except Exception as e:
            st.warning(f'Failed for {season}: {e}')
    
    progress_bar.empty()
    status_text.empty()
    
    if zone_frames:
        df_league_raw = pd.concat(zone_frames, ignore_index=True)
        df_league_raw.to_csv(LEAGUE_CACHE_FILE, index=False)
        return df_league_raw
    return None

@st.cache_data(show_spinner=False)
def load_league_data():
    """Load or fetch league-wide shot distribution data."""
    if os.path.exists(LEAGUE_CACHE_FILE):
        st.success(f'✅ Loaded cached league data from {LEAGUE_CACHE_FILE}')
        return pd.read_csv(LEAGUE_CACHE_FILE)
    else:
        st.warning('⚠️ Cache not found. Fetching from NBA API (this may take several minutes)...')
        return fetch_league_shot_data()

@st.cache_data(show_spinner=False)
def process_league_data(df_league_raw):
    """Transform league shot-location data into long format."""
    if df_league_raw is None:
        return None
    
    zone_names = [
        'Restricted Area',
        'In The Paint (Non-RA)',
        'Mid-Range',
        'Left Corner 3',
        'Right Corner 3',
        'Above the Break 3',
        'Backcourt'
    ]
    
    records = []
    for idx, row in df_league_raw.iterrows():
        # Skip header row if it exists
        if row.get('Unnamed: 0') == 'TEAM_ID' or row.get('Unnamed: 1') == 'TEAM_NAME':
            continue
        
        season = row['SEASON']
        team_name = row.get('Unnamed: 1', 'Unknown')
        
        for zone in zone_names:
            fga_col = f'{zone}.1'  # .1 suffix is FGA
            if fga_col in df_league_raw.columns:
                fga_value = row[fga_col]
                try:
                    fga = float(fga_value)
                    if pd.notna(fga) and fga >= 0:
                        records.append({
                            'SEASON': season,
                            'TEAM_NAME': team_name,
                            'SHOT_ZONE_BASIC': zone,
                            'FGA': fga
                        })
                except (ValueError, TypeError):
                    continue
    
    df_league_long = pd.DataFrame(records)
    
    if df_league_long.empty:
        return None
    
    # Aggregate by season and zone
    df_league = (
        df_league_long
        .groupby(['SEASON', 'SHOT_ZONE_BASIC'], as_index=False)['FGA']
        .sum()
    )
    
    # Compute share of FGA per season
    df_league['TOTAL_FGA_SEASON'] = df_league.groupby('SEASON')['FGA'].transform('sum')
    df_league['FGA_SHARE'] = df_league['FGA'] / df_league['TOTAL_FGA_SEASON']
    
    return df_league

@st.cache_data(show_spinner=False)
def fetch_player_shot_data():
    """Fetch player-level shot distribution data from NBA API."""
    if not NBA_API_AVAILABLE:
        return None
    
    # Resolve player IDs
    player_map = {}
    for name in PLAYER_NAMES:
        matches = find_player_by_name(name)
        if matches:
            player_map[name] = matches[0]['id']
    
    if not player_map:
        return None
    
    player_frames = []
    seasons_to_fetch = SEASONS
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_ops = len(player_map) * len(seasons_to_fetch)
    current_op = 0
    
    for name, pid in player_map.items():
        player_season_frames = []
        
        for season in seasons_to_fetch:
            status_text.text(f'Fetching {name} data for {season}...')
            progress_bar.progress((current_op + 1) / total_ops)
            current_op += 1
            
            try:
                resp = ShotChartDetail(
                    team_id=0,
                    player_id=pid,
                    season_type_all_star='Regular Season',
                    season_nullable=season,
                    context_measure_simple='FGA'
                )
                df_shots = resp.get_data_frames()[0]
                
                if not df_shots.empty and 'SHOT_ZONE_BASIC' in df_shots.columns:
                    df_agg = (
                        df_shots.groupby('SHOT_ZONE_BASIC')
                        .agg(
                            FGA=('SHOT_MADE_FLAG', 'count'),
                            FGM=('SHOT_MADE_FLAG', 'sum')
                        )
                        .reset_index()
                    )
                    df_agg['SEASON_ID'] = season
                    df_agg['PLAYER_NAME'] = name
                    player_season_frames.append(df_agg)
                
                time.sleep(0.6)
            except Exception as e:
                st.warning(f'Failed for {name} {season}: {e}')
        
        if player_season_frames:
            player_frames.extend(player_season_frames)
    
    progress_bar.empty()
    status_text.empty()
    
    if player_frames:
        df_players_raw = pd.concat(player_frames, ignore_index=True)
        df_players_raw.to_csv(PLAYER_CACHE_FILE, index=False)
        return df_players_raw
    return None

@st.cache_data(show_spinner=False)
def load_player_data():
    """Load or fetch player-level shot distribution data."""
    if os.path.exists(PLAYER_CACHE_FILE):
        st.success(f'✅ Loaded cached player data from {PLAYER_CACHE_FILE}')
        return pd.read_csv(PLAYER_CACHE_FILE)
    else:
        st.warning('⚠️ Player cache not found. Fetching from NBA API...')
        return fetch_player_shot_data()

@st.cache_data(show_spinner=False)
def process_player_data(df_players_raw):
    """Transform player shooting splits for visualization."""
    if df_players_raw is None:
        return None
    
    df_players = df_players_raw.copy()
    df_players.rename(columns={'SEASON_ID': 'SEASON'}, inplace=True)
    
    # Compute per-season total FGA for each player
    df_players['TOTAL_FGA_PLAYER_SEASON'] = df_players.groupby(['PLAYER_NAME', 'SEASON'])['FGA'].transform('sum')
    df_players['FGA_SHARE'] = df_players['FGA'] / df_players['TOTAL_FGA_PLAYER_SEASON']
    
    return df_players

@st.cache_data(show_spinner=False)
def fetch_curry_shotchart_data():
    """Fetch Stephen Curry shot chart data from NBA API."""
    if not NBA_API_AVAILABLE:
        return None
    
    # Get Curry's ID
    matches = find_player_by_name('Stephen Curry')
    if not matches:
        return None
    
    curry_id = matches[0]['id']
    curry_seasons = [s for s in SEASONS if int(s[:4]) >= 2009] # Curry started in 2009
    
    frames = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, season in enumerate(curry_seasons):
        status_text.text(f'Fetching Curry shot chart for {season}...')
        progress_bar.progress((i + 1) / len(curry_seasons))
        
        try:
            resp = ShotChartDetail(
                team_id=0,
                player_id=curry_id,
                season_type_all_star='Regular Season',
                season_nullable=season,
                context_measure_simple='FGA'
            )
            df = resp.get_data_frames()[0]
            df['SEASON'] = season
            frames.append(df)
            time.sleep(1.0)
        except Exception as e:
            st.warning(f'Failed for {season}: {e}')
    
    progress_bar.empty()
    status_text.empty()
    
    if frames:
        df_curry = pd.concat(frames, ignore_index=True)
        df_curry.to_csv(CURRY_CACHE_FILE, index=False)
        return df_curry
    return None

@st.cache_data(show_spinner=False)
def load_curry_shotchart_data():
    """Load or fetch Stephen Curry shot chart data."""
    if os.path.exists(CURRY_CACHE_FILE):
        st.success(f'✅ Loaded cached Curry shot chart from {CURRY_CACHE_FILE}')
        return pd.read_csv(CURRY_CACHE_FILE)
    else:
        st.warning('⚠️ Curry shot chart cache not found. Fetching from NBA API...')
        return fetch_curry_shotchart_data()

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================


def create_zone_legend_court():
    """Create a half-court diagram showing the shot zones used in the app."""
    fig = go.Figure()
    
    # Court dimensions (simplified half court, feet)
    x_min, x_max = -25, 25
    y_min, y_max = -5, 47  # include small backcourt area

    def add_zone_rect(x0, x1, y0, y1, zone_name):
        fig.add_shape(
            type="rect",
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            line=dict(width=0),
            fillcolor=ZONE_COLORS[zone_name],
            layer="below",
        )

    baseline_y = 0

    # Backcourt
    add_zone_rect(x_min, x_max, y_min, baseline_y, "Backcourt")

    # Above the Break 3 (top band)
    add_zone_rect(x_min, x_max, 22, y_max, "Above the Break 3")

    # Mid-Range band (inside arc but outside the paint)
    add_zone_rect(-22, 22, baseline_y, 22, "Mid-Range")

    # Corners 3
    add_zone_rect(x_min, -22, baseline_y, 22, "Left Corner 3")
    add_zone_rect(22, x_max, baseline_y, 22, "Right Corner 3")

    # Paint (Non-RA)
    add_zone_rect(-8, 8, 8, 16, "In The Paint (Non-RA)")

    # Restricted Area (inner paint)
    add_zone_rect(-4, 4, baseline_y, 8, "Restricted Area")

    # Court outline
    fig.add_shape(type="rect", x0=x_min, x1=x_max, y0=baseline_y, y1=y_max, line=dict(color="black", width=2))

    # Half-court line
    fig.add_shape(type="line", x0=x_min, x1=x_max, y0=baseline_y, y1=baseline_y, line=dict(color="black", width=2))

    # Add hoops / key details for polish
    fig.add_shape(
        type="circle",
        xref="x",
        yref="y",
        x0=-3,
        x1=3,
        y0=-1.5,
        y1=4.5,
        line=dict(color="#1f1f1f", width=1.5),
        fillcolor="rgba(255,255,255,0.4)",
    )
    fig.add_annotation(
        x=0,
        y=1.5,
        text="Hoop",
        showarrow=False,
        font=dict(color="#1f1f1f", size=12),
    )

    # Legend entries (dummy traces for each zone, to show colors in legend)
    for zone in ZONE_ORDER:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=ZONE_COLORS[zone]),
                name=zone,
                showlegend=True,
            )
        )

    fig.update_xaxes(
        visible=False,
        range=[x_min, x_max],
        scaleanchor="y",
        scaleratio=1,
        showgrid=False,
        zeroline=False,
    )
    fig.update_yaxes(visible=False, range=[y_min, y_max], showgrid=False, zeroline=False)

    fig.update_layout(
        title={
            "text": "NBA Shot Zones on the Half Court",
            "font": {"size": 22, "color": "#1f1f1f"},
            "x": 0,
            "xanchor": "left",
        },
        font=dict(family="Lato, 'Open Sans', sans-serif", size=13, color="#1f1f1f"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.1,          # push legend below the court
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        margin=dict(l=40, r=40, t=60, b=100),
        height=450,
    )

    return fig


def create_distribution_chart(df, title, entity_name="League Average"):
    """Create stacked area chart for shot distribution (League or Player)."""
    fig = go.Figure()
    
    seasons = sorted(df['SEASON'].unique())
    
    # Add traces for each zone (in reverse order for proper stacking)
    for zone in reversed(ZONE_ORDER):
        zone_data = df[df['SHOT_ZONE_BASIC'] == zone].sort_values('SEASON')
        
        if zone_data.empty:
            continue
        
        hover_text = [
            f"Entity: {entity_name}<br>" +
            f"Season: {season}<br>" +
            f"Zone: {zone}<br>" +
            f"Shot Share: {share:.1%}<br>" +
            f"FGA: {int(fga):,}"
            for season, share, fga in zip(
                zone_data['SEASON'],
                zone_data['FGA_SHARE'],
                zone_data['FGA']
            )
        ]
        
        fig.add_trace(go.Scatter(
            x=zone_data['SEASON'],
            y=zone_data['FGA'],
            name=zone,
            mode='lines',
            stackgroup='one',
            groupnorm='percent',
            line=dict(width=0.5, color=ZONE_COLORS[zone]),
            fillcolor=ZONE_COLORS[zone],
            hovertext=hover_text,
            hoverinfo='text'
        ))
    
    fig.update_layout(
        title={
            'text': title,
            'font': {'size': 24, 'color': '#1f1f1f'},
            'x': 0,
            'xanchor': 'left'
        },
        xaxis=dict(
            title='Season',
            title_font=dict(size=18, color='#1f1f1f'),
            tickangle=-45,
            tickfont=dict(size=12),
            type='category',
            categoryorder='array',
            categoryarray=SEASONS,  # Use global SEASONS to show full timeline
            automargin=True,
            showgrid=True,
            gridcolor='#f0f0f0',
            linecolor='#888888',
            fixedrange=False
        ),
        yaxis=dict(
            title='Share of FGA',
            title_font=dict(size=18, color='#1f1f1f'),
            tickformat='.0%',
            tickfont=dict(size=14),
            showgrid=True,
            gridcolor='#f0f0f0',
            linecolor='#888888'
        ),
        legend=dict(
            title='Shot Zone',
            title_font=dict(size=16),
            font=dict(size=14),
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02
        ),
        hovermode='closest',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=600,
        margin=dict(l=80, r=250, t=100, b=120),
        showlegend=False,
        font=dict(family="Lato, 'Open Sans', sans-serif", size=13, color='#1f1f1f'),
        hoverlabel=dict(
            bgcolor='#1f1f1f',
            font=dict(size=12, color='white')
        )
    )
    
    # Add event markers only if viewing League Average
    if entity_name == "League Average":
        for i, event in enumerate(EVENTS_DATA):
            season = event['SEASON']
            event_text = event['event']
            
            if season in seasons:
                fig.add_shape(
                    type="line",
                    x0=season,
                    x1=season,
                    y0=0,
                    y1=1,
                    yref="paper",
                    line=dict(
                        color='rgba(0, 0, 0, 0.7)',
                        width=2.5,
                        dash='dash'
                    ),
                    layer='above'
                )
                
                y_positions = [0.25, 0.40, 0.55, 0.70]
                y_pos = y_positions[i % len(y_positions)]
                
                fig.add_annotation(
                    x=season,
                    y=y_pos,
                    yref='paper',
                    text=event_text,
                    showarrow=False,
                    textangle=-90,
                    font=dict(size=9, color="white", family="Arial"),
                    bgcolor="rgba(0, 0, 0, 0.85)",
                    borderpad=5,
                    xanchor="center",
                    yanchor="middle"
                )
    
    return fig

def create_shot_chart(df_shots, selected_season):
    """Create 3D Hexagon Layer shot chart using PyDeck."""
    df_filtered = df_shots[df_shots['SEASON'] == selected_season].copy()
    
    if df_filtered.empty:
        return None
    
    # Filter for half court (LOC_Y < 420 corresponds to 42 ft range)
    df_filtered = df_filtered[df_filtered['LOC_Y'] < 420]
    
    # Map NBA coordinates to Latitude/Longitude for PyDeck
    # We'll map the court to a location (e.g., Chase Center)
    # LOC_X, LOC_Y are in 0.1 ft units
    # Scaling: 1 unit = 0.1 ft. 
    # To make it visible on a map, we can use a custom scale.
    # Let's map 10 units (1 ft) to approx 0.00001 degrees ~ 1.1 meters
    
    LAT_CENTER = 37.7680
    LON_CENTER = -122.3875
    SCALE = 0.00001
    
    # Map X (width) to Longitude, Y (length) to Latitude
    # NBA X: -250 to 250 (Left to Right) -> Longitude
    # NBA Y: -50 to 800 (Baseline to Backcourt) -> Latitude
    df_filtered['lat'] = LAT_CENTER + (df_filtered['LOC_Y'] * SCALE)
    df_filtered['lon'] = LON_CENTER + (df_filtered['LOC_X'] * SCALE)
    
    # Generate Court Lines
    court_lines = []
    def add_line(x1, y1, x2, y2):
        court_lines.append({
            "start": [LON_CENTER + x1 * SCALE, LAT_CENTER + y1 * SCALE],
            "end": [LON_CENTER + x2 * SCALE, LAT_CENTER + y2 * SCALE],
            "name": "court_line"
        })
    
    # Baseline (-52.5 to 417.5 covers the 47ft half court)
    baseline_y = -52.5
    halfcourt_y = 417.5
    
    # Outer box
    add_line(-250, baseline_y, 250, baseline_y)    # Baseline
    add_line(-250, baseline_y, -250, halfcourt_y)  # Left Side
    add_line(250, baseline_y, 250, halfcourt_y)    # Right Side
    add_line(-250, halfcourt_y, 250, halfcourt_y)  # Half Court Line
    
    # The Paint (Key)
    add_line(-80, baseline_y, -80, baseline_y + 190)
    add_line(80, baseline_y, 80, baseline_y + 190)
    add_line(-80, baseline_y + 190, 80, baseline_y + 190) # Free Throw Line
    
    # Backboard/Hoop area
    add_line(-30, baseline_y + 40, 30, baseline_y + 40) # Backboard roughly
    
    # 3-Point Line (Approximate with segments)
    # Straight parts
    add_line(-220, baseline_y, -220, baseline_y + 140)
    add_line(220, baseline_y, 220, baseline_y + 140)
    
    # Arc (Top of Key)
    # Center (0,0), Radius 237.5. connect (-220, 87.5) to (220, 87.5) via arc
    radius = 237.5
    start_angle = math.acos(220/radius) # approx 0.38 rad (~22 deg)
    end_angle = math.pi - start_angle
    
    steps = 20
    angles = [start_angle + (end_angle - start_angle) * i / steps for i in range(steps + 1)]
    
    for i in range(len(angles) - 1):
        x1 = radius * math.cos(angles[i])
        y1 = radius * math.sin(angles[i])
        x2 = radius * math.cos(angles[i+1])
        y2 = radius * math.sin(angles[i+1])
        add_line(x1, y1, x2, y2)
        
    df_court = pd.DataFrame(court_lines)

    # Define the Court Line Layer
    line_layer = pdk.Layer(
        "LineLayer",
        data=df_court,
        get_source_position="start",
        get_target_position="end",
        get_color=[50, 205, 50], # Lime Green lines for visibility
        get_width=3,
        width_min_pixels=3,
        pickable=False
    )
    
    # Define the 3D Hexagon Layer
    layer = pdk.Layer(
        "HexagonLayer",
        data=df_filtered,
        get_position=["lon", "lat"],
        radius=8,           # Increased radius to match the map scale
        elevation_scale=2,  # Adjusted scale
        elevation_range=[0, 100],
        pickable=True,
        extruded=True,
        auto_highlight=True,
        coverage=0.9,        # Slight gap between bins
        upper_percentile=100,
        material=True,
        transitions={'elevationScale': 1000},
        color_range=[
            [255, 255, 178],
            [254, 204, 92],
            [253, 141, 60],
            [240, 59, 32],
            [189, 0, 38]
        ]
    )
    
    # Set the viewport
    view_state = pdk.ViewState(
        latitude=LAT_CENTER + (100 * SCALE),
        longitude=LON_CENTER,
        zoom=16,          # Default zoom to show entire half court
        pitch=50,           # Tilted for 3D effect
        bearing=0,

    )
    
    # Tooltip
    tooltip = {
        "html": "<b>Count:</b> {elevationValue}",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }
    
    deck = pdk.Deck(
        layers=[line_layer, layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style='mapbox://styles/mapbox/dark-v10'  # Dark map style
    )
    
    return deck

def create_trend_comparison_chart(df_league, df_players, selected_players):
    """Create a line chart comparing 3-point share trends."""
    fig = go.Figure()
    
    three_pt_zones = ['Left Corner 3', 'Right Corner 3', 'Above the Break 3']
    all_seasons = SEASONS  # Use full season range for x-axis (axis only)
    
    # 1. League Trend (only seasons with data; axis still shows full range)
    league_3pt = df_league[
        df_league['SHOT_ZONE_BASIC'].isin(three_pt_zones)
    ].groupby('SEASON')['FGA_SHARE'].sum().reset_index()
    
    fig.add_trace(go.Scatter(
        x=league_3pt['SEASON'],
        y=league_3pt['FGA_SHARE'],
        name='League Average',
        line=dict(color='black', width=4, dash='dot'),
        mode='lines+markers',
        hovertemplate='<b>League Average</b><br>Season: %{x}<br>3PT Share: %{y:.1%}<extra></extra>'
    ))
    
    # 2. Stephen Curry (Always shown if available)
    curry_df = df_players[df_players['PLAYER_NAME'] == 'Stephen Curry']
    if not curry_df.empty:
        curry_3pt = curry_df[
            curry_df['SHOT_ZONE_BASIC'].isin(three_pt_zones)
        ].groupby('SEASON')['FGA_SHARE'].sum().reset_index()
        
    fig.add_trace(go.Scatter(
            x=curry_3pt['SEASON'],
            y=curry_3pt['FGA_SHARE'],
            name='Stephen Curry',
            line=dict(color='#FDB927', width=5), # Warriors Gold
            mode='lines+markers',
            hovertemplate='<b>Stephen Curry</b><br>Season: %{x}<br>3PT Share: %{y:.1%}<extra></extra>'
        ))
        
    # 3. Other Selected Players
    colors = ['#E03A3E', '#CE1141', '#007A33', '#552583', '#6F263D'] # Generic team colors
    for i, player in enumerate(selected_players):
        if player == 'Stephen Curry': continue
        
        p_df = df_players[df_players['PLAYER_NAME'] == player]
        if p_df.empty: continue
        
        p_3pt = p_df[
            p_df['SHOT_ZONE_BASIC'].isin(three_pt_zones)
        ].groupby('SEASON')['FGA_SHARE'].sum().reset_index()
        
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=p_3pt['SEASON'],
            y=p_3pt['FGA_SHARE'],
            name=player,
            line=dict(color=color, width=3),
            mode='lines+markers',
            hovertemplate=f'<b>{player}</b><br>Season: %{{x}}<br>3PT Share: %{{y:.1%}}<extra></extra>'
        ))
    
    fig.update_layout(
        title={
            'text': 'The 3-Point Revolution: Curry vs. The Field',
            'font': {'size': 24, 'color': '#1f1f1f'}
        },
        xaxis=dict(
            title='Season',
            title_font=dict(size=18, color='#1f1f1f'),
            tickangle=-45,
            tickfont=dict(size=12),
            type='category',
            categoryorder='array',
            categoryarray=all_seasons,
            automargin=True,
            showgrid=True,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title='3-Point Attempt Rate (3PAR)',
            title_font=dict(size=18, color='#1f1f1f'),
            tickformat='.0%',
            tickfont=dict(size=14),
            showgrid=True,
            gridcolor='lightgray'
        ),
        legend=dict(
            title='Entity',
            font=dict(size=14),
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.8)"
        ),
        hovermode='x unified',
        plot_bgcolor='white',
        height=600,
        margin=dict(l=80, r=50, t=100, b=100)
    )
    
    return fig

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.title("Stephen Curry and the Three-Point Revolution")
    
    st.markdown("""
    Stephen Curry is widely regarded as the greatest shooter in basketball history, and he is 
    > *“credited with revolutionizing the game by popularizing the three-point shot across all levels”* 
    > ([Wikipedia](https://en.wikipedia.org)). 
    
    The data back this up: when the NBA first adopted the 3-point line in 1979, teams averaged only about 
    **2.8** three-point attempts per game. By 2024–25, that number has exploded to roughly **37–38** 
    three-point attempts per game ([Wikipedia](https://en.wikipedia.org), [WBUR](https://www.wbur.org)). 
    
    As one analyst noted, Curry has become:
    > *“perhaps the figurehead in the NBA’s Three-Point Revolution™”* 
    > ([FiveThirtyEight](https://fivethirtyeight.com)).
    """)

    st.markdown("""
    In short, the style of play that Curry and the Golden State Warriors exemplified – high-volume, 
    deep shooting – has spread across the league. Teams shot **22.4** threes per game in 2014-15, but 
    by the 2024-25 season that had risen to **37.6** ([WBUR](https://www.wbur.org)), and many coaches 
    now prioritize spacing and threes over older mid-range strategies. Some commentators joke we’re 
    even seeing more threes than twos – one analyst quipped that we might as well rename it the 
    “two-point line” ([WBUR](https://www.wbur.org)).
    """)
    
    st.divider()

    # Sidebar for data management
    st.sidebar.markdown("## Authors")
    st.sidebar.markdown("""
    **Haoyu Ma**  
    **Qihang Sun**  
    *University of Michigan*
    """)
    st.sidebar.divider()

    st.sidebar.title("⚙️ Data Management")
    
    if not NBA_API_AVAILABLE:
        st.sidebar.error("NBA API not available. Please install nba_api.")
        return
    
    # Check cache status
    league_cached = os.path.exists(LEAGUE_CACHE_FILE)
    player_cached = os.path.exists(PLAYER_CACHE_FILE)
    curry_cached = os.path.exists(CURRY_CACHE_FILE)
    
    st.sidebar.markdown("### Cache Status")
    st.sidebar.write(f"League Data: {'✅' if league_cached else '❌'}")
    st.sidebar.write(f"Player Data: {'✅' if player_cached else '❌'}")
    st.sidebar.write(f"Curry Shot Chart: {'✅' if curry_cached else '❌'}")
    
    # Data refresh buttons
    st.sidebar.markdown("### Refresh Data")
    if st.sidebar.button("🔄 Refresh League Data"):
        if os.path.exists(LEAGUE_CACHE_FILE):
            os.remove(LEAGUE_CACHE_FILE)
        st.rerun()
    
    if st.sidebar.button("🔄 Refresh Player Data"):
        if os.path.exists(PLAYER_CACHE_FILE):
            os.remove(PLAYER_CACHE_FILE)
        st.rerun()
    
    if st.sidebar.button("🔄 Refresh Curry Data"):
        if os.path.exists(CURRY_CACHE_FILE):
            os.remove(CURRY_CACHE_FILE)
        st.rerun()
    
    # Load data
    with st.spinner("Loading data..."):
        df_league_raw = load_league_data()
        df_league = process_league_data(df_league_raw) if df_league_raw is not None else None
        
        df_players_raw = load_player_data()
        df_players = process_player_data(df_players_raw) if df_players_raw is not None else None
        
        df_curry_shots = load_curry_shotchart_data()
    
    # Visualization 1: Shot Distribution Evolution
    st.header("1️⃣ The Data Tell the Story: Shot Selection Shift")
    
    with st.container():
        st.info("""
        **Context:** In 2014–15, Curry’s Warriors led the league in 3-point volume and won a championship. 
        Analysis of that season shows that the Warriors took many more threes than any other team – 
        and they scored huge value from them. That year, all of the top 3-point shooting teams made 
        the conference finals ([FiveThirtyEight](https://fivethirtyeight.com)). 
        
        *In other words, teams that shot a lot of threes and hit them at a high rate tended to win; 
        the correlation between 3-point rate and winning percentage was the highest ever recorded* 
        ([FiveThirtyEight](https://fivethirtyeight.com)).
        
        Golden State’s deep shooting and ball-movement offense proved to be a championship formula, 
        and other teams took notice.
        """)

    st.markdown(
        "Use the dropdown to switch between **League Average** and individual players to see this shift."
    )

    # Prepare selection options
    options = ["League Average"]
    if df_players is not None and not df_players.empty:
        options += sorted(df_players['PLAYER_NAME'].unique())
    
    selected_entity = st.selectbox("Select View:", options, index=0)
    
    # Determine which dataframe to use
    current_df = None
    chart_title = ""
    
    if selected_entity == "League Average":
        if df_league is not None:
            current_df = df_league
            chart_title = 'League-wide Shot Distribution by Zone (2000–2025)'
    else:
        if df_players is not None:
            current_df = df_players[df_players['PLAYER_NAME'] == selected_entity]
            chart_title = f'{selected_entity} - Shot Selection Evolution by Zone'
            
    # Render chart and insights
    if current_df is not None and not current_df.empty:
        # Create and display chart alongside zone legend court
        fig1 = create_distribution_chart(
            current_df, 
            chart_title,
            entity_name=selected_entity
        )

        # Use a slightly wider left panel while keeping the right panel readable
        col_chart, col_legend = st.columns([3, 2])
        with col_chart:
            st.plotly_chart(fig1, width='stretch')
        with col_legend:
            zone_fig = create_zone_legend_court()
            st.plotly_chart(zone_fig, width='stretch')
        
        # Calculate Key Insights dynamically
        st.subheader(f"📈 Key Insights ({selected_entity})")
        col1, col2, col3 = st.columns(3)
        
        three_pt_zones = ['Left Corner 3', 'Right Corner 3', 'Above the Break 3']
        seasons = sorted(current_df['SEASON'].unique())
        first_season = seasons[0]
        last_season = seasons[-1]
        
        # Helper to get share safely
        def get_share(df, season, zones):
            if isinstance(zones, list):
                mask = (df['SEASON'] == season) & (df['SHOT_ZONE_BASIC'].isin(zones))
            else:
                mask = (df['SEASON'] == season) & (df['SHOT_ZONE_BASIC'] == zones)
            
            val = df[mask]['FGA_SHARE'].sum()
            return val
        
        # 3-Point Share
        three_pt_first = get_share(current_df, first_season, three_pt_zones)
        three_pt_last = get_share(current_df, last_season, three_pt_zones)
        
        with col1:
            st.metric(
                "3-Point Shot Share",
                f"{three_pt_last:.1%}",
                f"{((three_pt_last - three_pt_first)):+.1%} since {first_season}"
            )
        
        # Mid-Range Share
        mid_range_first = get_share(current_df, first_season, 'Mid-Range')
        mid_range_last = get_share(current_df, last_season, 'Mid-Range')
        
        with col2:
            st.metric(
                "Mid-Range Shot Share",
                f"{mid_range_last:.1%}",
                f"{((mid_range_last - mid_range_first)):+.1%} since {first_season}"
            )
        
        # Restricted Area Share
        restricted_first = get_share(current_df, first_season, 'Restricted Area')
        restricted_last = get_share(current_df, last_season, 'Restricted Area')
        
        with col3:
            st.metric(
                "Restricted Area Share",
                f"{restricted_last:.1%}",
                f"{((restricted_last - restricted_first)):+.1%} since {first_season}"
            )
        
        # Show data
        with st.expander(f"📋 View {selected_entity} Data"):
            st.dataframe(current_df.sort_values(['SEASON', 'SHOT_ZONE_BASIC']), width='stretch')
            
    else:
        st.warning(f"Data not available for {selected_entity}. Please refresh to fetch from NBA API.")
    
    st.divider()

    # Visualization 2: The Curry Effect Comparison
    st.header("2️⃣ Curry’s Individual Impact & Records")
    
    st.markdown("""
    Curry’s individual shooting numbers have consistently defied expectations. 
    He broke Ray Allen’s single-season 3-point record (**269**) during the 2012–13 season (with **272** threes), 
    and then smashed that record again with **402** threes in 2015–16 ([NBA.com](https://www.nba.com)).
    """)

    st.markdown("### Efficiency at Scale")
    st.markdown("""
    Remarkably, as Curry’s shot volume went up, his efficiency did not drop. By late 2015, Curry was 
    attempting nearly **29** field goals (15.5 threes) per 100 possessions – career highs – yet his shooting 
    percentage actually improved ([FiveThirtyEight](https://fivethirtyeight.com)). 
    
    Analysts have shown that Curry’s enormous volume combined with elite shooting added far more scoring 
    value than any other player. In one study of 2014–15 data:
    - **Stephen Curry:** Accumulated **371** “points added” from efficient shooting (on ~1,600 shots)
    - **Kyle Korver:** Next highest, with **247** points added
    
    Data analysis illustrates that Curry’s unprecedented range and volume put him in a class of his own: 
    he remained a deadly efficient shooter even as his offensive load soared.
    """)

    st.success("""
    **Curry vs. The Field**
    
    Curry’s shooting records extend to career totals. In fact, Curry needed only **762** games to surpass 
    Reggie Miller’s total (which took Miller 1,389 games) ([NBA.com](https://www.nba.com)). 
    
    - On **January 12, 2022**, Curry broke Ray Allen’s all-time record to become the NBA’s career leader in 3-pointers.
    - By **2025**, he has led the league in total 3-pointers made a record **eight times**.
    
    These milestones underline how rapidly and consistently Curry has hit long-range shots compared to any predecessor.
    """)
    
    st.markdown("**Compare Curry's 3-Point Attempt Rate (3PAR) to the League Average and other stars:**")

    if df_league is not None and df_players is not None:
        # Multi-select for other players
        available_stars = sorted([p for p in df_players['PLAYER_NAME'].unique() if p != 'Stephen Curry'])
        default_compare = [p for p in ['James Harden', 'LeBron James'] if p in available_stars]
        
        comparison_players = st.multiselect(
            "Compare other stars:", 
            options=available_stars,
            default=default_compare
        )
        
        fig2 = create_trend_comparison_chart(df_league, df_players, comparison_players)
        st.plotly_chart(fig2, width='stretch')
    else:
        st.warning("Data not available for comparison chart.")

    st.divider()

    # Visualization 3: Stephen Curry shot chart
    st.header("3️⃣ Beyond the Numbers: Reshaping the Game")
    st.markdown("""
    Curry’s impact goes beyond just raw numbers; he reshaped how the game is played. 
    His shooting range and quick release forced defenses to guard him out to 30 feet. 
    
    **Key indicators of the shift:**
    - **Pull-up Revolution:** Over eight seasons of tracking data, **54%** of Curry’s 3-point attempts were pull-up jumpers (shots off the dribble), showcasing that he created his own looks and thrived under pressure.
    - **League Follows Suit:** League-wide, the share of pull-up threes jumped from about **23%** in 2013–14 to a peak of **30%** by 2019–20, as other players emulated his style.
    - **The Math of Moreyball:** Coaches like Mike D’Antoni and Daryl Morey seized on the math: when a roughly 35% three-point shot is often worth more points than a 40% long two, it makes sense to “take the smart ones” – i.e., shoot threes.
    
    By 2017–18 the Houston Rockets were attempting about **50%** of their shots from three (the NBA’s first 50%-of-shots 3-point rate). Today almost every team plays “pace and space”: in 2024–25, the Boston Celtics even became the first team in history to attempt more threes than twos in a game ([WBUR](https://www.wbur.org)). 
    
    In short, Curry’s success convinced teams and players at all levels to shoot from farther out, and now long-range shooting dominates the NBA landscape.
    """)

    st.markdown("""
    ### 3D Shot Map: Where Curry Bends the Defense
    Explore the 3D map below to see the volume and location of Curry's shots. Note the density beyond the arc.
    """)
    
    if df_curry_shots is not None and not df_curry_shots.empty:
        seasons_available = sorted(df_curry_shots['SEASON'].unique())
        selected_season = st.selectbox("Select a season:", seasons_available, index=len(seasons_available)-1)
        
        deck = create_shot_chart(df_curry_shots, selected_season)
        if deck:
            st.pydeck_chart(deck, width="stretch")
            st.caption("Standard NBA half-court mapped to Chase Center, San Francisco. Height represents shot frequency in that zone.")
        else:
            st.warning(f"No shot chart data available for {selected_season}")
        
        # Shot statistics
        season_data = df_curry_shots[df_curry_shots['SEASON'] == selected_season]
        if not season_data.empty:
            st.subheader("📊 Shot Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            total = len(season_data)
            made = season_data['SHOT_MADE_FLAG'].sum()
            fg_pct = (made / total * 100) if total > 0 else 0
            
            three_pt = season_data[season_data['SHOT_TYPE'] == '3PT Field Goal']
            three_pt_made = three_pt['SHOT_MADE_FLAG'].sum()
            three_pt_total = len(three_pt)
            three_pt_pct = (three_pt_made / three_pt_total * 100) if three_pt_total > 0 else 0
            
            with col1:
                st.metric("Total Shots", f"{total:,}")
            with col2:
                st.metric("FG%", f"{fg_pct:.1f}%")
            with col3:
                st.metric("3PT Made", f"{three_pt_made}/{three_pt_total}")
            with col4:
                st.metric("3PT%", f"{three_pt_pct:.1f}%")
        
        with st.expander("📋 View Shot Data"):
            st.dataframe(
                season_data[['SEASON', 'SHOT_ZONE_BASIC', 'SHOT_DISTANCE', 'SHOT_TYPE', 
                            'ACTION_TYPE', 'SHOT_MADE_FLAG', 'LOC_X', 'LOC_Y']],
                width='stretch'
            )
    else:
        st.warning("Curry shot chart data not available. Please refresh to fetch from NBA API.")
    
    st.divider()

    # Conclusion and Sources
    st.header("Questions & Conclusion")
    
    st.warning("""
    **The ongoing debate:**
    Some fans and even players have lamented an overload of 3-point shooting (worse ratings or “boring” offense). 
    Stars like LeBron James and NBA commissioner Adam Silver have publicly mused about whether teams are taking 
    too many threes. Such debates show how deeply Curry has changed the game: what used to be a rare, exciting play has become commonplace. 
    
    *But on balance his influence has opened up basketball. As one analyst put it, the 3-point line has “made the sport better” by diversifying play and rewarding perimeter skill.*
    """)

    st.success("""
    **Conclusion**
    
    Stephen Curry’s career is a chronicle of a shooting revolution in action. Through astonishing statistics and 
    championship success, he forced every team to re-think offense. The Warriors’ four titles in eight years 
    (with Curry as the star) have made “lots of threes” into a winning blueprint. 
    
    Even youth basketball and the WNBA have moved their lines back to emulate today’s range. Whether his influence 
    is universally loved or debated, one thing is clear: **Curry’s unprecedented shooting ability has permanently 
    shifted the NBA toward a game where the three-point shot is the most potent weapon on the floor.**
    """)

    st.caption("""
    **Sources:**
    Authoritative sports analytics and journalism sources document Curry’s impact and league trends, including:
    [FiveThirtyEight](https://fivethirtyeight.com), [NBA.com Analysis](https://www.nba.com), 
    [WBUR Commentary](https://www.wbur.org), and [Wikipedia](https://en.wikipedia.org).
    """)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>Data source: <a href='https://github.com/swar/nba_api'>NBA API</a></p>
        <p>Built with Streamlit 🎈 | Last updated: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
