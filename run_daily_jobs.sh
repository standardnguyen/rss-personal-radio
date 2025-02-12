#!/bin/bash
# run_jobs.sh
# A wrapper script to run daily_intro.py and mp3.py from the project directory,
# using a pyenv-based virtual environment.

# Usage: ./run_jobs.sh <username>
# Example: ./run_jobs.sh standard
# Once a day: 0 1 * * * /home/standard/Projects/rss-personal-radio/run_daily_jobs.sh standard >> /home/standard/Projects/rss-personal-radio/cron.log 2>&1

# 1. Check if a username was provided as an argument.
if [ $# -lt 1 ]; then
  echo "Usage: $0 <username>"
  exit 1
fi

# 2. Use the provided username to construct the project path.
USER_NAME="$1"
PROJECT_DIR="/home/${USER_NAME}/Projects/rss-personal-radio"

# 3. Change to the project directory.
cd "$PROJECT_DIR" || {
  echo "Project directory not found at $PROJECT_DIR; exiting."
  exit 1
}

# 4. Load environment variables (optional).
if [ -f ".env" ]; then
  set -o allexport     # turn on 'allexport' so all variables sourced become environment vars
  source .env          # read the .env file as if it were a shell script
  set +o allexport     # turn off 'allexport'
fi

# 5. (OPTIONAL) Export the variables directly if you don’t use a .env file:
# export TRELLO_API_KEY="your_trello_api_key"
# export TRELLO_TOKEN="your_trello_token"
# export TRELLO_BOARD_NAME="your_trello_board_name"
# export ELEVENLABS_API_KEY="your_elevenlabs_api_key"

# 6. Activate the pyenv-based virtual environment.
#    Adjust this path to match where your environment lives.
#    e.g., ~/.pyenv/versions/.venv/bin/activate
if [ -f "/home/${USER_NAME}/.pyenv/versions/.venv/bin/activate" ]; then
  source "/home/${USER_NAME}/.pyenv/versions/.venv/bin/activate"
else
  echo "Could not find virtual environment at /home/${USER_NAME}/.pyenv/versions/.venv/bin/activate."
  echo "Please adjust the path as needed."
  exit 1
fi

# 7. Run daily_intro.py
echo "Running daily_intro.py..."
python daily_intro.py
if [ $? -ne 0 ]; then
  echo "daily_intro.py encountered an error." >&2
fi

# 9. Deactivate the virtual environment if it was activated.
if [ -n "$VIRTUAL_ENV" ]; then
  deactivate
fi

echo "Jobs completed."
