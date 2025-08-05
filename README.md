# WeChatPadPro 微信登录验证码系统

## 项目概述

WeChatPadPro是一个功能强大的微信登录验证码处理系统，支持自动验证码提交、RabbitMQ消息队列、多账号管理等功能。

## 主要功能

### ✅ 核心功能
- **自动验证码处理**: 无需手动获取ticket和data62，系统自动处理
- **二维码登录**: 支持绕过验证码的二维码获取
- **状态检测**: 实时检测扫码和登录状态
- **RabbitMQ集成**: 异步消息处理和状态推送
- **多账号管理**: 支持多设备同时登录
- **自动Token刷新**: 自动维护登录状态

### 🔧 技术特性
- **连接管理**: 自动连接池和健康检查
- **断线重连**: 智能重连机制
- **消息持久化**: 确保消息不丢失
- **性能监控**: 实时统计和告警
- **安全验证**: 完善的授权和参数验证

## 快速开始

### 1. 环境要求

- Go 1.16+
- Redis 6.0+
- RabbitMQ 3.8+
- MySQL 5.7+

### 2. 安装配置

```bash
# 克隆项目
git clone https://github.com/your-repo/WeChatPadPro.git
cd WeChatPadPro

# 安装依赖
go mod tidy

# 配置环境
cp config/application.example.yml config/application.yml
# 编辑配置文件
```

### 3. 配置文件

```yaml
# application.yml
server:
  port: 8080
  mode: debug

redis:
  host: localhost
  port: 6379
  password: ""
  db: 0

rabbitmq:
  enabled: true
  url: "amqp://user:pass@localhost:5672/"
  exchange: "wx_sys_exchangeName"
  heartbeat: 4s
  skipRedis: true

mysql:
  host: localhost
  port: 3306
  username: root
  password: password
  database: wechat_pad_pro
```

### 4. 启动服务

```bash
# 开发环境
go run main.go

# 生产环境
go build -o wechatpadpro main.go
./wechatpadpro
```

## 登录验证码使用流程

### 完整流程示例

#### 步骤1: 获取二维码
```bash
curl -X POST "http://localhost:8080/api/login/qr/newx" \
  -H "Content-Type: application/json" \
  -d '{
    "deviceName": "iPhone",
    "deviceId": "123456789"
  }'
```

**响应**:
```json
{
  "code": 200,
  "success": true,
  "message": "获取二维码成功",
  "data": {
    "uuid": "abc123def456",
    "qrcode": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "qrcodeUrl": "https://login.weixin.qq.com/qrcode/abc123def456",
    "expireTime": 300,
    "deviceId": "123456789",
    "data62": "base64encodeddata..."
  }
}
```

#### 步骤2: 提交验证码
```bash
curl -X POST "http://localhost:8080/api/login/AutoVerificationcode" \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "abc123def456",
    "code": "123456"
  }'
```

**响应**:
```json
{
  "code": 200,
  "success": true,
  "message": "验证码提交成功",
  "data": {
    "loginResult": "success",
    "userInfo": {
      "wxid": "wxid_abc123",
      "nickname": "用户昵称",
      "avatar": "头像URL"
    }
  }
}
```

#### 步骤3: 检测登录状态
```bash
curl -X GET "http://localhost:8080/api/login/CheckLoginStatus?key=abc123def456"
```

**响应**:
```json
{
  "code": 200,
  "success": true,
  "message": "扫码状态",
  "data": {
    "status": "scanned",
    "userInfo": {
      "wxid": "wxid_abc123",
      "nickname": "用户昵称"
    }
  }
}
```

## API 接口文档

### 核心接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/login/qr/newx` | POST | 获取微信登录二维码（绕过验证码） |
| `/api/login/AutoVerificationcode` | POST | 自动处理验证码提交 |
| `/api/login/CheckLoginStatus` | GET | 检测扫码状态 |
| `/api/login/GetLoginStatus` | GET | 获取在线状态 |
| `/api/login/LogOutRequest` | POST | 退出登录 |

### 错误码说明

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 200 | 成功 | - |
| -3 | 需要提交验证码 | 使用AutoVerificationcode接口 |
| 300 | 状态不存在 | 重新获取二维码 |
| 400 | 参数错误 | 检查请求参数 |
| 401 | 授权失败 | 检查授权码 |
| 500 | 系统错误 | 查看服务器日志 |

## RabbitMQ 配置

### 消息类型

1. **登录状态变更**: `login.status.change`
2. **验证码提交**: `verification.submit`
3. **二维码状态**: `qrcode.status`
4. **系统事件**: `system.event`

