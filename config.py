from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    APP_NAME    : str = "BI Co-Pilot"
    APP_VERSION : str = "1.0.0"
    DEBUG       : bool = True

    JWT_SECRET_KEY   : str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM    : str = "HS256"
    JWT_EXPIRE_HOURS : int = 24
 
    DATABASE_URL : str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./bi_copilot.db"  
    )
 
    # OPENAI_API_KEY : str = os.getenv("OPENAI_API_KEY")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")

    REDIS_HOST : str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT : int = int(os.getenv("REDIS_PORT", 6379))

    BCRYPT_ROUNDS : int = 12   

settings = Settings()