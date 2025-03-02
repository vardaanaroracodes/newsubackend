from .brave_service import BraveSearchService
from .gemini_service import GeminiService

brave_service = None
gemini_service = None

def init_services(app):
    global brave_service, gemini_service
    
    if not brave_service:
        brave_service = BraveSearchService()
    
    if not gemini_service:
        gemini_service = GeminiService()
    
    return brave_service, gemini_service