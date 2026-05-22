import streamlit as st
import math
import pandas as pd

# ================= 核心计算逻辑 =================
def deg_to_rad(d, m=0, s=0):
    """度分秒转弧度"""
    return math.radians(d + m/60 + s/3600)

def rad_to_dms(rad):
    """弧度转度分秒"""
    decimal_deg = math.degrees(rad) % 360
    d = int(decimal_deg)
    m = int((decimal_deg - d) * 60)
    s = ((decimal_deg - d) * 60 - m) * 60
    return d, m, s

def dms_to_str(d, m, s):
    return f"{d}°{m}'{s:.1f}\""

class ClosedTraverse:
    def __init__(self, start_x, start_y, start_azimuth):
        self.start_x = start_x
        self.start_y = start_y
        self.start_azimuth = deg_to_rad(*start_azimuth)
        self.angles = []
        self.distances = []
        self.n = 0
    
    def add_observation(self, angle_dms, distance):
        self.angles.append(deg_to_rad(*angle_dms))
        self.distances.append(distance)
        self.n += 1
    
    def calculate(self):
        if self.n < 3:
            return None
        
        # 1. 角度闭合差计算与分配
        theoretical_sum = (self.n - 2) * math.pi
        observed_sum = sum(self.angles)
        angle_closure = observed_sum - theoretical_sum
        angle_correction = -angle_closure / self.n
        
        corrected_angles = [angle + angle_correction for angle in self.angles]
        
        # 2. 计算各边方位角
        azimuths = [self.start_azimuth]
        for i in range(self.n - 1):
            next_azimuth = azimuths[i] + math.pi + corrected_angles[i]
            azimuths.append(next_azimuth % (2 * math.pi))
        
        # 3. 坐标增量计算
        delta_x = [self.distances[i] * math.cos(azimuths[i]) for i in range(self.n)]
        delta_y = [self.distances[i] * math.sin(azimuths[i]) for i in range(self.n)]
        
        # 4. 坐标闭合差计算
        sum_dx, sum_dy = sum(delta_x), sum(delta_y)
        linear_closure = math.sqrt(sum_dx**2 + sum_dy**2)
        total_distance = sum(self.distances)
        relative_error = linear_closure / total_distance
        
        # 5. 坐标增量改正
        correction_x = -sum_dx / total_distance
        correction_y = -sum_dy / total_distance
        
        corrected_dx = [delta_x[i] + self.distances[i] * correction_x for i in range(self.n)]
        corrected_dy = [delta_y[i] + self.distances[i] * correction_y for i in range(self.n)]
        
        # 6. 计算各点坐标
        points_x, points_y = [self.start_x], [self.start_y]
        for i in range(self.n):
            points_x.append(points_x[-1] + corrected_dx[i])
            points_y.append(points_y[-1] + corrected_dy[i])
        
        return {
            'angle_closure': math.degrees(angle_closure) * 3600,
            'angle_correction': math.degrees(angle_correction) * 3600,
            'linear_closure': linear_closure,
            'relative_error': f"1/{1/relative_error:.0f}",
            'points': [(points_x[i], points_y[i]) for i in range(self.n + 1)],
            'azimuths': azimuths,
        }

# ================= Streamlit 网页界面 =================
st.set_page_config(page_title="闭合导线平差计算", layout="wide")
st.title("📐 闭合导线平差计算工具")

# 1. 侧边栏：输入起始数据
with st.sidebar:
    st.header("起始数据设置")
    start_x = st.number_input("起始点 X 坐标", value=1000.0)
    start_y = st.number_input("起始点 Y 坐标", value=1000.0)
    
    st.subheader("起始方位角")
    col_d, col_m, col_s = st.columns(3)
    with col_d: az_d = st.number_input("度", value=0, min_value=0, max_value=359)
    with col_m: az_m = st.number_input("分", value=0, min_value=0, max_value=59)
    with col_s: az_s = st.number_input("秒", value=0.0, min_value=0.0, max_value=59.9)

# 2. 主界面：动态输入观测数据
st.header("观测数据录入")
st.info("💡 提示：在下方表格中直接修改或添加观测角度（左角）和边长。")

# 使用 session_state 保存表格数据，防止刷新丢失
if "observations" not in st.session_state:
    st.session_state.observations = pd.DataFrame({
        "角度(度)": [89, 90, 89, 90],
        "角度(分)": [59, 0, 59, 0],
        "角度(秒)": [30, 15, 45, 30],
        "边长(m)": [100.0, 120.0, 110.0, 105.0]
    })

# 动态数据表格
edited_df = st.data_editor(
    st.session_state.observations,
    num_rows="dynamic",  # 允许用户动态增删行
    hide_index=True,
    column_config={
        "角度(度)": st.column_config.NumberColumn(min_value=0, max_value=360),
        "角度(分)": st.column_config.NumberColumn(min_value=0, max_value=59),
        "角度(秒)": st.column_config.NumberColumn(min_value=0, max_value=59),
        "边长(m)": st.column_config.NumberColumn(min_value=0.0),
    }
)

# 3. 计算与结果展示
if st.button("🚀 开始计算平差", type="primary", use_container_width=True):
    # 实例化计算类
    traverse = ClosedTraverse(start_x, start_y, (az_d, az_m, az_s))
    
 # 读取表格数据并添加观测

# --- 修复：同时提供坐标和起始方位角 ---
# 这里的 0 代表起始方位角。如果你有具体的起始方位角数值，请替换这里的 0
# 修改点：把最后一个 0 改成了 (0, 0, 0)
traverse = ClosedTraverse(start_x=0, start_y=0, start_azimuth=(0, 0, 0))
try:
    # 遍历表格的每一行
    for i, row in edited_df.iterrows():
        # 1. 获取单元格数据
        d = row["角度(度)"]
        m = row["角度(分)"]
        s = row["角度(秒)"]
        dist = row["边长(m)"]

        # 2. 安全检查：如果“角度(度)”是空的，直接跳过
        if pd.isna(d):
            continue

        # 3. 数据清洗（防止空值或浮点数导致崩溃）
        deg = int(float(d))
        minute = int(float(m)) if not pd.isna(m) else 0
        sec = int(float(s)) if not pd.isna(s) else 0
        distance = float(dist) if not pd.isna(dist) else 0.0

        # 4. 添加观测数据
        traverse.add_observation(
            (deg, minute, sec),
            distance
        )

except Exception as e:
    st.error(f"发生错误：{e}")
    st.stop()

# 执行计算
results = traverse.calculate()
    
if results:
        st.success("✅ 计算成功！")
        
        # 展示精度指标
        st.subheader("精度评定")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("导线点数", traverse.n)
        col2.metric("角度闭合差", f"{results['angle_closure']:.2f} 秒")
        col3.metric("坐标",0)