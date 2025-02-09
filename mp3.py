#!/usr/bin/env python3

import feedparser
import requests
import logging
import os
from pathlib import Path
from trello import TrelloClient
from typing import Optional, Tuple, Dict
from datetime import datetime
from dataclasses import dataclass

@dataclass
class FeedConfig:
    """Configuration for a podcast feed sync"""
    feed_url: str
    card_name: str
    file_prefix: str = ""  # Optional prefix for downloaded files

class PodcastSyncProcessor:
    """Syncs podcast RSS feeds with Trello cards"""

    def __init__(self, feeds_config: Dict[str, Dict[str, str]]):
        """
        Initialize the processor with feed configurations

        Args:
            feeds_config: Dictionary mapping feed IDs to their configurations
                Example: {
                    'npr': {
                        'feed_url': 'https://feeds.npr.org/1039/rss.xml',
                        'card_name': 'NPR New Music Friday'
                    },
                    'oddlots': {
                        'feed_url': 'https://www.omnycontent.com/d/playlist/...',
                        'card_name': 'Odd Lots'
                    }
                }
        """
        # Set up logging
        self.setup_logging()

        # Load configuration from environment
        self.load_config()

        # Configure feeds
        self.feeds = {
            feed_id: FeedConfig(**config)
            for feed_id, config in feeds_config.items()
        }

        # Initialize Trello client
        self.trello = TrelloClient(
            api_key=self.config['trello_key'],
            token=self.config['trello_token']
        )

        # Create temp directory for downloads
        self.temp_dir = Path('temp_downloads')
        self._ensure_temp_dir()  # Ensure directory exists at initialization

    def setup_logging(self):
        """Configure logging with both file and console output"""
        self.logger = logging.getLogger('PodcastSync')
        self.logger.setLevel(logging.INFO)

        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(parents=True, exist_ok=True)

        # File handler with daily rotation
        log_file = log_dir / f'podcast_sync_{datetime.now().strftime("%Y%m%d")}.log'
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

    def _ensure_temp_dir(self):
        """Ensure temporary directory exists and is empty"""
        try:
            # Recreate temp directory if it doesn't exist
            self.temp_dir.mkdir(parents=True, exist_ok=True)

            # Clean any existing files
            for file in self.temp_dir.glob('*'):
                try:
                    file.unlink()
                except Exception as e:
                    self.logger.warning(f"Could not remove existing file {file}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error ensuring temp directory exists: {str(e)}")
            raise

    def _get_board_and_card(self, card_name: str) -> Tuple[Optional[str], Optional[object]]:
        """Find a specific card on the specified board"""
        try:
            # Find the board
            boards = self.trello.list_boards()
            board = next((b for b in boards if b.name == self.config['board_name']), None)
            if not board:
                self.logger.error(f"Board '{self.config['board_name']}' not found")
                return None, None

            # Find the specified card
            for list_obj in board.list_lists():
                for card in list_obj.list_cards():
                    if card.name == card_name:
                        return board.id, card

            self.logger.error(f"Card '{card_name}' not found")
            return None, None

        except Exception as e:
            self.logger.error(f"Error accessing Trello: {str(e)}")
            return None, None

    def _get_latest_episode(self, feed_url: str) -> Optional[dict]:
        """Get the URL and info of the latest episode from an RSS feed"""
        try:
            feed = feedparser.parse(feed_url)

            # Look for audio enclosures in entries
            for entry in feed.entries:
                if 'enclosures' in entry:
                    for enclosure in entry.enclosures:
                        if enclosure.type in ['audio/mpeg', 'audio/mp3']:
                            return {
                                'url': enclosure.href,
                                'title': entry.title,
                                'date': entry.get('published', 'Unknown date'),
                                'description': entry.get('summary', '')
                            }

            self.logger.error("No audio file found in RSS feed")
            return None

        except Exception as e:
            self.logger.error(f"Error parsing RSS feed: {str(e)}")
            return None

    def _download_audio(self, url: str, prefix: str = "") -> Optional[Path]:
        """Download audio file to temporary location"""
        try:
            # Ensure temp directory exists before download
            self._ensure_temp_dir()

            filename = f"{prefix}_latest.mp3" if prefix else "latest.mp3"
            temp_file = self.temp_dir / filename

            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Verify file was created successfully
            if not temp_file.exists():
                raise FileNotFoundError(f"Failed to create file: {temp_file}")

            return temp_file

        except Exception as e:
            self.logger.error(f"Error downloading audio: {str(e)}")
            return None

    def _update_card_attachment(self, card, audio_path: Path, episode_info: dict, prefix: str = "") -> bool:
        """Update the card's attachment and description with new audio"""
        try:
            # Remove existing attachments
            for attachment in card.get_attachments():
                if attachment.name.endswith('.mp3'):
                    card.remove_attachment(attachment.id)

            # Update card description with episode info
            card.set_description(
                f"Latest Episode: {episode_info['title']}\n"
                f"Published: {episode_info['date']}\n"
                f"Description: {episode_info.get('description', '')}\n"
                f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Add new attachment
            filename = f"{prefix}_{datetime.now().strftime('%Y%m%d')}.mp3" if prefix else f"episode_{datetime.now().strftime('%Y%m%d')}.mp3"
            with open(audio_path, 'rb') as f:
                card.attach(
                    name=filename,
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
                    try:
                        file.unlink()
                    except Exception as e:
                        self.logger.warning(f"Could not remove file {file}: {str(e)}")
                try:
                    self.temp_dir.rmdir()
                except Exception as e:
                    self.logger.warning(f"Could not remove temp directory: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def sync_feed(self, feed_id: str) -> bool:
        """
        Sync a specific feed. Returns True if successful, False otherwise.
        """
        if feed_id not in self.feeds:
            self.logger.error(f"Unknown feed ID: {feed_id}")
            return False

        feed_config = self.feeds[feed_id]

        try:
            # Get board and card
            board_id, card = self._get_board_and_card(feed_config.card_name)
            if not card:
                return False

            # Get latest episode info from RSS
            episode_info = self._get_latest_episode(feed_config.feed_url)
            if not episode_info:
                return False

            # Check if the audio URL matches current attachment
            current_attachments = card.get_attachments()
            for attachment in current_attachments:
                if attachment.url == episode_info['url']:
                    self.logger.info(f"Card already has the latest episode: {episode_info['title']}")
                    return True

            # Download new audio
            audio_path = self._download_audio(episode_info['url'], feed_config.file_prefix)
            if not audio_path:
                return False

            # Update card attachment and description
            success = self._update_card_attachment(card, audio_path, episode_info, feed_config.file_prefix)

            if success:
                self.logger.info(f"Successfully updated {feed_config.card_name} with: {episode_info['title']}")

            return success

        except Exception as e:
            self.logger.error(f"Sync error for {feed_id}: {str(e)}")
            return False
        finally:
            self.cleanup()

    def sync_all(self) -> Dict[str, bool]:
        """
        Sync all configured feeds. Returns a dictionary of results.
        """
        results = {}
        for feed_id in self.feeds:
            results[feed_id] = self.sync_feed(feed_id)
        return results

if __name__ == "__main__":
    import argparse

    # Example configuration
    FEEDS_CONFIG = {
        'cpr': {
            'feed_url': 'https://pod.cpr.org/cm/',
            'card_name': 'Colorado Matters',
            'file_prefix': 'cpr'
        },
        'npr': {
            'feed_url': 'https://feeds.npr.org/510019/podcast.xml',
            'card_name': 'NPR New Music Friday',
            'file_prefix': 'npr'
        },
        'oddlots': {
            'feed_url': 'https://www.omnycontent.com/d/playlist/e73c998e-6e60-432f-8610-ae210140c5b1/8a94442e-5a74-4fa2-8b8d-ae27003a8d6b/982f5071-765c-403d-969d-ae27003a8d83/podcast.rss',
            'card_name': 'Odd Lots',
            'file_prefix': 'oddlots'
        },
        'radio_atlantic': {
            'feed_url': 'https://feeds.megaphone.fm/ATL8165151910',
            'card_name': 'Radio Atlantic',
            'file_prefix': 'radio_atlantic'
        },
        '80k_hours': {
            'feed_url': 'https://feeds.transistor.fm/80000-hours-podcast',
            'card_name': '80k Hours',
            'file_prefix': '80k_hours'
        },
        'ft_rachman_review': {
            'feed_url': 'https://feeds.acast.com/public/shows/7144a390-7a86-440e-9b2e-db712c18368c',
            'card_name': 'FT Rachman Review',
            'file_prefix': 'ft_rachman_review'
        },
        'ft_news_briefing': {
            'feed_url': 'https://feeds.acast.com/public/shows/73fe3ede-5c5c-4850-96a8-30db8dbae8bf',
            'card_name': 'FT News Briefing',
            'file_prefix': 'ft_news_briefing'
        }
    }

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Sync podcast RSS feeds to Trello cards')
    parser.add_argument('feed_id', nargs='?', help='Specific feed to sync (default: sync all)')
    parser.add_argument('--list', action='store_true', help='List available feeds')
    args = parser.parse_args()

    try:
        # Initialize processor
        processor = PodcastSyncProcessor(FEEDS_CONFIG)

        # List available feeds if requested
        if args.list:
            print("\nAvailable feeds:")
            for feed_id, config in FEEDS_CONFIG.items():
                print(f"  {feed_id}: {config['card_name']}")
            print("\nUse: python script.py [feed_id] to sync a specific feed")
            print("Or:  python script.py to sync all feeds")
            exit(0)

        # Sync specific feed or all feeds
        if args.feed_id:
            if args.feed_id not in FEEDS_CONFIG:
                print(f"Error: Unknown feed '{args.feed_id}'")
                print("Use --list to see available feeds")
                exit(1)
            success = processor.sync_feed(args.feed_id)
            print(f"{args.feed_id}: {'Success' if success else 'Failed'}")
        else:
            print("Syncing all feeds...")
            results = processor.sync_all()
            for feed_id, success in results.items():
                print(f"{feed_id}: {'Success' if success else 'Failed'}")

    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)
