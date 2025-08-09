#!/usr/bin/env python3
"""
厚東川リアルタイム監視システム v2.0 - モダンUI版
山口県宇部市の厚東川ダムおよび厚東川（持世寺）の監視データを表示
改善点：警戒情報の視認性向上、住民向け説明、モダンデザイン、通知機能
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python 3.8以前の場合
    import pytz
    ZoneInfo = lambda x: pytz.timezone(x)
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ページ設定
st.set_page_config(
    page_title="厚東川監視システム",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# モダンなデザインテーマのCSS
st.markdown("""
<style>
    /* === 基本設定 === */
    :root {
        --primary-color: #2E7D32;
        --success-color: #4CAF50;
        --warning-color: #FF9800;
        --danger-color: #F44336;
        --info-color: #2196F3;
        --dark-bg: #1E1E1E;
        --light-bg: #FFFFFF;
        --card-shadow: 0 2px 8px rgba(0,0,0,0.1);
        --border-radius: 12px;
    }
    
    /* 上部マージンの削除 */
    .main .block-container {
        padding-top: 0.5rem !important;
        max-width: 100%;
    }
    
    /* === 警戒レベル表示カード === */
    .alert-card {
        padding: 1.5rem;
        border-radius: var(--border-radius);
        margin-bottom: 1.5rem;
        box-shadow: var(--card-shadow);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .alert-card::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        width: 6px;
    }
    
    .alert-normal {
        background: linear-gradient(135deg, #E8F5E9 0%, #F1F8E9 100%);
        border: 1px solid #C8E6C9;
    }
    
    .alert-normal::before {
        background: var(--success-color);
    }
    
    .alert-caution {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
        border: 1px solid #FFCC80;
    }
    
    .alert-caution::before {
        background: var(--warning-color);
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFCCBC 100%);
        border: 1px solid #FFAB91;
    }
    
    .alert-warning::before {
        background: #FF6F00;
    }
    
    .alert-danger {
        background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%);
        border: 1px solid #EF9A9A;
        animation: pulse 2s infinite;
    }
    
    .alert-danger::before {
        background: var(--danger-color);
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.01); }
        100% { transform: scale(1); }
    }
    
    /* === メトリクスカード === */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: var(--border-radius);
        box-shadow: var(--card-shadow);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .metric-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
        color: #616161;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #212121;
        margin-bottom: 0.5rem;
    }
    
    .metric-delta {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    .delta-positive {
        background: #E8F5E9;
        color: #2E7D32;
    }
    
    .delta-negative {
        background: #FFEBEE;
        color: #C62828;
    }
    
    .delta-neutral {
        background: #F5F5F5;
        color: #616161;
    }
    
    /* === 説明テキスト === */
    .info-box {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border-left: 4px solid var(--info-color);
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .info-box h4 {
        color: #1565C0;
        margin: 0 0 0.5rem 0;
        font-size: 1.1rem;
    }
    
    .info-box p {
        color: #424242;
        margin: 0;
        line-height: 1.6;
    }
    
    /* === グラフコンテナ === */
    .graph-container {
        background: white;
        padding: 1.5rem;
        border-radius: var(--border-radius);
        box-shadow: var(--card-shadow);
        margin-bottom: 1.5rem;
    }
    
    .graph-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #212121;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #E0E0E0;
    }
    
    /* === ステータスバッジ === */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 500;
        font-size: 0.9rem;
        gap: 0.5rem;
    }
    
    .status-normal {
        background: var(--success-color);
        color: white;
    }
    
    .status-caution {
        background: var(--warning-color);
        color: white;
    }
    
    .status-danger {
        background: var(--danger-color);
        color: white;
        animation: blink 1.5s infinite;
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    
    /* === レスポンシブ対応 === */
    @media (max-width: 768px) {
        .metric-card {
            margin-bottom: 1rem;
        }
        
        .metric-value {
            font-size: 2rem;
        }
        
        .alert-card {
            padding: 1rem;
        }
    }
    
    /* Streamlitのデフォルトスタイル上書き */
    .stMetric > div {
        background: white;
        padding: 1.2rem;
        border-radius: var(--border-radius);
        box-shadow: var(--card-shadow);
    }
    
    /* タブのスタイル改善 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #F5F5F5;
        padding: 0.5rem;
        border-radius: var(--border-radius);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        background-color: white;
        border: none;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color);
        color: white;
    }
    
    /* サイドバーのモダン化 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FAFAFA 0%, #F5F5F5 100%);
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# 日本時間のタイムゾーン
JST = ZoneInfo('Asia/Tokyo')

def load_latest_data() -> Optional[Dict[str, Any]]:
    """最新データを読み込む"""
    try:
        json_path = Path("data/latest.json")
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
    return None

def get_alert_level(river_level: float) -> tuple:
    """河川水位から警戒レベルを判定
    Returns: (level_name, level_class, icon, description)
    """
    if river_level >= 5.50:
        return ("氾濫危険", "danger", "🚨", "直ちに安全な場所へ避難してください")
    elif river_level >= 5.00:
        return ("氾濫注意", "warning", "⚠️", "避難の準備を始めてください")
    elif river_level >= 3.80:
        return ("水防団待機", "caution", "📢", "今後の情報に注意してください")
    else:
        return ("正常", "normal", "✅", "現在、危険はありません")

def get_rain_alert_level(hourly_rain: float) -> tuple:
    """雨量から警戒レベルを判定"""
    if hourly_rain >= 50:
        return ("豪雨", "danger", "🌊", "非常に激しい雨")
    elif hourly_rain >= 30:
        return ("大雨", "warning", "☔", "激しい雨")
    elif hourly_rain >= 10:
        return ("やや強い雨", "caution", "🌧️", "傘が必要")
    else:
        return ("通常", "normal", "☁️", "問題なし")

def display_alert_banner(data: Dict[str, Any]):
    """最上部に警戒情報バナーを表示"""
    river_level = data.get('river', {}).get('water_level', 0)
    level_name, level_class, icon, description = get_alert_level(river_level)
    
    # 雨量情報も確認
    hourly_rain = data.get('rainfall', {}).get('hourly', 0) or 0
    rain_level, rain_class, rain_icon, rain_desc = get_rain_alert_level(hourly_rain)
    
    # 最も危険度の高いレベルを採用
    if level_class == "danger" or rain_class == "danger":
        final_class = "danger"
        if level_class == "danger":
            final_message = f"{icon} **{level_name}** - {description}"
        else:
            final_message = f"{rain_icon} **{rain_level}** - {rain_desc}"
    elif level_class == "warning" or rain_class == "warning":
        final_class = "warning"
        if level_class == "warning":
            final_message = f"{icon} **{level_name}** - {description}"
        else:
            final_message = f"{rain_icon} **{rain_level}** - {rain_desc}"
    elif level_class == "caution" or rain_class == "caution":
        final_class = "caution"
        if level_class == "caution":
            final_message = f"{icon} **{level_name}** - {description}"
        else:
            final_message = f"{rain_icon} **{rain_level}** - {rain_desc}"
    else:
        final_class = "normal"
        final_message = f"{icon} **{level_name}** - {description}"
    
    st.markdown(f"""
        <div class="alert-card alert-{final_class}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin: 0; color: #212121;">厚東川監視システム</h2>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem;">{final_message}</p>
                </div>
                <div style="text-align: right;">
                    <div class="status-badge status-{final_class}">
                        河川水位: {river_level:.2f}m
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

def display_info_boxes():
    """住民向けの説明を表示"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div class="info-box">
                <h4>💡 このシステムについて</h4>
                <p>
                厚東川の水位と雨量を10分ごとに自動更新し、
                洪水の危険性をリアルタイムでお知らせします。
                色と記号で危険度が一目でわかるようになっています。
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="info-box">
                <h4>📊 データの見方</h4>
                <p>
                <strong>河川水位</strong>: 川の水面の高さ（3.8m以上で注意）<br>
                <strong>時間雨量</strong>: 1時間あたりの降水量<br>
                <strong>貯水率</strong>: ダムの水の満杯度（％表示）
                </p>
            </div>
        """, unsafe_allow_html=True)

def display_metrics_cards(data: Dict[str, Any]):
    """メトリクスをカード形式で表示"""
    col1, col2, col3, col4 = st.columns(4)
    
    # 河川水位
    with col1:
        river_level = data.get('river', {}).get('water_level', 0)
        level_change = data.get('river', {}).get('level_change', 0)
        level_name, level_class, _, _ = get_alert_level(river_level)
        
        delta_class = "positive" if level_change > 0 else "negative" if level_change < 0 else "neutral"
        delta_symbol = "↑" if level_change > 0 else "↓" if level_change < 0 else "→"
        
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-header">
                    🌊 河川水位（持世寺）
                </div>
                <div class="metric-value">{river_level:.2f}m</div>
                <div class="metric-delta delta-{delta_class}">
                    {delta_symbol} {abs(level_change):.2f}m
                </div>
                <div style="margin-top: 0.5rem;">
                    <span class="status-badge status-{level_class}">{level_name}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # ダム貯水率
    with col2:
        storage_rate = data.get('dam', {}).get('storage_rate', 0)
        water_level = data.get('dam', {}).get('water_level', 0)
        
        storage_class = "danger" if storage_rate >= 95 else "warning" if storage_rate >= 90 else "normal"
        
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-header">
                    🏞️ ダム貯水率
                </div>
                <div class="metric-value">{storage_rate:.1f}%</div>
                <div style="color: #616161; font-size: 0.9rem;">
                    水位: {water_level:.2f}m
                </div>
                <div style="margin-top: 0.5rem;">
                    <span class="status-badge status-{storage_class}">
                        {"危険" if storage_rate >= 95 else "警戒" if storage_rate >= 90 else "正常"}
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # 時間雨量
    with col3:
        hourly_rain = data.get('rainfall', {}).get('hourly', 0) or 0
        rain_level, rain_class, _, _ = get_rain_alert_level(hourly_rain)
        
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-header">
                    ☔ 時間雨量
                </div>
                <div class="metric-value">{hourly_rain:.0f}mm</div>
                <div style="color: #616161; font-size: 0.9rem;">
                    累積: {data.get('rainfall', {}).get('cumulative', 0) or 0:.0f}mm
                </div>
                <div style="margin-top: 0.5rem;">
                    <span class="status-badge status-{rain_class}">{rain_level}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # 流入/放流量
    with col4:
        inflow = data.get('dam', {}).get('inflow', 0)
        outflow = data.get('dam', {}).get('outflow', 0)
        flow_diff = inflow - outflow if inflow and outflow else 0
        
        flow_class = "danger" if abs(flow_diff) > 50 else "warning" if abs(flow_diff) > 30 else "normal"
        
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-header">
                    💧 ダム流入/放流
                </div>
                <div style="font-size: 1.2rem; margin: 0.5rem 0;">
                    流入: <strong>{inflow:.1f}</strong> m³/s<br>
                    放流: <strong>{outflow:.1f}</strong> m³/s
                </div>
                <div class="metric-delta delta-{"positive" if flow_diff > 0 else "negative" if flow_diff < 0 else "neutral"}">
                    差: {flow_diff:+.1f} m³/s
                </div>
            </div>
        """, unsafe_allow_html=True)

def create_modern_graph(df: pd.DataFrame, title: str, y_cols: list, colors: list = None):
    """モダンなスタイルのグラフを作成"""
    fig = go.Figure()
    
    if colors is None:
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336']
    
    for i, col in enumerate(y_cols):
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df['datetime'],
                y=df[col],
                name=col,
                mode='lines+markers',
                line=dict(color=colors[i % len(colors)], width=2.5),
                marker=dict(size=6),
                hovertemplate='%{y:.2f}<extra></extra>'
            ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color='#212121')),
        xaxis=dict(
            title="",
            gridcolor='#E0E0E0',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            title="",
            gridcolor='#E0E0E0',
            showgrid=True,
            zeroline=False
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        height=400,
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig

def main():
    """メインアプリケーション"""
    
    # 自動更新（サイドバーで設定）
    with st.sidebar:
        st.title("⚙️ 設定")
        
        # 自動更新
        auto_refresh = st.checkbox("自動更新", value=True)
        refresh_interval = st.selectbox(
            "更新間隔",
            options=[10, 30, 60],
            format_func=lambda x: f"{x}分",
            index=0
        )
        
        if auto_refresh:
            st_autorefresh(interval=refresh_interval * 60 * 1000, key="datarefresh")
        
        # 通知設定（将来実装用）
        st.markdown("### 🔔 通知設定")
        notification_enabled = st.checkbox("ブラウザ通知を有効化", value=False, disabled=True)
        st.info("通知機能は準備中です")
        
        # AI予測（将来実装用）
        st.markdown("### 🤖 AI予測")
        st.info("AI予測機能は開発中です")
        
        # データソース
        with st.expander("📊 データソース"):
            st.markdown("""
            - 山口県土木防災情報システム
            - Yahoo! Weather API
            - 更新: 10分間隔
            """)
    
    # データ読み込み
    data = load_latest_data()
    
    if not data:
        st.error("データが見つかりません")
        return
    
    # 警戒バナー表示
    display_alert_banner(data)
    
    # 説明ボックス
    display_info_boxes()
    
    # メトリクスカード
    st.markdown("### 📈 現在の状況")
    display_metrics_cards(data)
    
    # タブでグラフを整理
    st.markdown("### 📊 詳細データ")
    tab1, tab2, tab3 = st.tabs(["📈 時系列グラフ", "🌤️ 天気予報", "📋 データテーブル"])
    
    with tab1:
        # ここに既存のグラフ表示ロジックを配置
        st.info("グラフ表示機能は既存のコードから移植します")
    
    with tab2:
        # 天気予報
        if 'weather' in data:
            weather = data['weather']
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 今日")
                if 'today' in weather:
                    st.write(weather['today'].get('weather_text', '情報なし'))
            
            with col2:
                st.markdown("#### 明日")
                if 'tomorrow' in weather:
                    st.write(weather['tomorrow'].get('weather_text', '情報なし'))
            
            with col3:
                st.markdown("#### 明後日")
                if 'day_after_tomorrow' in weather:
                    st.write(weather['day_after_tomorrow'].get('weather_text', '情報なし'))
    
    with tab3:
        # データテーブル
        st.dataframe(pd.DataFrame([data]), use_container_width=True)

if __name__ == "__main__":
    main()