"""
Main entry point for the Notion Search API.

Run with: python main.py
Or with uvicorn: uvicorn app.api.main:app --reload
"""

if __name__ == "__main__":
    import uvicorn
    from config import settings

    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )
