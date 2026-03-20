import requests
import json

# 测试登录获取token
def test_login():
    url = "http://localhost:5000/api/auth/login"
    data = {"username": "teacher", "password": "teacher123"}
    response = requests.post(url, json=data)
    print("Login response:")
    print(response.json())
    return response.json().get('access_token')

# 测试辅导员端API
def test_teacher_api(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n=== 测试辅导员端API ===")
    
    # 1. 班级概览
    print("\n1. 班级概览:")
    url = "http://localhost:5000/api/teacher/dashboard"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 2. 学生列表
    print("\n2. 学生列表:")
    url = "http://localhost:5000/api/teacher/students"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 3. 待处理预警
    print("\n3. 待处理预警:")
    url = "http://localhost:5000/api/teacher/warnings"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 4. 重点关注列表
    print("\n4. 重点关注列表:")
    url = "http://localhost:5000/api/teacher/focus"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 5. 本周趋势
    print("\n5. 本周趋势:")
    url = "http://localhost:5000/api/teacher/stats/weekly"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 6. 诈骗类型分布
    print("\n6. 诈骗类型分布:")
    url = "http://localhost:5000/api/teacher/stats/types"
    response = requests.get(url, headers=headers)
    print(response.json())

# 测试管理员端API
def test_admin_api():
    # 先登录获取admin token
    url = "http://localhost:5000/api/auth/login"
    data = {"username": "admin", "password": "admin123"}
    response = requests.post(url, json=data)
    token = response.json().get('access_token')
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n=== 测试管理员端API ===")
    
    # 1. 总览卡片
    print("\n1. 总览卡片:")
    url = "http://localhost:5000/api/admin/overview"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 2. 最新10条预警
    print("\n2. 最新10条预警:")
    url = "http://localhost:5000/api/admin/recent-warnings"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 3. 近7天趋势
    print("\n3. 近7天趋势:")
    url = "http://localhost:5000/api/admin/trends/daily"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 4. 诈骗类型TOP5
    print("\n4. 诈骗类型TOP5:")
    url = "http://localhost:5000/api/admin/trends/types"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 5. 学院排行
    print("\n5. 学院排行:")
    url = "http://localhost:5000/api/admin/trends/colleges"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 6. 热力图数据
    print("\n6. 热力图数据:")
    url = "http://localhost:5000/api/admin/heatmap"
    response = requests.get(url, headers=headers)
    print(response.json())
    
    # 7. 高危画像
    print("\n7. 高危画像:")
    url = "http://localhost:5000/api/admin/portrait"
    response = requests.get(url, headers=headers)
    print(response.json())

if __name__ == "__main__":
    print("测试API开始...")
    token = test_login()
    if token:
        test_teacher_api(token)
        test_admin_api()
    print("\n测试API结束!")
