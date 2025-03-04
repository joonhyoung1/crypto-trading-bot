import os
import logging
from telegram import Bot

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def send_test_message():
    try:
        bot = Bot(token=os.environ.get('TELEGRAM_BOT_TOKEN'))
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')

        logger.info("Sending test message...")
        message = bot.send_message(chat_id=chat_id, text="Hi 👋")
        logger.info("Test message sent successfully")
        return message

    except Exception as e:
        logger.error(f"Failed to send test message: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    send_test_message()