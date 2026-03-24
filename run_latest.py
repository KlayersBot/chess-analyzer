import asyncio
from agent import root_agent
from google.adk.runners import InMemoryRunner
from google.genai import types
import tools

async def analyze_game():
    try:
        runner = InMemoryRunner(agent=root_agent)
        await runner.session_service.create_session(user_id="user_latest", session_id="sess_latest", app_name=runner.app_name)
        
        prompt = "Analyze game index 0 for user 'kar2on'. Step through it move-by-move and create the full report."
        content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        
        print(f"Starting analysis for the latest game...")
        async for event in runner.run_async(user_id="user_latest", session_id="sess_latest", new_message=content):
            pass
        print(f"Latest game analysis complete.")
    except Exception as e:
        print(f"Error analyzing game: {e}")
    finally:
        if tools.GAME_STATE.engine:
            tools.GAME_STATE.engine.quit()
            tools.GAME_STATE.engine = None

if __name__ == "__main__":
    asyncio.run(analyze_game())
