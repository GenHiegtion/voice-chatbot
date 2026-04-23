import asyncio
from langchain_core.messages import HumanMessage
from src.agents.graph import get_graph

async def main():
    graph = get_graph()
    messages = [HumanMessage(content="Thêm 1 lẩu thái vào giỏ hàng")]
    print("Testing new item addition...")
    result = await graph.ainvoke({
        "messages": messages,
        "session_id": "test_1",
        "current_cart": [],
        "action": "None",
        "action_data": None
    })
    print("\n\n--- Result ---")
    for msg in result["messages"]:
        print(f"[{getattr(msg, 'name', msg.type)}] {msg.content}")
    print(f"Action: {result.get('action')} - Data: {result.get('action_data')}")

if __name__ == "__main__":
    asyncio.run(main())
