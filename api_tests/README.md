# 个人记账 API 自动化

独立 HTTP 集成测试，针对运行中的 Django REST Framework 服务。仅对专用测试环境运行；用例会创建、修改、逻辑删除数据，并调用余额校准接口清理测试账户。

## 安装和运行

```powershell
python -m pip install -r api_tests/requirements.txt
$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:API_TEST_USERNAME = "测试用户A"
$env:API_TEST_PASSWORD = "密码"
$env:API_TEST_USERNAME_2 = "测试用户B" # 越权用例必需
$env:API_TEST_PASSWORD_2 = "密码"
python -m pytest api_tests -q --junitxml=api_tests/results.xml
```

未配置第二个用户时，越权用例会明确标记为 skipped。未配置基本环境变量时，集成测试也会 skipped，不会误连默认环境。

## 覆盖范围

- 正常链路：登录、账户创建、账单创建/修改/删除、余额联动。
- 异常链路：匿名访问、错误密码、无效 Token、非法金额、余额不足、分类类型不匹配、非法日期范围、跨用户读写。

`pytest -m smoke` 运行核心链路；`pytest -m negative` 运行异常用例。测试失败时会显示 HTTP 状态和统一响应体。账号应为专用测试账号，且测试环境中的余额校准记录允许留存。
