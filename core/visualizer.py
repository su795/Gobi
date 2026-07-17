import plotly.graph_objects as go
import pandas as pd

class NeoWaveVisualizer:
    """
    글렌 닐리의 네오웨이브 분석 결과를 Plotly를 활용해 시각화하는 클래스
    """
    # def __init__(self, df: pd.DataFrame, monowaves: list):
    #     self.df = df
    #     self.monowaves = monowaves
    #     self.fig = go.Figure()

    # def create_chart(self, title="Glenn Neely's NeoWave Analysis Chart"):
    #     # 1. 원본 캔들/종가 차트 배경 (연한 회색 선)
    #     self.fig.add_trace(go.Scatter(
    #         x=self.df['Date'],
    #         y=self.df['Close'],
    #         mode='lines',
    #         name='Original Price (Close)',
    #         line=dict(color='rgba(200, 200, 200, 0.4)', width=1)
    #     ))
    def __init__(self, df, monowaves):
        self.df = df
        self.monowaves = monowaves
        self.fig = None

    def create_chart(self, title):
        fig = go.Figure()
        # 캔들스틱 추가
        fig.add_trace(go.Candlestick(x=self.df['Date'], open=self.df['Open'], 
                                     high=self.df['High'], low=self.df['Low'], close=self.df['Close'],
                                     name='Market Data'))
        
        # 모노파동 라인 추가
        wave_x = []
        wave_y = []
        for w in self.monowaves:
            wave_x.extend([w.start_time, w.end_time])
            wave_y.extend([w.start_price, w.end_price])
            
        fig.add_trace(go.Scatter(x=wave_x, y=wave_y, mode='lines+markers', 
                                 line=dict(color='cyan', width=2), name='NeoWave Path'))
        
        fig.update_layout(title=title, template='plotly_dark', xaxis_rangeslider_visible=False, height=600)
        self.fig = fig
        return fig

        # 2. 모노파동(Monowave) 연결 선 및 마커 (진한 파란색)
        wave_dates = [self.monowaves[0].start_time] + [w.end_time for w in self.monowaves]
        wave_prices = [self.monowaves[0].start_price] + [w.end_price for w in self.monowaves]
        
        # 툴팁(Hover Text) 생성: 각 파동의 기호와 비율을 한눈에 표시
        hover_texts = ["Start point"]
        for w in self.monowaves:
            text = (f"<b>Wave {w.index:02d}</b><br>"
                    f"Length: {w.price_length:.2f}<br>"
                    f"Retracement: {w.retracement_ratio*100:.1f}%<br>"
                    f"Labels: {', '.join(w.structure_labels)}")
            hover_texts.append(text)

        self.fig.add_trace(go.Scatter(
            x=wave_dates,
            y=wave_prices,
            mode='lines+markers',
            name='Monowave (m0)',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=7, color='#1f77b4'),
            text=hover_texts,
            hoverinfo='text+x+y'
        ))

        # 차트 레이아웃 스타일링
        self.fig.update_layout(
            title=dict(text=f"<b>{title}</b>", font=dict(size=20)),
            xaxis_title="Date / Time",
            yaxis_title="Price",
            template="plotly_dark", # 트레이더들이 좋아하는 다크 테마
            hovermode="closest",
            showlegend=True,
            margin=dict(l=40, r=40, t=60, b=40)
        )

    def highlight_pattern(self, start_wave_idx, end_wave_idx, pattern_name, color='rgba(0, 255, 0, 0.15)', border_color='#00ff00'):
        """
        검증 완료된 충격파동이나 조정파동 영역을 차트 위에 하이라이트 박스로 표시합니다.
        """
        start_time = self.monowaves[start_wave_idx].start_time
        end_time = self.monowaves[end_wave_idx].end_time
        
        # 영역 내 최고가/최저가 계산
        slice_prices = []
        for i in range(start_wave_idx, end_wave_idx + 1):
            slice_prices.extend([self.monowaves[i].start_price, self.monowaves[i].end_price])
        max_p, min_p = max(slice_prices), min(slice_prices)

        # 4각형 하이라이트 영역 추가
        self.fig.add_shape(
            type="rect",
            x0=start_time, y0=min_p,
            x1=end_time, y1=max_p,
            fillcolor=color,
            line=dict(color=border_color, width=2, dash="dash"),
            layer="below"
        )

        # 패턴 이름 텍스트 주석(Annotation) 추가
        self.fig.add_annotation(
            x=start_time + (end_time - start_time) / 2,
            y=max_p,
            text=f"<b>{pattern_name}</b>",
            showarrow=True,
            arrowhead=2,
            ax=0, ay=-30,
            font=dict(color=border_color, size=13),
            bgcolor="rgba(0,0,0,0.7)"
        )

    def show(self):
        """VS Code의 뷰어나 기본 웹 브라우저에서 인터랙티브 차트를 렌더링합니다."""
        self.fig.show()