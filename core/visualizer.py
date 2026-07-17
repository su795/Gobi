import plotly.graph_objects as go
import pandas as pd

class NeoWaveVisualizer:
    def __init__(self, df: pd.DataFrame, monowaves: list):
        self.df = df
        self.monowaves = monowaves
        self.fig = None

    def create_chart(self, title: str = "NeoWave AI Master Chart") -> go.Figure:
        self.fig = go.Figure()

        # 1. 트레이딩뷰 고유 색상의 캔들스틱 차트 작도
        self.fig.add_trace(go.Candlestick(
            x=self.df['Date'],
            open=self.df['Open'],
            high=self.df['High'],
            low=self.df['Low'],
            close=self.df['Close'],
            name='Market Price',
            increasing_line_color='#089981',  # 트레이딩뷰 상승 캔들 (청록)
            increasing_fillcolor='#089981',
            decreasing_line_color='#f23645',  # 트레이딩뷰 하락 캔들 (적색)
            decreasing_fillcolor='#f23645'
        ))

        # 2. 글렌 닐리 모노파동 라인 (트레이딩뷰 스타일 Cyan 라인)
        wave_x, wave_y = [], []
        for w in self.monowaves:
            wave_x.extend([w.start_time, w.end_time, None])
            wave_y.extend([w.start_price, w.end_price, None])

        self.fig.add_trace(go.Scatter(
            x=wave_x, y=wave_y,
            mode='lines',
            line=dict(color='#00bcd4', width=2),  # 선명한 형광 청록색
            name='Monowave Path',
            hoverinfo='skip'
        ))

        # 3. 파동 꼭지점마다 트레이딩뷰 스타일 라벨(:3, :5 등) 부착
        for w in self.monowaves:
            label_text = ", ".join(w.structure_labels) if hasattr(w, 'structure_labels') and w.structure_labels else ""
            if label_text:
                is_top = (w.direction == 1)
                self.fig.add_annotation(
                    x=w.end_time,
                    y=w.end_price,
                    text=f"<b>{label_text}</b>",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=1,
                    arrowcolor="#ffe500" if is_top else "#00ffff",
                    ax=0, ay=-25 if is_top else 25,
                    font=dict(color="#131722", size=10),
                    bgcolor="#ffe500" if is_top else "#00ffff",
                    bordercolor="#ffffff",
                    borderwidth=1,
                    borderpad=3
                )

        # 4. 트레이딩뷰 프로(Pro) 다크 테마 레이아웃 및 십자선(Crosshair) 설정
        self.fig.update_layout(
            title=dict(text=f"<b>{title}</b>", font=dict(color="#d1d4dc", size=18)),
            paper_bgcolor="#131722",  # 트레이딩뷰 메인 배경색
            plot_bgcolor="#131722",   # 트레이딩뷰 차트 배경색
            height=650,
            margin=dict(l=10, r=60, t=50, b=20),
            showlegend=False,
            xaxis_rangeslider_visible=False,  # 하단 슬라이더 제거로 깔끔한 화면 유지
            hovermode="x unified",            # 트레이딩뷰 스타일 일괄 호버 정보
            dragmode="pan"                    # 기본 마우스 드래그를 '화면 이동(Pan)'으로 설정
        )

        # X축 (시간축) 트레이딩뷰 눈금 스타일
        self.fig.update_xaxes(
            gridcolor="#1f293d",
            showgrid=True,
            zeroline=False,
            color="#787b86",
            showline=True,
            linewidth=1,
            linecolor="#2b2b43",
            spikemode="across",
            spikesnap="cursor",
            showspikes=True,
            spikethickness=1,
            spikecolor="#787b86"
        )

        # Y축 (가격축) 트레이딩뷰 눈금 스타일 (우측 배치)
        self.fig.update_yaxes(
            gridcolor="#1f293d",
            showgrid=True,
            zeroline=False,
            color="#787b86",
            side="right",        # 트레이딩뷰처럼 가격을 오른쪽 화면에 배치
            showline=True,
            linewidth=1,
            linecolor="#2b2b43",
            spikemode="across",
            spikesnap="cursor",
            showspikes=True,
            spikethickness=1,
            spikecolor="#787b86"
        )

        return self.fig

    # 상위 차수 폴리파동/멀티파동 하이라이트 박스 기능
    def highlight_pattern(self, start_idx: int, end_idx: int, label: str, color: str = 'rgba(0, 255, 100, 0.1)', border_color: str = '#00ff66'):
        if start_idx >= len(self.monowaves) or end_idx >= len(self.monowaves):
            return

        start_time = self.monowaves[start_idx].start_time
        end_time = self.monowaves[end_idx].end_time

        # 해당 기간 내 고점/저점 탐색
        slice_waves = self.monowaves[start_idx:end_idx+1]
        max_p = max(max(w.start_price, w.end_price) for w in slice_waves)
        min_p = min(min(w.start_price, w.end_price) for w in slice_waves)

        self.fig.add_shape(
            type="rect",
            x0=start_time, y0=min_p, x1=end_time, y1=max_p,
            fillcolor=color, line=dict(color=border_color, width=1.5, dash="dash"),
            layer="below"
        )

        self.fig.add_annotation(
            x=start_time, y=max_p,
            text=f"<b>{label}</b>",
            showarrow=False,
            xanchor="left", yanchor="bottom",
            font=dict(color=border_color, size=11),
            bgcolor="rgba(19, 23, 34, 0.7)"
        )