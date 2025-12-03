"""
Real-time GNSS Monitoring Dashboard
Displays live GNSS data, anomalies, and visualizations
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import folium_static
import os
import glob
import time
from datetime import datetime, timedelta
import yaml

# Page configuration
st.set_page_config(
    page_title="GNSS Anomaly Detection",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .critical { color: #ff4b4b; }
    .warning { color: #ffa500; }
    .ok { color: #00cc00; }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=2)
def load_config(config_path='config/settings.yaml'):
    """Load configuration file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        st.error(f"Configuration file not found: {config_path}")
        return None


@st.cache_data(ttl=2)
def load_anomalies(output_dir='results'):
    """Load anomaly data from CSV files"""
    try:
        # Find all CSV files in anomalies directory
        csv_pattern = os.path.join(output_dir, 'anomalies_csv', '*.csv')
        csv_files = glob.glob(csv_pattern)
        
        if not csv_files:
            return pd.DataFrame()
        
        # Read all CSV files
        dfs = []
        for file in csv_files[-10:]:  # Last 10 files
            try:
                df = pd.read_csv(file)
                dfs.append(df)
            except Exception as e:
                continue
        
        if not dfs:
            return pd.DataFrame()
        
        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Convert timestamp
        if 'timestamp' in combined_df.columns:
            combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'])
        
        return combined_df.sort_values('timestamp', ascending=False)
    
    except Exception as e:
        st.error(f"Error loading anomalies: {e}")
        return pd.DataFrame()


def generate_sample_data(num_points=100):
    """Generate sample data for demonstration"""
    import numpy as np
    
    timestamps = pd.date_range(
        start=datetime.now() - timedelta(minutes=10),
        end=datetime.now(),
        periods=num_points
    )
    
    base_lat = -33.865
    base_lon = 151.209
    
    data = []
    for i, ts in enumerate(timestamps):
        # Simulate multiple satellites
        for sat in range(1, 10):
            snr = np.random.normal(35, 10)
            if np.random.random() < 0.1:  # 10% anomalies
                snr = np.random.uniform(10, 20)
                anomaly = True
                anomaly_type = "SIGNAL_DROP"
            else:
                anomaly = False
                anomaly_type = "NONE"
            
            data.append({
                'timestamp': ts,
                'lat': base_lat + np.random.uniform(-0.0001, 0.0001),
                'lon': base_lon + np.random.uniform(-0.0001, 0.0001),
                'satellite_id': f'G{sat:02d}',
                'snr': max(0, snr),
                'num_sats': np.random.randint(8, 14),
                'hdop': np.random.uniform(0.8, 2.0),
                'anomaly_detected': anomaly,
                'anomaly_type': anomaly_type,
                'signal_drop': anomaly,
                'satellite_loss': False,
                'position_drift': False
            })
    
    return pd.DataFrame(data)


def create_snr_timeline(df):
    """Create SNR timeline chart"""
    if df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # Group by satellite
    for sat_id in df['satellite_id'].unique()[:10]:  # Limit to 10 satellites
        sat_data = df[df['satellite_id'] == sat_id].sort_values('timestamp')
        
        fig.add_trace(go.Scatter(
            x=sat_data['timestamp'],
            y=sat_data['snr'],
            mode='lines+markers',
            name=sat_id,
            line=dict(width=2),
            marker=dict(size=4)
        ))
    
    # Add threshold line
    fig.add_hline(
        y=20, 
        line_dash="dash", 
        line_color="red",
        annotation_text="SNR Threshold"
    )
    
    fig.update_layout(
        title="Signal Strength (SNR) Over Time",
        xaxis_title="Time",
        yaxis_title="SNR (dB)",
        hovermode='x unified',
        height=400,
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.01)
    )
    
    return fig


