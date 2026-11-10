import os
from dotenv import load_dotenv

load_dotenv()  # reads .env into the environment; must run before os.getenv


class Settings:
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')  # no default on purpose
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    TOKEN_EXPIRATION_MINUTES = int(os.getenv('TOKEN_EXPIRATION_MINUTES', 480))
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    DEMO_PASSWORD = os.getenv('DEMO_PASSWORD')

    PLACEHOLDER_SECRETS = {'FVDSHF', 'changeme', 'secret', 'your-secret-here'}

    def validate(self):
        if not self.JWT_SECRET_KEY:
            raise Exception('JWT_SECRET_KEY must be set')
        if self.ENVIRONMENT != 'development' and self.JWT_SECRET_KEY in self.PLACEHOLDER_SECRETS:
            raise Exception('set a real JWT_SECRET_KEY')
        if not self.DEMO_PASSWORD:
            raise Exception('DEMO_PASSWORD must be set')


settings = Settings()
settings.validate()