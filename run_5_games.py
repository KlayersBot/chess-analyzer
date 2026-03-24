import asyncio
import sys
from agent import root_agent
from google.adk.runners import InMemoryRunner
from google.genai import types
import tools

async def analyze_game(index):
    try:
        runner = InMemoryRunner(agent=root_agent)
        await runner.session_service.create_session(user_id=f"user_{index}", session_id=f"sess_{index}", app_name=runner.app_name)
        
        prompt = f"Analyze game index {index} for user 'kar2on'. Step through it move-by-move and create the full report."
        content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        
        print(f"Starting analysis for game {index}...")
        async for event in runner.run_async(user_id=f"user_{index}", session_id=f"sess_{index}", new_message=content):
            pass
        print(f"Game {index} analysis complete.")
    except Exception as e:
        print(f"Error analyzing game {index}: {e}")
    finally:
        if tools.GAME_STATE.engine:
            tools.GAME_STATE.engine.quit()
            tools.GAME_STATE.engine = None

async def main():
    for i in range(5):
        await analyze_game(i)

if __name__ == "__main__":
    asyncio.run(main())
