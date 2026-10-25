# Railway 部署镜像（构建上下文 = 仓库根）
#
# 为什么不用 Nixpacks：依赖清单在 server/ 子目录，Nixpacks 在仓库根探测不到 Python 项目，
# 即使显式写 providers = ["python"] 也只装 python3 不装 pip，构建会报 "pip: command not found"。
# 这里用官方 python:3.11-slim，pip 与 wheel 都在，构建结果可预期。
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/server

# 先只拷依赖清单，最大化 Docker 层缓存（改业务代码不会重装依赖）
COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 再拷整个仓库（后端 + 云函数种子 + 前端构建产物 bala-web/dist）
COPY . /app

WORKDIR /app/server

# SQLite 与日志目录：镜像里没有（已 gitignore），启动时程序会自建，这里预建更稳
RUN mkdir -p data logs admin-web/static

EXPOSE 8000

# Railway 通过环境变量 PORT 指定端口，这里必须留默认值以便本地也能跑
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
