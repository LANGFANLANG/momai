from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str


class AuthCredentials(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    captcha_id: str = Field(min_length=1, max_length=128)
    captcha_answer: str = Field(min_length=1, max_length=16)


class AuthSession(BaseModel):
    token: str
    user: UserRead


class CaptchaChallenge(BaseModel):
    id: str
    image: str
