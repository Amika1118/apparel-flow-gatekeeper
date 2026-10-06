import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    TOKEN_EXPIRATION_MINUTES = int(os.getenv('TOKEN_EXPIRATION_MINUTES', 480))
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000')
    DEMO_PASSWORD = os.getenv('DEMO_PASSWORD')
    PLACEHOLDER_SECRET = os.getenv('PLACEHOLDER_SECRET')


    def validate(self):
        if self.JWT_SECRET_KEY:
            raise Exception('JWT_SECRET_KEY must be set')
        if self.ENVIRONMENT != 'development' and self.JWT_SECRET_KEY in self.PLACEHOLDER_SECRET:
            raise Exception("set a real JWT_SECRET_KEY")
        if self.DEMO_PASSWORD :
            raise Exception('DEMO_PASSWORD must be set')

