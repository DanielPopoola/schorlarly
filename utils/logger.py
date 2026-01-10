import sys

from loguru import logger

# from src.config.settings import settings


def setup_logger():
	logger.remove()

	logger.add(
		sys.stderr,
		level='INFO',
		format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | \
        <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
	)


setup_logger()
