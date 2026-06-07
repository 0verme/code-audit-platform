# 代码审查平台

当前仓库已将静态原型拆成可运行的 `React + Vite` 前端和 `Flask + SQLite` 后端，保留了原型的页面结构、卡片、表格、导航和交互，同时增加了 REST API、mock 回退、构建和离线部署说明。

## 目录结构

```text
code-review-platform/
├─ 静态原型代码/
├─ frontend/
│  ├─ src/
│  │  ├─ components/
│  │  ├─ config/
│  │  ├─ hooks/
│  │  ├─ mock/
│  │  ├─ pages/
│  │  ├─ services/
│  │  └─ styles/
│  ├─ package.json
│  ├─ vite.config.js
│  └─ .env.example
├─ backend/
│  ├─ app.py
│  ├─ database.py
│  ├─ requirements.txt
│  └─ data/
└─ README.md
```

## 第一阶段：前端工程化

前端位于 [frontend](E:/AI生成代码/代码审查平台/frontend)。

安装依赖：

```bash
cd frontend
npm install
```

开发启动：

```bash
npm run dev
```

生产构建：

```bash
npm run build
```

说明：

- 原型中的 React/Babel CDN 已移除，改为 Vite 本地构建。
- CSS 已迁移到 `src/styles`，并继续沿用原有视觉风格。
- mock 数据位于 `src/mock/data.js`，后端不可用时自动回退。
- 前端 API 地址通过 `VITE_API_BASE_URL` 配置，示例见 [frontend/.env.example](E:/AI生成代码/代码审查平台/frontend/.env.example)。

## 第二阶段：后端 Flask

后端位于 [backend](E:/AI生成代码/代码审查平台/backend)。

创建虚拟环境并安装依赖：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

开发启动：

```bash
python app.py
```

已提供接口：

- `GET /api/health`
- `GET /api/projects`
- `GET /api/audit-tasks`
- `GET /api/audit-results`
- `POST /api/audit-tasks`
- `GET /api/fine-report/items`

说明：

- SQLite 数据库文件默认生成在 `backend/data/app.db`。
- 首次启动会自动初始化表结构和示例数据。
- 已启用 CORS，方便前端本地联调。

## 第三阶段：前后端联调

联调要点：

- `frontend/src/services/apiClient.js` 统一管理请求。
- `frontend/src/config/api.js` 统一管理 API 路径和基础地址。
- 首页项目列表、任务列表、结果列表、帆软报表列表优先请求后端。
- 当后端不可用时，页面会显示友好提示并回退到 `mock` 数据。
- 已处理 `loading / empty / error` 三类状态。

前后端一起启动时建议：

```bash
cd backend
python app.py
```

```bash
cd frontend
copy .env.example .env
npm run dev
```

默认前端会请求：

```text
http://127.0.0.1:5000/api
```

## 第四阶段：Linux 离线部署

### 前端离线部署

在有依赖缓存或内网 npm 源的环境完成构建：

```bash
cd frontend
npm install
npm run build
```

构建产物位于：

```text
frontend/dist
```

`dist` 可独立部署到 Nginx 静态目录，不依赖 `unpkg`、`cdn.jsdelivr` 或任何公网 CDN。

### 后端离线部署

建议先在内网制品库准备 Python wheel 包，再安装：

```bash
cd backend
pip install -r requirements.txt
```

Linux 启动方式：

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

如果环境更适合 Windows 服务或纯 Python 方式，可用：

```bash
waitress-serve --host 0.0.0.0 --port 5000 app:app
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name _;

    root /opt/code-review-platform/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 后续可扩展点

- 将 SQLite 数据访问替换为 SQLAlchemy 或仓储层，方便后续切 Oracle/PostgreSQL。
- 增加 `GET /api/audit-results/:taskId` 之类的明细接口，进一步替换结果页 mock 数据。
- 将“提交审查”真正接入 SVN/Git 扫描与规则引擎。
