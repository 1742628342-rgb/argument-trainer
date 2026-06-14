# 观点反驳训练器

## 项目简介

这是一个使用 Python、Streamlit 和 SQLite 构建的观点分析与逻辑训练工具。
用户输入观点后，系统会分析支持理由、反对理由、成立条件、概念偷换风险，
再通过 5 轮反方追问和六维评分帮助用户收窄结论、补充证据并改进表达。

项目默认使用本地规则，不配置 API Key 也能完整运行。Gemini、OpenRouter
和 Groq 只是可选增强，调用失败时会自动回退规则模式。

## 功能列表

- 规则版观点分析
- 可选 Gemini、OpenRouter、Groq API 分析
- 自动模式按 Gemini → OpenRouter → Groq 尝试
- 连续 5 轮定义、边界、反例、因果和副作用追问
- 概念清晰度等六个维度的逻辑评分
- SQLite 自动建库、兼容迁移和历史记录
- 完整训练记录的 UTF-8 Markdown 导出
- API 配置状态与连通性测试，页面不显示完整 Key
- 本地读取 `.env`，Streamlit Community Cloud 读取应用 Secrets

## 安装步骤

建议使用 Python 3.10 或更高版本。在项目目录执行：

```powershell
py -m pip install -r requirements.txt
```

如果系统没有 `py` 命令，也可以使用：

```powershell
python -m pip install -r requirements.txt
```

## 运行命令

```powershell
py -m streamlit run app.py
```

也可以直接使用：

```powershell
streamlit run app.py
```

浏览器通常会打开 `http://localhost:8501`。`data/` 或数据库文件不存在时，
程序会在启动或首次操作时自动创建。

## 规则模式使用方法

1. 打开“新训练”页面。
2. 输入一个需要检验的观点。
3. 选择反方强度。
4. 分析模式选择“规则分析”。
5. 点击“开始分析”，查看五类初始分析。
6. 点击“进入 5 轮反方追问”，逐轮回答。
7. 完成第 5 轮后点击“生成逻辑评分”。
8. 在“历史记录”页面查看或导出完整训练。

规则模式完全本地运行，不需要 `.env`，也不会发送观点或回答到外部服务。

## API 配置方法

复制环境变量示例：

```powershell
Copy-Item .env.example .env
```

在 `.env` 中只填写准备使用的 Key：

```dotenv
GEMINI_API_KEY=
OPENROUTER_API_KEY=
GROQ_API_KEY=

DEFAULT_PROVIDER=auto
GEMINI_MODEL=gemini-2.5-flash
OPENROUTER_MODEL=openrouter/free
GROQ_MODEL=llama-3.1-8b-instant
```

`.env` 已加入 `.gitignore`，不要把真实 Key 提交到仓库，也不要在截图或聊天中
公开 Key。

### Gemini

1. 打开 [Google AI Studio API Keys](https://aistudio.google.com/app/apikey)。
2. 创建 API Key。
3. 将其填入 `GEMINI_API_KEY`。
4. 在“API 设置”页面测试可用性。

### OpenRouter

1. 打开 [OpenRouter Keys](https://openrouter.ai/keys)。
2. 创建 API Key。
3. 将其填入 `OPENROUTER_API_KEY`。
4. 可保留 `OPENROUTER_MODEL=openrouter/free` 使用平台免费路由。

### Groq

1. 打开 [Groq API Keys](https://console.groq.com/keys)。
2. 创建 API Key。
3. 将其填入 `GROQ_API_KEY`。
4. 在“API 设置”页面测试可用性。

## 免费 API 说明

免费模型、免费额度、速率限制、地区限制和模型名称可能随平台政策变化，
请以各平台官方页面为准。免费额度用尽、Key 错误、网络异常或模型不可用时，
页面会提示 API 不可用，并自动使用规则模式继续当前训练。

## Streamlit Community Cloud 部署

1. 将项目上传到 GitHub，确保 `.env` 和 `data/*.db` 没有提交。
2. 打开 [Streamlit Community Cloud](https://share.streamlit.io/)。
3. 选择 GitHub 仓库，并将入口文件设置为 `app.py`。
4. 在应用的 Advanced settings 或 Secrets 中填写：

```toml
OPENROUTER_API_KEY = "你的 OpenRouter Key"
DEFAULT_PROVIDER = "openrouter"
OPENROUTER_MODEL = "openrouter/free"
```

云端不需要上传 `.env`。Community Cloud 的本地文件系统不是永久存储，
应用重启或重新部署后，SQLite 历史记录可能被清空；请及时导出重要训练记录。

## 分析模式

- `规则分析`：完全本地运行。
- `Gemini API`：优先使用 Gemini，失败后回退规则模式。
- `OpenRouter API`：优先使用 OpenRouter，失败后回退规则模式。
- `Groq API`：优先使用 Groq，失败后回退规则模式。
- `自动模式`：依次尝试 Gemini、OpenRouter、Groq，最后回退规则模式。

## 常见问题

### 启动时提示找不到 streamlit

确认已在当前 Python 环境运行 `py -m pip install -r requirements.txt`，然后使用
`py -m streamlit run app.py`，避免调用到另一个 Python 环境。

### API 页面显示“已配置”，测试却不可用

Key 可能无效、无权限、额度用尽、模型不可用或网络受限。重新生成 Key，
检查 `.env` 中是否有多余空格，并以服务商控制台状态为准。规则模式仍可使用。

### 没有 `.env` 或 `.env` 是空文件

这是允许的。进入“新训练”并选择“规则分析”即可完成全部功能。

### 数据库报错或历史记录异常

先确认项目目录可写，并检查 `data/argument_trainer.db` 是否被其他程序独占。
程序会自动创建表并迁移已知旧字段。重要记录请先通过历史页面导出 Markdown。

### 页面没有出现最新结果

刷新页面后重新选择对应训练记录。当前进度以 SQLite 中已保存的记录为准。

## 测试

```powershell
py -m unittest discover -s tests -v
```

## 项目结构

```text
argument_trainer/
├── .env.example
├── app.py
├── requirements.txt
├── README.md
├── data/
├── exports/
├── modules/
│   ├── database.py
│   ├── export_utils.py
│   ├── llm_client.py
│   ├── prompt_templates.py
│   ├── rule_engine.py
│   └── scoring.py
├── pages/
│   ├── 1_new_training.py
│   ├── 2_debate_session.py
│   ├── 3_history.py
│   └── 4_settings.py
└── tests/
```

## 后续扩展建议

- 增加训练标签、搜索和筛选
- 支持导出 PDF 或打印版报告
- 增加同一观点的多次训练对比
- 增加可编辑的规则词库和评分权重
- 在明确隐私策略后增加多用户账户与数据隔离