def create_satellite_count_chart(df):
    """Create satellite count chart"""
    if df.empty:
        return go.Figure()
    
    # Aggregate by timestamp
    sat_count = df.groupby('timestamp')['num_sats'].first().reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=sat_count['timestamp'],
        y=sat_count['num_sats'],
        mode='lines+markers',
        name='Satellites',
        fill='tozeroy',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=6)
    ))
    
    # Add minimum threshold line
    fig.add_hline(
        y=5,
        line_dash="dash",
        line_color="red",
        annotation_text="Minimum Required"
    )
    
    fig.update_layout(
        title="Number of Satellites in View",
        xaxis_title="Time",
        yaxis_title="Number of Satellites",
        height=300,
        hovermode='x unified'
    )
    
    return fig


def create_position_map(df):
    """Create map with position markers"""
    if df.empty or 'lat' not in df.columns:
        # Default location
        m = folium.Map(location=[-33.865, 151.209], zoom_start=15)
        return m
    
    # Get latest position
    latest = df.sort_values('timestamp').iloc[-1]
    
    # Create map centered on latest position
    m = folium.Map(
        location=[latest['lat'], latest['lon']],
        zoom_start=15,
        tiles='OpenStreetMap'
    )
    
    # Add markers for recent positions
    recent_df = df.sort_values('timestamp').tail(50)
    
    for idx, row in recent_df.iterrows():
        if pd.notna(row['lat']) and pd.notna(row['lon']):
            # Color based on anomaly
            color = 'red' if row.get('anomaly_detected', False) else 'blue'
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=3,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.6,
                popup=f"Time: {row['timestamp']}<br>SNR: {row['snr']:.1f} dB"
            ).add_to(m)
    
    # Add marker for current position
    folium.Marker(
        location=[latest['lat'], latest['lon']],
        popup=f"Current Position<br>SNR: {latest['snr']:.1f} dB<br>Sats: {latest['num_sats']}",
        icon=folium.Icon(color='green', icon='info-sign')
    ).add_to(m)
    
    return m


def create_anomaly_distribution(df):
    """Create anomaly distribution pie chart"""
    if df.empty or 'anomaly_type' not in df.columns:
        return go.Figure()
    
    anomaly_counts = df[df['anomaly_detected'] == True]['anomaly_type'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=anomaly_counts.index,
        values=anomaly_counts.values,
        hole=0.3
    )])
    
    fig.update_layout(
        title="Anomaly Distribution",
        height=300
    )
    
    return fig


