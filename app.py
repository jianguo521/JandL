import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt

# ================= 全局配置 =================
st.set_page_config(page_title="专业闭合导线平差工具", layout="wide")

# 设置中文字体，防止绘图时中文乱码
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ================= 基础工具函数 =================
def deg_to_rad(d, m=0, s=0):
    """度分秒转弧度"""
    return math.radians(d + m/60 + s/3600)

def rad_to_dms(rad):
    """弧度转度分秒 (返回元组 d, m, s)"""
    decimal_deg = math.degrees(rad) % 360
    d = int(decimal_deg)
    m = int((decimal_deg - d) * 60)
    s = ((decimal_deg - d) * 60 - m) * 60
    return d, m, s

def format_dms(d, m, s):
    """格式化度分秒字符串"""
    return f"{d}°{m}'{s:.1f}\""

# ================= 闭合导线计算核心类 =================
class ClosedTraverse:
    def __init__(self, start_x, start_y, start_azimuth):
        self.start_x = start_x
        self.start_y = start_y
        # 起始方位角转为弧度
        self.start_azimuth = deg_to_rad(*start_azimuth)
        self.angles_dms = []  # 原始角度
        self.distances = []   # 边长
        self.n = 0            # 边数

    def add_observation(self, angle_dms, distance):
        self.angles_dms.append(angle_dms)
        self.distances.append(distance)
        self.n += 1

    def calculate(self):
        if self.n < 3:
            return None

        # 1. 角度闭合差计算
        theoretical_sum_rad = (self.n - 2) * math.pi
        observed_angles_rad = [deg_to_rad(*ang) for ang in self.angles_dms]
        observed_sum_rad = sum(observed_angles_rad)

        angle_closure_rad = observed_sum_rad - theoretical_sum_rad
        angle_correction_rad = -angle_closure_rad / self.n

        # 改正后的角度
        corrected_angles_rad = [a + angle_correction_rad for a in observed_angles_rad]

        # 2. 推算各边方位角
        azimuths_rad = [self.start_azimuth]
        for i in range(self.n):
            # 左角公式：α前 = α后 + 180 + β左
            next_az = azimuths_rad[-1] + math.pi + corrected_angles_rad[i]
            azimuths_rad.append(next_az % (2 * math.pi))

        # 3. 坐标增量计算 (未改正)
        delta_x_prime = []
        delta_y_prime = []
        for i in range(self.n):
            dx = self.distances[i] * math.cos(azimuths_rad[i])
            dy = self.distances[i] * math.sin(azimuths_rad[i])
            delta_x_prime.append(dx)
            delta_y_prime.append(dy)

        # 4. 精度评定
        sum_dx = sum(delta_x_prime)
        sum_dy = sum(delta_y_prime)
        linear_closure = math.sqrt(sum_dx**2 + sum_dy**2)
        total_distance = sum(self.distances)
        relative_error_val = linear_closure / total_distance if total_distance != 0 else 0

        # 5. 坐标增量改正 (按边长成正比分配)
        correction_x_rate = -sum_dx / total_distance if total_distance != 0 else 0
        correction_y_rate = -sum_dy / total_distance if total_distance != 0 else 0

        corrected_dx = [delta_x_prime[i] + self.distances[i] * correction_x_rate for i in range(self.n)]
        corrected_dy = [delta_y_prime[i] + self.distances[i] * correction_y_rate for i in range(self.n)]

        # 6. 坐标推算
        points_x = [self.start_x]
        points_y = [self.start_y]
        for i in range(self.n):
            points_x.append(points_x[-1] + corrected_dx[i])
            points_y.append(points_y[-1] + corrected_dy[i])

        # --- 整理表格数据 ---
        table_data = []
        for i in range(self.n):
            obs_dms = self.angles_dms[i]
            cor_dms = rad_to_dms(corrected_angles_rad[i])
            az_dms = rad_to_dms(azimuths_rad[i])

            table_data.append({
                "点号": f"P{i+1}",
                "观测左角": format_dms(*obs_dms),
                "改正后角度": format_dms(*cor_dms),
                "坐标方位角": format_dms(*az_dms),
                "边长(m)": round(self.distances[i], 3),
                "Δx'(m)": round(delta_x_prime[i], 3),
                "Δy'(m)": round(delta_y_prime[i], 3),
                "改正Δx(m)": round(corrected_dx[i], 3),
                "改正Δy(m)": round(corrected_dy[i], 3),
                "X坐标(m)": round(points_x[i+1], 3),
                "Y坐标(m)": round(points_y[i+1], 3),
            })

        # 添加闭合回起点的行
        table_data.append({
            "点号": f"P1(闭合)",
            "观测左角": "-", "改正后角度": "-", "坐标方位角": "-", "边长(m)": "-",
            "Δx'(m)": "-", "Δy'(m)": "-", "改正Δx(m)": "-", "改正Δy(m)": "-",
            "X坐标(m)": round(points_x[-1], 3),
            "Y坐标(m)": round(points_y[-1], 3),
        })

        return {
            "table_data": table_data,
            "coords_x": points_x,
            "coords_y": points_y,
            "angle_closure_sec": round(math.degrees(angle_closure_rad) * 3600, 1),
            "linear_closure": round(linear_closure, 3),
            "relative_error": f"1/{int(1/relative_error_val)}" if relative_error_val > 0 else "无穷大",
            "sum_distance": round(total_distance, 3),
            "fx": round(sum_dx, 3),
            "fy": round(sum_dy, 3)
        }
