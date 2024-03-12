# 使用Python的官方镜像作为基础镜像
FROM python:3.9.6

# 设置工作目录
WORKDIR /app

# 复制应用程序代码到工作目录
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露应用程序的端口
EXPOSE 5000

# 启动应用程序
CMD ["python", "icloud_prices.py"]
