
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always rain in {city}!"


model = ChatOpenAI(
    api_key=SecretStr(""),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    model="qwen-plus",  # Base URL
    temperature=0.7,
    max_tokens=1000
)

agent = create_agent(
    model=model,
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

# Run the agent
result = agent.invoke(
    {"messages": [{"role": "user", "content": "淄博今天天气怎么样？适合出行吗？"}]}
)
print(result)