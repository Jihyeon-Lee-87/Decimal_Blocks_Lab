# Decimal Blocks 3D — 소수 셋째 자리까지의 덧셈·뺄셈 (Streamlit)

초등 수학 소수 덧셈/뺄셈을 3D 블록(작은 큐브=0.001, 막대=0.01, 판=0.1, 큐브=1)으로
시각화하는 학습 앱입니다. 받아올림/받아내림 과정을 형광 노랑 깜빡임과 말풍선 안내로 보여줍니다.

## 실행 방법 (로컬)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py