# ================= Streamlit 界面逻辑 =================
st.title("📐 专业闭合导线内业计算与展点")

with st.sidebar:
    st.header("📍 起始数据")
    start_x = st.number_input("起始点 X (m)", value=500.000, step=0.001)
    start_y = st.number_input("起始点 Y (m)", value=500.000, step=0.001)

    st.subheader("起始边方位角")
    c1, c2, c3 = st.columns(3)
    with c1: az_d = st.number_input("度", value=0, min_value=0, max_value=359)
    with c2: az_m = st.number_input("分", value=0, min_value=0, max_value=59)
    with c3: az_s = st.number_input("秒", value=0.0, min_value=0.0, max_value=59.9)

st.header("📝 观测数据录入")
st.info("💡 提示：直接在下方表格修改数据，支持动态增删行。请确保至少输入3个测站。")

# 初始化 Session State
if "observations" not in st.session_state:
    st.session_state.observations = pd.DataFrame({
        "角度(度)": [89, 90, 89, 92],
        "角度(分)": [59, 0, 59, 0],
        "角度(秒)": [30.0, 15.0, 45.0, 10.0],
        "边长(m)": [100.0, 120.0, 110.0, 105.0]
    })

# 动态编辑表格
edited_df = st.data_editor(
    st.session_state.observations,
    num_rows="dynamic",
    hide_index=True,
    column_config={
        "角度(度)": st.column_config.NumberColumn(min_value=0, max_value=360, step=1),
        "角度(分)": st.column_config.NumberColumn(min_value=0, max_value=59, step=1),
        "角度(秒)": st.column_config.NumberColumn(min_value=0.0, max_value=59.9, step=0.1),
        "边长(m)": st.column_config.NumberColumn(min_value=0.0, step=0.001),
    }
)
if st.button("🚀 开始计算并生成成果表", type="primary", use_container_width=True):
    traverse = ClosedTraverse(start_x, start_y, (az_d, az_m, az_s))

    try:
        for _, row in edited_df.iterrows():
            d = row["角度(度)"]
            m = row["角度(分)"] if not pd.isna(row["角度(分)"]) else 0
            s = row["角度(秒)"] if not pd.isna(row["角度(秒)"]) else 0.0
            dist = row["边长(m)"] if not pd.isna(row["边长(m)"]) else 0.0

            if pd.isna(d) or dist <= 0: continue
            traverse.add_observation((int(d), int(m), float(s)), float(dist))
    except Exception as e:
        st.error(f"数据读取错误：{str(e)}")
        st.stop()

    results = traverse.calculate()
    if not results:
        st.warning("⚠️ 观测数据不足（至少需要3条边），无法进行平差计算。")
        st.stop()

    # --- 结果展示区 ---
    st.success("✅ 计算完成！")

    # 1. 精度指标卡片
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("导线全长", f"{results['sum_distance']} m")
    col2.metric("角度闭合差", f"{results['angle_closure_sec']} 秒")
    col3.metric("坐标闭合差", f"f={results['linear_closure']} m")
    col4.metric("相对闭合差", results['relative_error'])

    # 2. 导线略图
    st.subheader("🗺️ 导线略图")
    fig, ax = plt.subplots(figsize=(10, 8))
    x_coords = results['coords_x']
    y_coords = results['coords_y']

    # 绘制导线边
    ax.plot(x_coords, y_coords, 'b-o', linewidth=2, markersize=8, label='导线边')

    # 标注点号
    for i, (x, y) in enumerate(zip(x_coords[:-1], y_coords[:-1])):
        ax.annotate(f'P{i+1}', (x, y), textcoords="offset points", xytext=(10,10), fontsize=12, color='red')

    # 绘制闭合差示意线 (红色虚线)
    ax.plot([x_coords[-1], x_coords[0]], [y_coords[-1], y_coords[0]], 'r--', alpha=0.7, label=f'闭合差 f={results["linear_closure"]}m')

    ax.set_xlabel("X 坐标 (m)")
    ax.set_ylabel("Y 坐标 (m)")
    ax.set_title("闭合导线平面示意图")
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()
    ax.set_aspect('equal') # 保持纵横比一致，真实反映形状
    st.pyplot(fig)

    # 3. 详细计算表
    st.subheader("📋 闭合导线计算表")
    df_res = pd.DataFrame(results['table_data'])
    st.dataframe(df_res, use_container_width=True, hide_index=True)

    # 4. 导出功能
    csv = df_res.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下载计算结果 (CSV)",
        data=csv,
        file_name="traverse_result.csv",
        mime="text/csv"
    )