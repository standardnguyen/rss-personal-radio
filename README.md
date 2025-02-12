# RSS Personal Radio

A Python-based system that automatically syncs podcast episodes to Trello cards and generates personalized daily audio introductions using text-to-speech. This project helps create a personalized radio experience by managing podcast content through Trello and adding custom voice introductions.

## Features

- Automatically syncs latest episodes from multiple podcast RSS feeds to Trello cards
- Generates daily personalized audio introductions using ElevenLabs text-to-speech
- Applies audio effects (flanger, phaser, etc.) to the generated introductions
- Manages all audio content through Trello cards
- Runs on a scheduled basis using cron jobs

## Components

- `mp3.py` - Main podcast sync script that downloads episodes from RSS feeds and updates Trello cards
- `daily_intro.py` - Generates personalized daily introductions using ElevenLabs
- `vocoder.py` - Applies audio effects to generated speech
- `update_trello_card_audio.py` - Utility for updating Trello cards with audio attachments
- `run_jobs.sh` and `run_daily_jobs.sh` - Shell scripts for scheduled execution

## Prerequisites

- Python 3.12 (managed via pyenv)
- Trello account with API access
- ElevenLabs account with API access

## Installation

### Setting up Python environment

1. Install pyenv if you haven't already:
   ```bash
   # On Ubuntu/Debian
   sudo apt update
   sudo apt install pyenv
   
   # On macOS with Homebrew
   brew install pyenv
   ```

2. Install Python 3.12 using pyenv:
   ```bash
   pyenv install 3.12
   ```

3. Create a new virtual environment:
   ```bash
   # This will create a .venv directory in your current directory
   pyenv virtualenv 3.12 .venv
   pyenv local .venv
   ```

### Project Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd rss-personal-radio
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate  # On Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment template and configure your credentials:
   ```bash
   cp .env.template .env
   ```
   Edit `.env` and add your:
   - Trello API key
   - Trello token
   - Trello board name
   - ElevenLabs API key

## Configuration

### Podcast Feeds

Edit the `FEEDS_CONFIG` dictionary in `mp3.py` to configure your podcast feeds:

```python
FEEDS_CONFIG = {
    'feed_id': {
        'feed_url': 'https://example.com/feed.xml',
        'card_name': 'Card Name on Trello',
        'file_prefix': 'prefix_for_downloaded_files'
    },
    # Add more feeds as needed
}
```

### Audio Effects

Customize the audio effects in `vocoder.py` by adjusting the parameters:

```python
DO_FLANGER = True
FLANGER_RATE = 1
FLANGER_DEPTH = 0.8
# ... other effect parameters
```

## Usage

### Manual Execution

Run the podcast sync:
```bash
python mp3.py
```

Generate a daily intro:
```bash
python daily_intro.py
```

### Scheduled Execution

The project includes two shell scripts for scheduled execution:

1. `run_jobs.sh` - Runs the podcast sync (typically every few hours)
2. `run_daily_jobs.sh` - Runs the daily intro generation (once per day)

Add to crontab:
```bash
# Run podcast sync every hour from 4 AM to 5 PM
0 4-17 * * * /path/to/run_jobs.sh username >> /path/to/cron.log 2>&1

# Run daily intro at 1 AM
0 1 * * * /path/to/run_daily_jobs.sh username >> /path/to/cron.log 2>&1
```

## Project Structure

```
.
├── .env.template           # Template for environment variables
├── .gitignore             # Git ignore rules
├── .python-version        # Python version specification
├── daily_intro.py         # Daily introduction generator
├── mp3.py                 # Podcast sync main script
├── requirements.txt       # Python dependencies
├── run_daily_jobs.sh      # Shell script for daily tasks
├── run_jobs.sh           # Shell script for hourly tasks
├── update_trello_card_audio.py  # Trello card update utility
└── vocoder.py            # Audio effects processor
```

## Logging

The system logs activities to:
- Daily rotating logs in the `logs/` directory
- Console output
- Cron job output in `cron.log`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

See [LICENSE.md](./LICENSE.md)