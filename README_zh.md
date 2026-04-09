# NUS 选课智能助教 (NUS Course Selection Agent) 🎓

[**English**](./README.md) | [**简体中文**](./README_zh.md)

专为 NUS 学生设计的 AI 学术助手。利用 NUSMods 实时数据，提供个性化的课程推荐、先修课程 (Prerequisite) 校验以及基于个人偏好的选课规划。

---

## ✨ 核心功能
- **AI 智能推理**: 支持 Google Gemini 1.5 Pro 或 OpenRouter (如 NVIDIA Nemotron、Gemma 等)。
- **先修课自动校验**: 递归逻辑解析先修课树，根据已修课程判断选课资格。
- **实时数据同步**: 通过 NUSMods API 获取最新的课程描述和课表信息。
- **实时流式响应**: 采用 SSE 技术实现流式对话，交互更流畅。
- **极简玻璃拟物界面**: 基于 Next.js、Tailwind CSS 4 和 Framer Motion 打造的高端现代 UI。

## 🛠️ 技术栈
- **后端**: FastAPI (Python 3.10+)
- **前端**: Next.js 15+, Tailwind CSS 4, Framer Motion
- **模型**: Google Gemini, OpenRouter (NVIDIA, Llama, etc.)

---

## 🚀 快速开始

### 环境依赖
- Python 3.10 或更高版本
- Node.js 18.x 或更高版本
- [Google AI Studio](https://aistudio.google.com/) 或 [OpenRouter](https://openrouter.ai/) 的 API Key

### 1. 后端配置
```bash
cd backend
pip install -r requirements.txt
```

在 `backend/` 目录下创建 `.env` 文件：
```env
# 提供商选择: 'gemini' 或 'openrouter'
LLM_PROVIDER=gemini

# API 密钥 (至少配置一个)
GOOGLE_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=google/gemma-2-9b-it:free
```

启动服务器:
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. 前端配置
```bash
cd frontend
npm install
npm run dev
```
访问 [http://localhost:3000](http://localhost:3000) 即可开始。

---

## 📖 使用说明
1.  **设置个人文件**: 在左侧边栏添加你已修读过的课程（如 `CS1010`, `CS1231S`）并设置你的选课偏好。
2.  **测试连接**: 点击偏好设置中的 "Test Connection" 按钮，验证你的 LLM 配置是否成功。
3.  **开始对话**: 输入类似 "CS 大一新生对 AI 感兴趣，该怎么选课？" 或 "推荐一些适合未来从事 UI/UX 方向的课程" 等问题。

---

## 🛡️ 开源协议
本项目采用 MIT 协议。详见 `LICENSE`。

---

> [!TIP]
> **Demo 演示模式**: 如果你暂时没有 API Key，系统会自动切换到模拟模式 (Demo Mode)，你依然可以立即体验交互界面！
