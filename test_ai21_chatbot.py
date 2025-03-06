import asyncio
from app.core.chatbot import chatbot

async def test_chatbot():
    """Test the AI21-powered chatbot implementation"""
    print("Testing AI21 Chatbot Implementation...")
    
    try:
        # Process a simple message
        test_message = "Generate creative ideas for a sustainable smart home product"
        print(f"\nSending test message: '{test_message}'")
        
        # Process the message
        session = await chatbot.process_message(
            user_id="test_user",
            message=test_message,
            deep_research=False
        )
        
        # Get the chatbot's response (last message in the session)
        bot_response = session.messages[-1].content
        
        print("\n--- AI21 Response ---")
        print(bot_response)
        print("---------------------")
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"\nError during test: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_chatbot())
