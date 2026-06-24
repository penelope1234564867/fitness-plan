"""测试1: LLM 基础连通性"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LLM_API_KEY"] = "sk-f67e90469a0b4de9ab483196f6d5eb87"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL_ID"] = "deepseek-v4-flash"

from hello_agents import HelloAgentsLLM

print("=" * 50)
print("测试1: LLM 基础连通")
print("=" * 50)

try:
    llm = HelloAgentsLLM()
    print(f"  模型: {llm.model if hasattr(llm, 'model') else 'N/A'}")

    r = llm.invoke([{"role": "user", "content": "你好，回复一个字：好"}])
    print(f"  LLM响应: {r}")
    print("✅ LLM 连通正常")
except Exception as e:
    print(f"❌ LLM 连通失败: {e}")