def main():
    """Main dashboard application"""
    
    # Header
    st.title("🛰️ GNSS Real-Time Anomaly Detection Dashboard")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Load config
        config = load_config()
        
        if config:
            st.success("✓ Configuration loaded")
            
            # Display thresholds
            st.subheader("Detection Thresholds")
            st.metric("SNR Threshold", f"{config['anomaly_detection']['snr_threshold']} dB")
            st.metric("Min Satellites", config['anomaly_detection']['min_satellites'])
            st.metric("Drift Threshold", f"{config['anomaly_detection']['drift_threshold']}°")
        else:
            st.error("✗ Configuration not loaded")
        
        st.markdown("---")
        
        # Refresh controls
        st.subheader("Display Options")
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_interval = st.slider("Refresh interval (s)", 1, 10, 2)
        
        use_sample_data = st.checkbox("Use sample data", value=True, 
                                     help="Use generated sample data for demonstration")
        
        st.markdown("---")
        st.caption("GNSS Anomaly Detection System v1.0")
    
    # Load data
    if use_sample_data:
        df = generate_sample_data(200)
        st.info("📊 Displaying sample data for demonstration")
    else:
        df = load_anomalies()
        if df.empty:
            st.warning("⚠️ No anomaly data found. Start the producer and consumer first.")
            st.stop()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_records = len(df)
        st.metric("📡 Total Records", f"{total_records:,}")
    
    with col2:
        if not df.empty and 'anomaly_detected' in df.columns:
            anomaly_count = df['anomaly_detected'].sum()
            anomaly_pct = (anomaly_count / len(df) * 100) if len(df) > 0 else 0
        else:
            anomaly_count = 0
            anomaly_pct = 0
        
        st.metric("⚠️ Anomalies Detected", f"{int(anomaly_count)}", 
                 delta=f"{anomaly_pct:.1f}%")
    
    with col3:
        if not df.empty and 'num_sats' in df.columns:
            avg_sats = df['num_sats'].mean()
        else:
            avg_sats = 0
        st.metric("🛰️ Avg Satellites", f"{avg_sats:.1f}")
    
    with col4:
        if not df.empty and 'snr' in df.columns:
            avg_snr = df['snr'].mean()
            status_class = "ok" if avg_snr >= 30 else ("warning" if avg_snr >= 20 else "critical")
        else:
            avg_snr = 0
            status_class = "ok"
        
        st.markdown(f'<div class="metric-card"><h3 class="{status_class}">📶 Avg SNR</h3>'
                   f'<h2 class="{status_class}">{avg_snr:.1f} dB</h2></div>',
                   unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🗺️ Position Map", 
                                       "⚠️ Anomalies", "📈 Statistics"])
    
    with tab1:
        # SNR Timeline
        st.subheader("Signal Strength Timeline")
        snr_fig = create_snr_timeline(df)
        st.plotly_chart(snr_fig, use_container_width=True)
        
        # Satellite count
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Satellite Count")
            sat_fig = create_satellite_count_chart(df)
            st.plotly_chart(sat_fig, use_container_width=True)
        
        with col2:
            st.subheader("Anomaly Distribution")
            anomaly_fig = create_anomaly_distribution(df)
            st.plotly_chart(anomaly_fig, use_container_width=True)
    
    with tab2:
        st.subheader("🗺️ Position Tracking")
        position_map = create_position_map(df)
        folium_static(position_map, width=1200, height=600)
        
        if not df.empty:
            # Position statistics
            col1, col2, col3 = st.columns(3)
            
            latest = df.sort_values('timestamp').iloc[-1]
            
            with col1:
                st.metric("Latitude", f"{latest['lat']:.6f}°")
            with col2:
                st.metric("Longitude", f"{latest['lon']:.6f}°")
            with col3:
                if 'hdop' in latest and pd.notna(latest['hdop']):
                    st.metric("HDOP", f"{latest['hdop']:.2f}")
    
    with tab3:
        st.subheader("⚠️ Recent Anomalies")
        
        if not df.empty and 'anomaly_detected' in df.columns:
            anomalies = df[df['anomaly_detected'] == True].sort_values('timestamp', ascending=False)
            
            if not anomalies.empty:
                # Display table
                display_cols = ['timestamp', 'satellite_id', 'snr', 'num_sats', 
                              'anomaly_type', 'lat', 'lon']
                available_cols = [col for col in display_cols if col in anomalies.columns]
                
                st.dataframe(
                    anomalies[available_cols].head(50),
                    use_container_width=True,
                    height=400
                )
                
                # Download button
                csv = anomalies.to_csv(index=False)
                st.download_button(
                    label="📥 Download Anomalies CSV",
                    data=csv,
                    file_name=f"anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.success("✅ No anomalies detected!")
        else:
            st.info("No anomaly data available")
    
    with tab4:
        st.subheader("📈 Statistical Analysis")
        
        if not df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**SNR Statistics**")
                if 'snr' in df.columns:
                    st.write(df['snr'].describe())
            
            with col2:
                st.markdown("**Satellite Statistics**")
                if 'num_sats' in df.columns:
                    st.write(df['num_sats'].describe())
            
            # Hourly anomaly trend
            if 'timestamp' in df.columns and 'anomaly_detected' in df.columns:
                df['hour'] = pd.to_datetime(df['timestamp']).dt.floor('H')
                hourly = df.groupby('hour')['anomaly_detected'].sum().reset_index()
                
                fig = px.bar(
                    hourly,
                    x='hour',
                    y='anomaly_detected',
                    title="Anomalies by Hour",
                    labels={'anomaly_detected': 'Number of Anomalies', 'hour': 'Time'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
