# Media Opinion Simulator

一个融合多智能体仿真与大语言模型的新闻舆论分析系统，用于模拟国际事件中媒体与公众的舆论反应及传播动态。

## 核心特性

- **多智能体仿真**：基于 NetLogo 构建媒体机构与国际社交媒体用户两类智能体
- **LLM 增强内容生成**：集成智谱 AI GLM 模型，根据智能体属性生成符合其立场的提问与评论
- **社交网络传播**：模拟观点在社交网络中的传播与演化过程
- **模块化架构**：前后端分离设计，支持灵活扩展与定制

## 系统架构

NetLogo 前端 → 文件通信桥梁 → Python API 后端 → 智谱 AI LLM
↓ ↓ ↓ ↓
智能体可视化 请求/响应中转 业务逻辑处理 内容生成

## 快速开始

### 前置要求

- Python 3.8+
- NetLogo 6.2.1+
- 智谱 AI API 密钥

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/Qihusb/netlogo-llm-opinion-simulation.git
   cd netlogo-llm-opinion-simulation
   ```
2. **配置 Python 后端**
   cd api_server
   pip install -r requirements.txt
   cp .env.example .env
   编辑.env 文件，填入 ZHIPUAI_API_KEY
3. **启动服务**
   终端 1: 启动 API 服务器
   python api_server.py

   终端 2: 启动通信桥梁
   python http_client.py

4. **启动 NetLogo 仿真**
   打开 NetLogo，加载 news_simulation.nlogo

   依次点击：初始化 → 测试连接 → 开始仿真

## 项目结构

netlogo-llm-opinion-simulation/
├── api_server.py # Python 后端服务
├── agents_data/ # 智能体画像数据
├── news_simulation.nlogo # NetLogo 仿真前端
├── http_client.py # 通信工具脚本
├── prompts/ # prompt 方法
└── tests.py # 测试文件

## 配置说明

### 媒体画像配置

编辑 agents_data/media_profiles.json：

### 仿真参数调整

在 NetLogo 界面中可直接调整：
num-media：媒体数量
num-users：用户数量
conference-topic：仿真议题
api-temperature：AI 生成温度参数

## 使用示例

系统支持以下仿真场景：
新闻发布会模拟：多家媒体就指定议题提问
用户评论生成：社交媒体用户对新闻事件的反应
观点传播分析：观察舆论在社交网络中的扩散过程

## 输出数据

仿真结果自动导出：
media_questions.csv：媒体提问记录
user_comments.csv：用户评论记录
观点分布可视化图表

## 开发扩展

1. **添加新智能体类型**
   在 agents_data/ 中添加画像文件
   在 prompts/templates.py 中添加提示词模板
   在 NetLogo 模型中扩展智能体品种

2. **集成其他 LLM**
   修改 api_server.py 中的 generate_with_zhipuai() 函数，适配其他 AI 服务 API。

## 许可证

MIT License - 详见 LICENSE 文件。

## 致谢

NetLogo 社区提供的仿真平台
智谱 AI 的 GLM 大模型 API 支持
