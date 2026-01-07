from fastapi import APIRouter

from src.utils.logger import logger

health_router = APIRouter()


@health_router.get('/health')
async def health_check():
	logger.info('Health check requested')
	return {'status': 'ok'}