### 消息格式示例

```json
{
  "type": "login_status_change",
  "uuid": "abc123def456",
  "status": "online",
  "timestamp": 1640995200,
  "account": {
    "uuid": "abc123def456",
    "wxid": "wxid_abc123",
    "nickname": "用户昵称",
    "state": 1
  }
}
```

### 连接管理

- **自动重连**: 连接断开时自动重连
- **心跳检测**: 4秒心跳间隔
- **健康检查**: 10秒无心跳认为连接不健康
- **消息持久化**: 确保消息不丢失

## 开发指南

### 项目结构

```
WeChatPadPro/
├── api/                    # API接口层
│   ├── controller/        # 控制器
│   ├── service/          # 业务逻辑
│   ├── middleware/       # 中间件
│   └── router/           # 路由配置
├── db/                   # 数据库层
│   ├── redis.go         # Redis操作
│   └── rabbitMq.go      # RabbitMQ操作
├── docs/                 # 文档
├── config/               # 配置文件
└── main.go              # 主程序
```

### 开发环境

```bash
# 安装开发工具
go install github.com/swaggo/swag/cmd/swag@latest

# 生成API文档
swag init

# 运行测试
go test ./...

# 代码格式化
go fmt ./...
```

### 部署说明

#### Docker 部署

```yaml
# docker-compose.yml
version: '3.8'
services:
  wechatpadpro:
    build: .
    ports:
      - "8080:8080"
    environment:
      - REDIS_HOST=redis
      - RABBITMQ_URL=amqp://user:pass@rabbitmq:5672/
    depends_on:
      - redis
      - rabbitmq
      - mysql

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: secure_password

  mysql:
    image: mysql:5.7
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: wechat_pad_pro
```

#### 生产环境

```bash
# 构建镜像
docker build -t wechatpadpro .

# 运行容器
docker run -d \
  --name wechatpadpro \
  -p 8080:8080 \
  -v /path/to/config:/app/config \
  -v /path/to/logs:/app/logs \
  wechatpadpro
```

## 监控和日志

### 日志配置

```yaml
logging:
  level: info
  format: json
  output: file
  file: logs/wechatpadpro.log
  maxSize: 100MB
  maxBackups: 10
  maxAge: 30d
```

### 监控指标

- 登录成功率
- 验证码提交成功率
- API响应时间
- RabbitMQ消息队列状态
- 连接池使用情况

### 告警配置

```yaml
alerts:
  login_success_rate:
    threshold: 0.95
    window: 5m
  api_response_time:
    threshold: 1000ms
    window: 1m
  rabbitmq_queue_size:
    threshold: 1000
    window: 1m
```

## 安全说明

### 1. 授权验证
- 所有接口都需要有效的授权码
- 支持IP白名单配置
- 实现请求频率限制

### 2. 数据安全
- 敏感信息加密存储
- 传输数据SSL/TLS加密
- 定期数据备份

### 3. 访问控制
- 基于角色的权限控制
- API访问日志记录
- 异常行为监控

## 故障排除

### 常见问题

1. **连接失败**
   - 检查网络连接
   - 验证配置参数
   - 查看错误日志

2. **验证码提交失败**
   - 确认验证码格式
   - 检查时效性
   - 验证设备信息

3. **RabbitMQ连接问题**
   - 检查服务状态
   - 验证认证信息
   - 查看连接日志

### 调试模式

```bash
# 启用调试模式
export DEBUG=true
go run main.go

# 查看详细日志
tail -f logs/wechatpadpro.log
```

## 更新日志

### v1.0.0 (2024-01-01)
- ✅ 新增自动验证码处理功能
- ✅ 集成RabbitMQ消息队列
- ✅ 优化登录状态检测
- ✅ 支持多账号管理
- ✅ 添加自动Token刷新
- ✅ 完善错误处理机制
- ✅ 增强安全性验证
- ✅ 优化性能监控

### 待开发功能
- 🔄 支持更多登录方式
- 🔄 增强安全性验证
- 🔄 优化性能监控
- 🔄 添加管理后台
- 🔄 支持集群部署
- 🔄 添加WebSocket支持

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 技术支持

- **文档**: [docs/](docs/)
- **问题反馈**: [Issues](https://github.com/your-repo/WeChatPadPro/issues)
- **讨论**: [Discussions](https://github.com/your-repo/WeChatPadPro/discussions)
- **邮箱**: support@example.com

## 致谢

感谢所有为这个项目做出贡献的开发者和用户。

---

**注意**: 本项目仅供学习和研究使用，请遵守相关法律法规和微信平台的使用条款。 