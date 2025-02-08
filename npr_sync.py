#!/usr/bin/env python3
# 0 * * * * cd /path/to/npr-sync && source venv/bin/activate && source .env && python npr_sync.py
import feedparser
import requests
import logging
import os
from pathlib import Path
from trello import TrelloClient
from typing import Optional, Tuple
from datetime import datetime

class NPRSyncProcessor:
    """Syncs NPR New Music Friday RSS feed with a Trello card"""

    def __init__(self):
        # Set up logging
        self.setup_logging()

        # Load configuration from environment
        self.load_config()

        # Initialize Trello client
        self.trello = TrelloClient(
            api_key=self.config['trello_key'],
            token=self.config['trello_token']
        )

        # Create temp directory for downloads
        self.temp_dir = Path('temp_downloads')
        self.temp_dir.mkdir(exist_ok=True)

    def setup_logging(self):
        """Configure logging with both file and console output"""
        self.logger = logging.getLogger('NPRSync')
        self.logger.setLevel(logging.INFO)

        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        # File handler with daily rotation
        log_file = log_dir / f'npr_sync_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        self.logger.addHandler(console_handler)

    def load_config(self):
        """Load configuration from environment variables"""
        required_vars = {
            'TRELLO_API_KEY': 'trello_key',
            'TRELLO_TOKEN': 'trello_token',
            'TRELLO_BOARD_NAME': 'board_name'
        }

        self.config = {}
        missing_vars = []

        for env_var, config_key in required_vars.items():
            value = os.getenv(env_var)
            if value is None:
                missing_vars.append(env_var)
            self.config[config_key] = value

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _get_board_and_card(self) -> Tuple[Optional[str], Optional[object]]:
        """Find the NPR card on the specified board"""
        try:
            # Find the board
            boards = self.trello.list_boards()
            board = next((b for b in boards if b.name == self.config['board_name']), None)
            if not board:
                self.logger.error(f"Board '{self.config['board_name']}' not found")
                return None, None

            # Find the NPR card
            for list_obj in board.list_lists():
                for card in list_obj.list_cards():
                    if card.name == "NPR New Music Friday":
                        return board.id, card

            self.logger.error("NPR New Music Friday card not found")
            return None, None

        except Exception as e:
            self.logger.error(f"Error accessing Trello: {str(e)}")
            return None, None

    def _get_latest_npr_mp3(self) -> Optional[dict]:
        """Get the URL and title of the latest MP3 from the NPR feed"""
        try:
            feed = feedparser.parse('https://feeds.npr.org/510019/podcast.xml')

            # Look for MP3 enclosures in entries
            for entry in feed.entries:
                if 'enclosures' in entry:
                    for enclosure in entry.enclosures:
                        if enclosure.type == 'audio/mpeg':
                            return {
                                'url': enclosure.href,
                                'title': entry.title,
                                'date': entry.published
                            }

            self.logger.error("No MP3 found in RSS feed")
            return None

        except Exception as e:
            self.logger.error(f"Error parsing RSS feed: {str(e)}")
            return None

    def _download_mp3(self, url: str) -> Optional[Path]:
        """Download MP3 file to temporary location"""
        try:
            temp_file = self.temp_dir / 'latest_npr.mp3'

            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return temp_file

        except Exception as e:
            self.logger.error(f"Error downloading MP3: {str(e)}")
            return None

    def _update_card_attachment(self, card, mp3_path: Path, episode_info: dict) -> bool:
        """Update the card's attachment and description with new MP3"""
        try:
            # Remove existing attachments
            for attachment in card.get_attachments():
                if attachment.name.endswith('.mp3'):
                    attachment.delete()

            # Update card description with episode info
            card.set_description(
                f"Latest Episode: {episode_info['title']}\n"
                f"Published: {episode_info['date']}\n"
                f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Add new attachment
            with open(mp3_path, 'rb') as f:
                card.attach(
                    name=f"NPR_New_Music_Friday_{datetime.now().strftime('%Y%m%d')}.mp3",
                    file=f,
                    mimeType='audio/mpeg'
                )
            return True

        except Exception as e:
            self.logger.error(f"Error updating card attachment: {str(e)}")
            return False

    def cleanup(self):
        """Clean up temporary files"""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob('*'):
                    file.unlink()
                self.temp_dir.rmdir()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def sync(self) -> bool:
        """
        Main sync process. Returns True if successful, False otherwise.
        """
        try:
            # Get board and card
            board_id, card = self._get_board_and_card()
            if not card:
                return False

            # Get latest MP3 info from RSS
            episode_info = self._get_latest_npr_mp3()
            if not episode_info:
                return False

            # Check if the MP3 URL matches current attachment
            current_attachments = card.get_attachments()
            for attachment in current_attachments:
                if attachment.url == episode_info['url']:
                    self.logger.info("Card already has the latest MP3")
                    return True

            # Download new MP3
            mp3_path = self._download_mp3(episode_info['url'])
            if not mp3_path:
                return False

            # Update card attachment and description
            success = self._update_card_attachment(card, mp3_path, episode_info)

            if success:
                self.logger.info(f"Successfully updated NPR New Music Friday card with: {episode_info['title']}")

            return success

        except Exception as e:
            self.logger.error(f"Sync error: {str(e)}")
            return False
        finally:
            self.cleanup()

if __name__ == "__main__":
    try:
        processor = NPRSyncProcessor()
        processor.sync()
    except Exception as e:
        print(f"Error: {str(e)}")
