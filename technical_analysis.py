"""
Test your Telegram bot connection
Run: python test_telegram.py
"""

import os
from dotenv import load_dotenv
import requests

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def test_telegram_connection():
    """Test if Telegram bot is working"""
    
    print("🧪 Testing Telegram Bot Connection...")
    print(f"Bot Token: {BOT_TOKEN[:10]}..." if BOT_TOKEN else "❌ No token found")
    print(f"Chat ID: {CHAT_ID}" if CHAT_ID else "❌ No chat ID found")
    
    if not BOT_TOKEN or not CHAT_ID:
        print("\n❌ Missing credentials in .env file")
        print("Please add:")
        print("  TELEGRAM_BOT_TOKEN=your_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        return False
    
    # Test API endpoint
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('ok'):
            bot_info = data.get('result', {})
            print(f"\n✅ Bot Connected!")
            print(f"   Bot Name: @{bot_info.get('username')}")
            print(f"   Bot ID: {bot_info.get('id')}")
            
            # Test sending message
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            message_data = {
                'chat_id': CHAT_ID,
                'text': '✅ Telegram bot is working! Your bot is connected.',
                'parse_mode': 'Markdown'
            }
            
            send_response = requests.post(send_url, json=message_data, timeout=5)
            send_data = send_response.json()
            
            if send_data.get('ok'):
                print(f"\n✅ Message Sent Successfully!")
                print(f"   Message ID: {send_data.get('result', {}).get('message_id')}")
                return True
            else:
                print(f"\n❌ Failed to send message: {send_data.get('description')}")
                return False
        else:
            print(f"\n❌ Bot token invalid: {data.get('description')}")
            return False
    
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    success = test_telegram_connection()
    exit(0 if success else 1)
