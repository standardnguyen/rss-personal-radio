import os
import logging
from datetime import datetime
from pathlib import Path
from trello import TrelloClient

def update_trello_card_audio(card_name: str, audio_file_path: str) -> bool:
    """
    Update a Trello card by removing any existing MP3 attachments,
    updating the card’s description, and attaching the specified local audio file.
    
    This function requires the following environment variables to be set:
      - TRELLO_API_KEY
      - TRELLO_TOKEN
      - TRELLO_BOARD_NAME

    Args:
        card_name (str): The name of the Trello card to update.
        audio_file_path (str): The local filesystem path to the audio file (mp3) to attach.
    
    Returns:
        bool: True if the update was successful; False otherwise.
    """
    # Set up a basic logger
    logger = logging.getLogger("update_trello_card_audio")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(handler)

    # Load required configuration from environment variables
    trello_key = os.getenv("TRELLO_API_KEY")
    trello_token = os.getenv("TRELLO_TOKEN")
    board_name = os.getenv("TRELLO_BOARD_NAME")
    missing_vars = []
    if trello_key is None:
        missing_vars.append("TRELLO_API_KEY")
    if trello_token is None:
        missing_vars.append("TRELLO_TOKEN")
    if board_name is None:
        missing_vars.append("TRELLO_BOARD_NAME")
    if missing_vars:
        raise ValueError("Missing required environment variables: " + ", ".join(missing_vars))

    # Initialize the Trello client
    client = TrelloClient(api_key=trello_key, token=trello_token)

    # Find the board by name
    board = None
    for b in client.list_boards():
        if b.name == board_name:
            board = b
            break
    if board is None:
        logger.error(f"Board '{board_name}' not found.")
        return False

    # Find the card by name (searching all lists on the board)
    card = None
    for list_obj in board.list_lists():
        for c in list_obj.list_cards():
            if c.name == card_name:
                card = c
                break
        if card is not None:
            break
    if card is None:
        logger.error(f"Card '{card_name}' not found on board '{board_name}'.")
        return False

    # Remove any existing MP3 attachments on the card
    try:
        attachments = card.get_attachments()
        for attachment in attachments:
            if attachment.name.endswith('.mp3'):
                card.remove_attachment(attachment.id)
    except Exception as e:
        logger.warning(f"Error removing existing attachments: {str(e)}")

    # Update the card description to note a manual update
    description = (
        f"Updated Audio File\n"
        f"Updated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"File: {Path(audio_file_path).name}"
    )
    try:
        card.set_description(description)
    except Exception as e:
        logger.error(f"Error updating card description: {str(e)}")
        return False

    # Attach the new audio file
    try:
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            logger.error(f"Audio file '{audio_file_path}' does not exist.")
            return False

        # You can construct a filename; here we prefix with "manual" and today's date.
        file_name = f"manual_{datetime.now().strftime('%Y%m%d')}.mp3"
        with open(audio_path, 'rb') as f:
            card.attach(name=file_name, file=f, mimeType='audio/mpeg')
    except Exception as e:
        logger.error(f"Error attaching audio file: {str(e)}")
        return False

    logger.info(f"Successfully updated card '{card_name}' with audio '{audio_path.name}'.")
    return True
